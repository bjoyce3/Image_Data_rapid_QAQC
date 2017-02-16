import argparse
import folium
import folium.map
import folium.element
import folium.plugins
import glob
import json
import math
import numpy
import os
import subprocess
import string
import sys
import time


try:
    import PIL.Image
    import scipy.misc
    scipy_installed = True
except ImportError:
    scipy_installed = False

exiftool = "/usr/local/bin/exiftool"  #Need to update to make a path for all OS

######################################################################
# COMMAND LINE ARGS
######################################################################
#Establish args from command line
"""Ultimately there will be three required inputs: coords, camera, and ground. Currently, the check for camera is not written.
"""
parser = argparse.ArgumentParser(description='Parses user input for PhenomeQC')
#Required arguments
parser.add_argument('-inputfolder', required=True, help='Input folder of images that are to be assessed.')
parser.add_argument('-coords', required=True, help='Input file that contains the coordinates for the plot that has been flown. String of field plot in WKT.')
#parser.add_argument('-camera', required=True, help='Type of camera used. Supported camera types: sequoia/parrot, rededge, rgb, hyperspectral. Inputs as a string.')
parser.add_argument('-ground', required=True, type=float, help='Ground level from ocean height in meters. Set as a double.')
parser.add_argument('-upper_flight_lvl', type=float, help='Upper bounds on flight level measured as above ground level in meters. Set as a double.')
parser.add_argument('-lower_flight_lvl', type=float, help='Lower acceptable bound on flight level as above ground level in meters. Set as a double.')

#Optional arguments
parser.add_argument('--resolution', type=float, help='Resolution of bounding boxes on the ground. Changes the size of bounding box on the ground. Default == half a meter. Input as a double in meters.')

args = parser.parse_args()


######################################################################
# JEROME
######################################################################

def directory_check(directory):
    '''
    Go over the directory and make sure that
    the directory has TIFFs we need

    Return False if no tiff file or has any other files
    Return True  if only have tiff file(s)
    '''
    return True in [files.endswith(".tif") for files in os.listdir(directory)]


class FieldError(Exception):
    '''
    All Errors related to class Field are FieldError
    '''
    pass


class BoundingBox:
    '''
    The class for the bounding box
    '''


    def __init__(self, corner_1, corner_2):

        if not isinstance(corner_1, tuple) or not isinstance(corner_2, tuple):
            raise Exception

        self.northwest = corner_1
        self.southeast = corner_2

    def intersect(self, another_bounding_box):

        if not isinstance(another_bounding_box, BoundingBox):
            raise TypeError("You need a BoundingBox instance")

        self.west, self.north = self.northwest
        self.east, self.south = self.southeast

        self.another_west, self.another_north = another_bounding_box.northwest
        self.another_east, self.another_south = another_bounding_box.southeast


class Field:
    '''
    Field class has all the GPS information of the Field
    Can split the field into several bounding box
    '''

    bounding_box = []

    def __init__(self, latlngs):
        if not latlngs:
            raise FieldError

        self.raw_bounding_box = latlngs

    def split_bounding_box(self):
        pass

    def simplified_field(self):
        '''
        Return the approximate bounding box of the field
        '''

        unzip_bounding_box = zip(*self.raw_bounding_box)

        latitute = sorted(unzip_bounding_box[0])

        latitute_east, latitute_west = latitute[0], latitute[-1]

        longitude = sorted(unzip_bounding_box[-1])

        longitude_south, longitude_north = longitude[0], longitude[-1]

        return [(latitute_west, longitude_north), (latitute_east, longitude_south)]

    def get_bounding_box(self):

        if not self.raw_bounding_box:
            raise FieldError("No bounding box information (you may need to split it beforehand)")

        return self.raw_bounding_box

    def is_inbound(self, bounding_box):

        if not isinstance(bounding_box, BoundingBox):
            raise Exception


def GPS_Loader(wkt_str):
    '''
    Loads the GPS information from a WKT file and
    Wraps into a Field instance
    '''

    raw_data = wkt_str.strip(string.ascii_uppercase + "()").split(",")

    coordinates = [(float(members.split()[0]), float(members.split()[1])) for members in raw_data]

    return Field(coordinates)


def GPS_Expectaion(field_data, lat, lng):
    '''
    Check whether the
    '''

    if not isinstance(field_data, Field):
        raise FieldError

######################################################################
# GPS CHECK
######################################################################

# http://stackoverflow.com/a/7478827
def bbox(lat, lon, fov, alt):
    radius_earth = 6378
    width = math.tan(0.5 * fov / 180 * math.pi) * (alt / 1000.0)

    lat_add = (width / radius_earth) * (180 / math.pi)
    lon_add = (width / radius_earth) * (180 / math.pi) / math.cos(lat * math.pi / 180)

    south = lat - lat_add
    north = lat + lat_add
    west = lon - lon_add
    east = lon + lon_add

    return (north, east, south, west)

