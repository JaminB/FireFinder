import os
import csv
import json
import operator
from datetime import datetime
from math import sin, cos, sqrt, atan2, radians
from sys import stderr
from typing import List, Optional
from zlib import adler32

import requests


class WildFire:
    """
    Simple struct representing the relevant details from a wildfire
    """

    def __init__(self, lat, lon, date, time, confidence):
        self.lat = float(lat)
        self.lon = float(lon)
        self.date = date
        self.time = time
        self.datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H%M')
        self.confidence = confidence
        self.seen_count = 1
        self.fuzzy_hash = adler32(str(round(self.lat, 2) + round(self.lon, 2)).encode('ascii'))

    @classmethod
    def create_from_csv_row(cls, row):
        latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, \
        confidence, version, bright_ti5, frp, daynight = row
        return cls(latitude, longitude, acq_date, acq_time, confidence)

    def update_seen_count(self):
        self.seen_count += 1

    def __str__(self):
        return json.dumps(
            dict(
                lat=self.lat,
                lon=self.lon,
                date=str(self.date),
                time=str(self.time),
                confidence=self.confidence,
                seen_count=self.seen_count,
                hash=self.fuzzy_hash
            )
        )


# Open up our config.json


def _load_config(config_path='config.json') -> dict:
    """
    Load the configuration file

    :param config_path: The path to the config.json file, default is current_directory
    :return: A dictionary of config keys and values.
    """
    try:
        with open(config_path) as config_f:
            config = json.load(config_f)
    except FileNotFoundError:
        print('You are missing a config.json file. It must be present in the same directory you run this script.',
              file=stderr)
    except ValueError as e:
        print(f'There is an error in your JSON file: {e}', file=stderr)
    return config


# Load our configuration before anything else
CONFIG = _load_config()


def download_datasets() -> None:
    """
    Download the datasets from the URLs specified in the configuration; store them locally in the specified
    csv_directory

    :return: None
    """
    for url in CONFIG.get('csv_urls'):
        # Make an HTTP GET request to each of the csv_urls specified in our config.json
        response = requests.get(url)
        # Ignore errors; E.G server is down; file does not exist
        if response.status_code != 200:
            continue

        # Write our CSV files to disk (E.g csvs/J1_VIIRS_C2_Global_7d.csv)
        csv_directory = CONFIG.get('csv_output_directory', 'csvs/')
        try:
            with open(os.path.join(csv_directory, response.url.split('/')[-1]), 'w') as csv_f:
                csv_f.write(response.text)
        except FileNotFoundError:
            print(f'Could not find {csv_directory} directory. Please create it first.')


