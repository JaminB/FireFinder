## FireFinder

`fire_finder.py` is a simple utility that parses open-source NASA FIRMS data, and returns a `geojson` file of fires within a given bounding-box.

### Installation
1. Install Python3 or greater.
2. Install the required packages `pip3 install -r requirements.txt`

### Usage

`python3 fire_finder.py -h`

```buildoutcfg
usage: fire_finder.py [-h] [--download-csvs] [--config-file] [--merge-sensitivity MERGE_SENSITIVITY] output_file

positional arguments:
  output_file           The path to where the geojson file will be written.

optional arguments:
  -h, --help            show this help message and exit
  --download-csvs       Download new CSV files; delete old ones.
  --config-file         The path to the config.json file.
  --merge-sensitivity MERGE_SENSITIVITY
                        Value between 0 and 8: 0=111 km; 1=11.1 km; 2=1.11 km; 3=111 m; 4=11.1 m; 5=1.11 m; 6=0.111 m; 7=1.11 cm; 8=1.11 mm
```

### Configuration

You can either place the `config.json` in the same directory as the `fire_finder.py` script or, when executing the script, 
point the `--config-file` parameter to where ever the `config.json` exists on disk.

- *country_bounding_box*: Exclude any values outside this area. Given in the format: `[lat1, lon1, lat2, lon2]`
- *csv_urls*: The full URL to the CSV files you wish to merge and analyze.
- *csv_output_directory*: The path where CSVs (NASA FIRMS data) is cached. 

```json
{
  "country_bounding_box": [6.5, -84, 10, -76.5],
  "csv_urls": [
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/c6/csv/MODIS_C6_Global_7d.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_Global_7d.csv",
    "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv"
  ],
  "csv_output_directory": "csvs/",
}

```

### Examples:

1. Merge wildfires within 11 km of each other.

```bash
python3 fire_finder.py --merge-sensitivity=2 my_output.json
```

2. Don't merge wildfires at all.
```bash
python3 fire_finder.py --merge-sensitivity=8 my_output.json
```

3. Download CSVs first (refresh data if its been updated)
```bash
python3 fire_finder.py --download-csvs my_output.json
```

   
#### Sample Console Output
```buildoutcfg
  Seen Count  First Seen Date        Latitude    Longitude
------------  -------------------  ----------  -----------
           4  2020-12-13 06:36:00     9.16883     -79.5373
           4  2020-12-14 19:06:00     8.0566      -81.2318
           3  2020-12-18 17:48:00     9.34745     -79.8887
           3  2020-12-15 18:48:00     8.57511     -76.6631
           2  2020-12-12 06:54:00     9.07947     -79.4935
           2  2020-12-18 18:42:00     8.54965     -82.563
           2  2020-12-16 18:30:00     9.75075     -82.9732
           2  2020-12-13 06:36:00     9.83225     -83.9052
           2  2020-12-16 18:30:00     9.88388     -83.0591
           2  2020-12-16 18:30:00     8.57937     -76.6668
           2  2020-12-15 17:54:00     8.59975     -78.0831
           2  2020-12-14 18:12:00     8.47589     -80.9597
           2  2020-12-12 18:54:00     8.20811     -82.0011
           2  2020-12-12 06:54:00     9.83034     -83.904
           1  2020-12-14 19:06:00     9.56013     -82.5825
           1  2020-12-14 06:18:00     8.46741     -81.4435
           1  2020-12-14 07:12:00     8.46826     -81.4455
           1  2020-12-16 18:30:00     9.83867     -83.9608
           1  2020-12-18 18:35:00     9.341       -79.882
           1  2020-12-12 18:00:00     8.46299     -79.9754


Fires must be within 1.11 km of one another to be merged.
Using this method to merge 29 into 20 wildfires.

------------------------------------------------------------
Config File: config.json
Output File: my_output.json
```

#### Sample Geojson output