def check_gps(image, ground_level, lower_flight_level, upper_flight_level, field):
    global exiftool

    check = dict()
    check['error'] = list()

    result = subprocess.check_output([exiftool, "-n", image])
    fov = -9999
    alt = -9999
    lat = -9999
    lon = -9999
    for line in result.split("\n"):
        if " : " in line:
            (key, val) = line.split(" : ", 2)
            key = key.strip()
            val = val.strip()
            if "Field Of View" == key:
                fov = float(val)
            if "GPS Altitude" == key:
                alt = float(val)
            if "GPS Latitude" == key:
                lat = float(val)
            if "GPS Longitude" == key:
                lon = float(val)

    check['fov'] = fov
    check['alt'] = alt
    check['lat'] = lat
    check['lon'] = lon

    # do we have all information we need
    if fov == -9999 or alt == -9999 or lat == -9999 or lon == -9999:
        raise ValueError('fov, alt, lat or lon not found in image')

    # check flight level
    if (alt - ground_level) < lower_flight_level:
        check['flight_level'] = 'low'
        check['error'].append('Flying to low (%f < %f)' % (alt - ground_level, lower_flight_level))
    elif (alt - ground_level) > upper_flight_level:
        check['flight_level'] = 'high'
        check['error'].append('Flying to high (%f > %f)' % (alt - ground_level, upper_flight_level))
    else:
        check['flight_level'] = 'OK'

    # check lat/lon
    (north, east, south, west) = bbox(lat, lon, fov, alt - ground_level)
    check['north'] = north
    check['east'] = east
    check['south'] = south
    check['west'] = west

    # field[0][1], field[0][0], field[1][1], field[1][0]
    if south > field[0][1]:
        check['field'] = 'north'
        check['error'].append('Flying to far north (%f > %f)' % (south, field[0][1]))
    if north < field[1][1]:
        check['field'] = 'south'
        check['error'].append('Flying to far south (%f < %f)' % (north, field[1][1]))
    if west > field[0][0]:
        check['field'] = 'west'
        check['error'].append('Flying to far west (%f < %f)' % (west, field[0][0]))
    if east < field[1][0]:
        check['field'] = 'east'
        check['error'].append('Flying to far east (%f > %f)' % (east, field[1][0]))
    if 'field' not in check:
        check['field'] = 'OK'

    return check

######################################################################
# OUTPUT FUNCTIONS
######################################################################

# create boundbox on map
def map_bbox(feature_group, north, east, south, west, text, color):
    bbox = list()
    bbox.append(tuple([north, east]))
    bbox.append(tuple([north, west]))
    bbox.append(tuple([south, west]))
    bbox.append(tuple([south, east]))
    bbox.append(tuple([north, east]))
    feature_group.add_children(folium.PolyLine(bbox, popup=text, color=color, weight=2.5, opacity=1))
# folium.features.RectangleMarker(
#     bounds=[[35.681, 139.766], [35.691, 139.776]],
#     color='blue',
#     fill_color='red',
#     popup='Tokyo, Japan').add_to(m)