def get_distance_between_two_points(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Basic trig to find the distance between two kilometers using Harversines' formulae

    :param lat1: Latitude coordinate 1
    :param lon1: Longitude coordinate 1
    :param lat2: Latitude coordinate 2
    :param lon2: Longitude coordinate 2

    :return: Distance in kilometers between points 1 and 2
    """

    # approximate radius of earth in km
    R = 6373.0

    # Python's trig function all use radians instead of degrees
    # because their core dev team hates all that is good and holy.

    lat1 = radians(float(lat1))
    lat2 = radians(float(lat2))
    lon1 = radians(float(lon1))
    lon2 = radians(float(lon2))

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    #     a = sin²(Δφ/2) + cos φ1 ⋅ cos φ2 ⋅ sin²(Δλ/2)
    #     c = 2 ⋅ atan2( √a, √(1−a) )
    #     d = R ⋅ c
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance


def is_coordinate_in_bounding_box(lat: float, lon: float) -> bool:
    """
    Check to see if the given coordinates exists within the specified bounding box.

    Note that the bounding box is given as X1, X2, Y1, Y2 or lat1, lat2, lon1, lon2

    Panama's for example can be represented by: [-82.9657830472, 7.2205414901, -77.2425664944, 9.61161001224]
    More bounding boxes are available here: https://rb.gy/xl5gfh

    :param lat: Latitude coordinate
    :param lon: Longitude coordinate

    :return: True, if the coordinate exists within the bounding box.
    """

    # Turn this into a basic geometry (bounding_box) problem:
    # https://www.geeksforgeeks.org/check-if-a-point-lies-on-or-inside-a-rectangle-set-2

    x, y = lat, lon

    lat1, lon1, lat2, lon2 = CONFIG.get('country_bounding_box')
    x1, y1, x2, y2 = lat1, lon1, lat2, lon2

    # 1. You can evaluate with this expression: x > x1 and x < x2 and y > y1 and y < y2
    # 2. Which can be simplified to: x1 < x < x2 and y > y1 and y < y2
    # 3. Which can further be simplified to x1 < x < x2 and y1 < y < y2

    return x1 < x < x2 and y1 < y < y2


def get_wild_fires(honor_bounding_box=True) -> List[WildFire]:
    """
    Extract the wild fire data from all the CSVs currently saved to disk

    :param honor_bounding_box: If set to True, this function will only return values within that bounding box.
    Otherwise, the scope is determined by the downloaded datasets
    :return A list of Wildfire instances
    """
    wild_fires = []
    csv_directory = CONFIG.get('csv_output_directory', 'csvs')
    for csv_file in os.listdir(csv_directory):
        full_path_to_csv = os.path.join(csv_directory, csv_file)
        with open(full_path_to_csv, 'r') as csv_f:
            for row in csv.reader(csv_f):
                latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, \
                confidence, version, bright_ti5, frp, daynight = row
                try:
                    if honor_bounding_box:
                        if is_coordinate_in_bounding_box(float(latitude), float(longitude)):
                            wild_fires.append(WildFire.create_from_csv_row(row))
                    else:
                        wild_fires.append(WildFire.create_from_csv_row(row))
                except ValueError:
                    # This is most likely the header row
                    continue
    return wild_fires


def merge_wild_fires(max_distance_radius=10, honor_bounding_box=True) -> List[WildFire]:
    """
    Identify fires spotted more than once by different satellites or on different days.
    Additionally, results are de-duplicated using a "fuzzy hashing" methodology.


    :param max_distance_radius: Fires within this radius will be considered the same wildfire
    :param honor_bounding_box: If set to True, this function will only return values within that bounding box.
    Otherwise, the scope is determined by the downloaded datasets
    :return: A list of Wildfire instances
    """

    def get_first_match(fuzzy_hash: int) -> Optional[WildFire]:
        """
        Locates the first instance of a wildfire in our list that has the same hash as the one given

        :param fuzzy_hash: The hash created that represents the VERY approximate location of a wildfire
        :return: A wildfire class instance or None if no matches found
        """
        for candidate in original_wildfires:
            if candidate.fuzzy_hash == fuzzy_hash:
                return candidate
        return None

    original_wildfires = get_wild_fires(honor_bounding_box=honor_bounding_box)
    comparison_wildfires = get_wild_fires(honor_bounding_box=honor_bounding_box)
    deduplicated_wildfires = []

    # Iterate through our wild fires within our bounding box
    # For every fire, check to see how close it is to every other fire
    # If it is within max_distance_radius km then we update the seen count
    # Remove any other instances from our comparison list that were within the specified distance for future iterations
    for i, wild_fire in enumerate(original_wildfires):
        temp_comparison_wildfires = []
        for j, compare_wild_fire in enumerate(comparison_wildfires):
            if i == j:
                continue
            distance_between_fires = get_distance_between_two_points(wild_fire.lat, wild_fire.lon,
                                                                     compare_wild_fire.lat, compare_wild_fire.lon)
            if distance_between_fires <= max_distance_radius:
                wild_fire.update_seen_count()
            else:
                temp_comparison_wildfires.append(compare_wild_fire)
        comparison_wildfires = temp_comparison_wildfires

    # Sort descending by seen count
    original_wildfires = sorted(original_wildfires, key=operator.attrgetter('seen_count'), reverse=True)

    # Identify unique values using our fuzzy hashing method
    # (fuzzy hash represents coordinates up to 2 significant digits 1.11km)
    # Add our de-duplicated results to a new list
    unique_hashes = set([wild_fire.fuzzy_hash for wild_fire in original_wildfires])
    for hash in unique_hashes:
        match = get_first_match(hash)
        if not match:
            continue
        deduplicated_wildfires.append(match)
    # Sort by seen_count descending
    deduplicated_wildfires = sorted(deduplicated_wildfires, key=operator.attrgetter('seen_count'), reverse=True)
    return deduplicated_wildfires


if __name__ == '__main__':
    download_first = False
    if download_first:
        download_datasets()
    for wildfire in merge_wild_fires():
        print(wildfire)