```json
{
 "type": "FeatureCollection",
 "features": [
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.16883,
      -79.53727
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.16883,
    "LONGITUDE": -79.53727,
    "ACQ_DATE": "2020-12-13",
    "ACQ_TIME": "0636"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.0566,
      -81.23181
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.0566,
    "LONGITUDE": -81.23181,
    "ACQ_DATE": "2020-12-14",
    "ACQ_TIME": "1906"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.34745,
      -79.88868
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.34745,
    "LONGITUDE": -79.88868,
    "ACQ_DATE": "2020-12-18",
    "ACQ_TIME": "1748"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.57511,
      -76.66314
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.57511,
    "LONGITUDE": -76.66314,
    "ACQ_DATE": "2020-12-15",
    "ACQ_TIME": "1848"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.07947,
      -79.49352
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.07947,
    "LONGITUDE": -79.49352,
    "ACQ_DATE": "2020-12-12",
    "ACQ_TIME": "0654"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.54965,
      -82.56304
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.54965,
    "LONGITUDE": -82.56304,
    "ACQ_DATE": "2020-12-18",
    "ACQ_TIME": "1842"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.75075,
      -82.97324
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.75075,
    "LONGITUDE": -82.97324,
    "ACQ_DATE": "2020-12-16",
    "ACQ_TIME": "1830"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.83225,
      -83.90525
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.83225,
    "LONGITUDE": -83.90525,
    "ACQ_DATE": "2020-12-13",
    "ACQ_TIME": "0636"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.88388,
      -83.05907
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.88388,
    "LONGITUDE": -83.05907,
    "ACQ_DATE": "2020-12-16",
    "ACQ_TIME": "1830"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.57937,
      -76.66685
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.57937,
    "LONGITUDE": -76.66685,
    "ACQ_DATE": "2020-12-16",
    "ACQ_TIME": "1830"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.59975,
      -78.0831
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.59975,
    "LONGITUDE": -78.0831,
    "ACQ_DATE": "2020-12-15",
    "ACQ_TIME": "1754"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.47589,
      -80.9597
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.47589,
    "LONGITUDE": -80.9597,
    "ACQ_DATE": "2020-12-14",
    "ACQ_TIME": "1812"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.20811,
      -82.00114
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.20811,
    "LONGITUDE": -82.00114,
    "ACQ_DATE": "2020-12-12",
    "ACQ_TIME": "1854"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.83034,
      -83.904
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.83034,
    "LONGITUDE": -83.904,
    "ACQ_DATE": "2020-12-12",
    "ACQ_TIME": "0654"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.56013,
      -82.58255
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.56013,
    "LONGITUDE": -82.58255,
    "ACQ_DATE": "2020-12-14",
    "ACQ_TIME": "1906"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.46741,
      -81.44349
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.46741,
    "LONGITUDE": -81.44349,
    "ACQ_DATE": "2020-12-14",
    "ACQ_TIME": "0618"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.46826,
      -81.44551
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.46826,
    "LONGITUDE": -81.44551,
    "ACQ_DATE": "2020-12-14",
    "ACQ_TIME": "0712"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.83867,
      -83.96085
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.83867,
    "LONGITUDE": -83.96085,
    "ACQ_DATE": "2020-12-16",
    "ACQ_TIME": "1830"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      9.341,
      -79.882
     ]
    ]
   },
   "properties": {
    "LATITUDE": 9.341,
    "LONGITUDE": -79.882,
    "ACQ_DATE": "2020-12-18",
    "ACQ_TIME": "1835"
   }
  },
  {
   "type": "Feature",
   "geometry": {
    "type": "MultiPoint",
    "coordinates": [
     [
      8.46299,
      -79.97541
     ]
    ]
   },
   "properties": {
    "LATITUDE": 8.46299,
    "LONGITUDE": -79.97541,
    "ACQ_DATE": "2020-12-12",
    "ACQ_TIME": "1800"
   }
  }
 ]
}
```




