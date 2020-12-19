import argparse
import csv
import json
import operator
import os
from datetime import datetime
from math import sin, cos, sqrt, atan2, radians
from sys import stderr
from typing import List, Optional
from zlib import adler32

import geojson
import requests
import tabulate

FUZZY_MAP = {
    0: (111, 'km'),
    1: (11.1, 'km'),
    2: (1.11, 'km'),
    3: (111, 'm'),
    4: (11.1, 'm'),
    5: (1.11, 'm'),
    6: (0.111, 'm'),
    7: (1.11, 'cm'),
    8: (1.11, 'm')
}

class WildFire:
    """
    Simple struct representing the relevant details from a wildfire
    """

    def __init__(self, lat, lon, date, time, confidence, fuzziness=2):
        """

        :param lat: The latitude of the wildfire
        :param lon: The longitude of the wildfire
        :param date: The YYYY-MM-DD
        :param time: The HHMM
        :param confidence: String or integer value representing the level of confidence that there is a wildfire at the
                           specified coordinates
        :param fuzziness: Value between 0 and 8. This parameter is used to merge wild-fires together that are close
                          geographically; the higher the number the more exact coordinates have to be to merge two
                          fires:

                            decimal  degrees    distance
                            places
                            -------------------------------
                            0        1.0        111 km
                            1        0.1        11.1 km
                            2        0.01       1.11 km
                            3        0.001      111 m
                            4        0.0001     11.1 m
                            5        0.00001    1.11 m
                            6        0.000001   0.111 m
                            7        0.0000001  1.11 cm
                            8        0.00000001 1.11 mm
        """
        self.lat = float(lat)
        self.lon = float(lon)
        self.date = date
        self.time = time
        self.datetime = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H%M')
        self.confidence = confidence
        self.seen_count = 1
        self.fuzzy_hash = adler32(str(round(self.lat, fuzziness) + round(self.lon, fuzziness)).encode('ascii'))

    @classmethod
    def create_from_csv_row(cls, row, fuzziness=2):
        latitude, longitude, bright_ti4, scan, track, acq_date, acq_time, satellite, \
        confidence, version, bright_ti5, frp, daynight = row
        return cls(latitude, longitude, acq_date, acq_time, confidence, fuzziness=fuzziness)

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

    def to_geojson_feature(self):
        return geojson.Feature(
            geometry=geojson.MultiPoint(
                coordinates=[(self.lat, self.lon)]
            ),
            properties=dict(
                LATITUDE=self.lat,
                LONGITUDE=self.lon,
                ACQ_DATE=self.date,
                ACQ_TIME=str(self.time)
            ))

    def to_tabular_feature(self):
        return [self.seen_count, str(self.datetime), self.lat, self.lon]


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


def get_wild_fires(honor_bounding_box=True, fuzziness=2) -> List[WildFire]:
    """
    Extract the wild fire data from all the CSVs currently saved to disk

    :param honor_bounding_box: If set to True, this function will only return values within that bounding box.
    Otherwise, the scope is determined by the downloaded datasets
    :param fuzziness: Value between 0 and 8. This parameter is used to merge wild-fires together that are close
                  `geographically; the higher the number the more exact coordinates have to be to merge two
                  fires
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
                            wild_fires.append(WildFire.create_from_csv_row(row, fuzziness=fuzziness))
                    else:
                        wild_fires.append(WildFire.create_from_csv_row(row, fuzziness=fuzziness))
                except ValueError:
                    # This is most likely the header row
                    continue
    return wild_fires


def merge_wild_fires(honor_bounding_box=True, fuzziness=2) -> List[WildFire]:
    """
    Identify fires spotted more than once by different satellites or on different days.
    Additionally, results are de-duplicated using a "fuzzy hashing" methodology.


    :param fuzziness: Value between 0 and 8. This parameter is used to merge wild-fires together that are close
                      `geographically; the higher the number the more exact coordinates have to be to merge two
                      fires
    :param honor_bounding_box: If set to True, this function will only return values within that bounding box.
    Otherwise, the scope is determined by the downloaded datasets
    :return: A list of Wildfire instances
    """
    tabular_headers = ['Seen Count', 'First Seen Date', 'Latitude', 'Longitude']
    tabular_rows = []

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

    original_wildfires = get_wild_fires(honor_bounding_box=honor_bounding_box, fuzziness=fuzziness)
    comparison_wildfires = get_wild_fires(honor_bounding_box=honor_bounding_box, fuzziness=fuzziness)
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
            if wild_fire.fuzzy_hash == compare_wild_fire.fuzzy_hash:
                wild_fire.update_seen_count()
            else:
                temp_comparison_wildfires.append(compare_wild_fire)
        comparison_wildfires = temp_comparison_wildfires

    # Sort descending by seen count
    original_wildfires = sorted(original_wildfires, key=operator.attrgetter('seen_count'), reverse=True)

    # Identify unique values using our fuzzy hashing method
    # (fuzzy hash represents coordinates up to n significant digits.)
    # Add our de-duplicated results to a new list
    unique_hashes = set([wild_fire.fuzzy_hash for wild_fire in original_wildfires])
    for hash in unique_hashes:
        match = get_first_match(hash)
        if not match:
            continue
        deduplicated_wildfires.append(match)
    # Sort by seen_count descending
    deduplicated_wildfires = sorted(deduplicated_wildfires, key=operator.attrgetter('seen_count'), reverse=True)

    for deduped_wild_fire in deduplicated_wildfires:
        tabular_rows.append(deduped_wild_fire.to_tabular_feature())
    distance, unit = FUZZY_MAP.get(fuzziness)
    print(tabulate.tabulate(tabular_rows, headers=tabular_headers))
    print('\n')
    print(f'Fires must be within {distance} {unit} of one another to be merged.')
    print(f'Using this method to merge {len(original_wildfires)} into {len(deduplicated_wildfires)} wildfires.')

    return deduplicated_wildfires


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('output_file', action="store", type=str,
                            help='The path to where the geojson file will be written.')
    arg_parser.add_argument(
        '--download-csvs', dest='download_csvs', action='store_true', help='Download new CSV files; delete old ones.'
    )
    arg_parser.add_argument(
        '--config-file', dest='config_file', action='store_true', default='config.json',
        help='The path to the config.json file.'
    )
    arg_parser.add_argument(
        '--merge-sensitivity', dest='merge_sensitivity', type=int, default=2,
        help='Value between 0 and 8: '
             '0=111 km; 1=11.1 km; 2=1.11 km; 3=111 m; 4=11.1 m; 5=1.11 m; 6=0.111 m; 7=1.11 cm; 8=1.11 mm'
    )

    args = arg_parser.parse_args()
    CONFIG = _load_config(args.config_file)
    if args.download_csvs:
        print('Downloading datasets...')
        download_datasets()

    features = []
    for wild_fire in merge_wild_fires(honor_bounding_box=True, fuzziness=args.merge_sensitivity):
        features.append(wild_fire.to_geojson_feature())
    with open(args.output_file, 'w') as geojson_output_f:
        geojson_output_f.write(json.dumps(geojson.FeatureCollection(features=features), indent=1))
    print('\n' + '-' * 60)
    print(f'Config File: {args.config_file}')
    print(f'Output File: {args.output_file}')
    print('-' * 60)