# create map
def create_map(filename, results, field=None, boundaries=False, tiles=False):
    global scipy_installed

    map = folium.Map(location=[40.477507, -87.005613], zoom_start=16, tiles='Stamen Terrain')

    # add tiles to map
    if scipy_installed and tiles:
        layer_tiles = folium.FeatureGroup(name='Tiles')
        for result in results:
            im = PIL.Image.open(result['image'])
            im2 = im.resize((256, 192))
            data = scipy.misc.fromimage(im2)
            layer_tiles.add_children(folium.plugins.ImageOverlay(data, opacity=0.1,
                                                                 bounds=[[result['south'], result['east']],
                                                                         [result['north'], result['west']]]))
        map.add_children(layer_tiles)

    # show image boundaries
    if boundaries:
        layer_bbox_ok = folium.FeatureGroup(name='Box OK')
        layer_bbox_outside = folium.FeatureGroup(name='Box Outside')
        layer_bbox_flight = folium.FeatureGroup(name='Box Low/Hight')
        for result in results:
            if result['flight_level'] != 'OK':
                map_bbox(layer_bbox_flight, result['north'], result['east'], result['south'], result['west'], None, 'grey')
            elif result['field'] != 'OK':
                map_bbox(layer_bbox_outside, result['north'], result['east'], result['south'], result['west'], None, 'orange')
            else:
                map_bbox(layer_bbox_ok, result['north'], result['east'], result['south'], result['west'], None, 'blue')
        map.add_children(layer_bbox_ok)
        map.add_children(layer_bbox_flight)
        map.add_children(layer_bbox_outside)

    # add field to map
    if field:
        layer_field = folium.FeatureGroup(name='Field')
        map_bbox(layer_field, field[0][1], field[0][0], field[1][1], field[1][0], 'field', 'green')
        map.add_children(layer_field)

    # add flight path to map
    flightpath = list()
    for result in results:
        flightpath.append(tuple([result['lat'], result['lon']]))
    layer_flight_path = folium.FeatureGroup(name='Flight Path')
    layer_flight_path.add_children(folium.PolyLine(flightpath, popup='flightpath', color='red', weight=2.5, opacity=1))
    map.add_children(layer_flight_path)

    # add markers to map
    layer_image_ok = folium.FeatureGroup(name='Image OK')
    layer_image_outside = folium.FeatureGroup(name='Image Outside ')
    layer_image_flight = folium.FeatureGroup(name='Image Low/High')
    for result in results:
        html = """<table>
        <tr><th>Image</th><td>%s</td></tr>
        <tr><th>Lat/Lon</th><td>%f, %f</td></tr>
        <tr><th>Alt</th><td>%f</td></tr>
        </table>""" % (os.path.basename(result['image']), result['lat'], result['lon'], result['alt'])
        popup = folium.Popup(folium.element.IFrame(html, width="300px"))

        if result['flight_level'] != 'OK':
            layer_image_flight.add_children(folium.CircleMarker(location=[result['lat'], result['lon']], radius=5,
                                                                popup=popup, color='grey', fill_color='grey'))
        elif result['field'] != 'OK':
            layer_image_outside.add_children(folium.CircleMarker(location=[result['lat'], result['lon']], radius=5,
                                                                 popup=popup, color='orange', fill_color='orange'))
        else:
            layer_image_ok.add_children(folium.CircleMarker(location=[result['lat'], result['lon']], radius=5,
                                                            popup=popup, color='blue', fill_color='blue'))
    map.add_children(layer_image_ok)
    map.add_children(layer_image_flight)
    map.add_children(layer_image_outside)

    map.add_children(folium.map.LayerControl())

    # save map
    map.save(filename)


def create_log(filename, results):
    # write log file with all errors
    with open(filename, 'w') as log:
        for result in results:
            if len(result['error']) > 0:
                log.write(result['image'] + '\n')
                for error in result['error']:
                    log.write('\t' + str(error) + '\n')


def create_csv(filename, results, keys=None):
    if not keys:
        keys = ['Image']
        for result in results:
            for key in result.keys():
                if key not in keys:
                    keys.append(key)

    # write csv with all results
    with open("gps_check.csv", "w") as csv:
        line = 'ERROR'
        for key in keys:
            if key != 'error':
                line += '\t' + key
        csv.write(line + '\n')
        for result in results:
            if 'error' in result:
                line = str(len(result['error']))
            else:
                line = 'OK'
            for key in keys:
                if key != 'error':
                    line += '\t' + str(result.get(key, ''))
            csv.write(line + '\n')


def create_json(filename, results, keys=None, field=None):
    js = { 'results': results, 'keys': keys, 'field': field }
    with open(filename, 'w') as json_file:
        json_file.write(json.dumps(js, indent=True, sort_keys=True))

######################################################################
# MAIN FUNCTION
######################################################################

"""Initiates the other functions to check all images. The list `results` is a list of dicts with key(image properties/info stored in the list keys):value(stored value of the properties). The key `error` has a list of values so there can be multiple error reports on anything that's outside of the parameters set."""
field = GPS_Loader(args.coords).simplified_field()
start = time.time()
count = 0
badimage = 0
errors = 0
okimage = 0
points = list()
keys = ['image', 'lat', 'lon', 'alt', 'fov', 'north', 'east', 'south', 'west']
results = list()
for image in sorted(glob.glob(args.inputfolder + '*_1.tif')):
    count += 1
    try:
        result = {'image': image, 'error': list()}

        # check GPS
        gps_result = check_gps(image, args.ground, args.lower_flight_lvl, args.upper_flight_lvl, field)
        result['error'].extend(gps_result['error']) 
        for key in gps_result.keys():
            if key not in keys:
                keys.append(key)
            if key != 'error':
                if key in result:
                    print("DUPLICATE KEY : " + key)
                result[key] = gps_result[key]

        # check blurry
        # TODO SUXING CODE HERE

        # check result of image
        if len(result['error']) > 0:
            badimage += 1
        else:
            okimage += 1

        # store result for later
        results.append(result)
    except ValueError as e:
        errors += 1
        print("ERROR PROCESSING %s : %s" % (image, e.message))
    except subprocess.CalledProcessError as e:
        errors += 1
        print("ERROR PROCESSING %s : %s" % (image, e.message))
print('processed %d images (%d ok, %d bad %d errors) in %f seconds.' % (count, okimage, badimage, errors, time.time() - start))

# check number of images/plot
# TODO JEROME CODE HERE

# create outputs
create_log('gps_check.log', results)
create_csv('gps_check.csv', results, keys)
create_map('gps_check.html', results, field, boundaries=True, tiles=True)
create_json('gps_check.json', results, keys, field)
