# OSM2RN

A simple Python code to extract road network (in Shapefile) from [OpenStreetMap (OSM)](https://www.openstreetmap.org/). 

It serves as a fundamental data for trajectory map matching and other usages.

The generated road network is used for [TPTK](https://github.com/sjruan/TPTK) and [DeepMG](https://github.com/sjruan/DeepMG).

## Usage

1. Download OSM data from [Geofabrik](https://download.geofabrik.de/) in `.osm.pbf` format.

2. Clip the data according to your region of interest. 

```
python osm_clip.py --input_path china-latest.osm.pbf --output_path interest_region.osm.pbf --min_lat 39.8451 --min_lng 116.2810 --max_lat 39.9890 --max_lng 116.4684
```

3. Construct and store the road network from the clipped data.

```
python osm_to_rn.py --input_path interest_region.osm.pbf --output_path interest_region
```


## Requirements

OSM2RN uses the following dependencies with Python 3.6

* networkx==2.3

* GDAL==2.3.2

* osmium==2.15.3

Other packages can be easily installed using `conda install` or `pip install`, while the following scripts are recommended for `gdal`.

```
conda install -c conda-forge gdal==2.3.2
```
