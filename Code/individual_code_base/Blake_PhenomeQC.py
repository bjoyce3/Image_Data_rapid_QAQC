
# coding: utf-8

# In[ ]:

#Test script
#python PhenomeQC.py -inputfolder /home/test_data/complete_RedEdge_69meters/ -coord "POLYGON((-87.005519 40.477489 , -87.000945 40.477490 , -87.000971 40.476615 , -87.005519 40.476634, -87.005519 40.477489))" -ground 200 -upper_flight_lvl 150 -lower_flight_lvl 50


# In[1]:

import argparse
import numpy
import os
import string
import sys


# In[16]:

#Establish args from command line
parser = argparse.ArgumentParser(description='Parses user input for PhenomeQC')
#Required arguments
parser.add_argument('-coords', required=True, help='Input file that contains the coordinates for the plot that has been flown. String of field plot in WKT.')
parser.add_argument('-camera', required=True, help='Type of camera used. Supported camera types: sequoia/parrot, rededge, rgb, hyperspectral. Inputs as a string.')
parser.add_argument('-ground', required=True, type=float, help='Ground level from ocean height in meters. Set as a double.')

#Optional arguments
parser.add_argument('--resolution', type=float, help='Resolution of bounding boxes on the ground. Changes the size of bounding box on the ground. Default == half a meter. Input as a double in meters.')
parser.add_argument('--upper_flight_lvl', type=float, help='Upper bounds on flight level measured as above ground level in meters. Set as a double.')
parser.add_argument('--lower_flight_lvl', type=float, help='Lower acceptable bound on flight level as above ground level in meters. Set as a double.')

args = parser.parse_args()


# In[17]:

parser.print_help()


# In[18]:

#Defined Functions

#Check functions for input
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
        
        if not isinstance(corner_1,tuple) or not isinstance(corner_2,tuple):
            raise Exception
        
        self.northwest = corner_1
        self.southeast = corner_2
        
        


class Field:
    '''
    Field class has all the GPS information of the Field
    Can split the field into several bounding box
    '''
    
    bounding_box = []
    
    def __init__(self, *args):
        if not args:
            raise FieldError
            
        self.raw_bounding_box = list(args)     
    
    def split_bounding_box(self):
        pass
    
    
    def simplified_field(self):
        '''
        Return the approximate bounding box of the field
        '''
        
        unzip_bounding_box = zip(*bounding_box)
        
        latitute = sorted(unzip_bounding_box[0])
        
        latitute_east, latitute_west = latitute[0], latitute[-1]
        
        longitude = sorted(unzip_bounding_box[-1])
        
        longitude_south, longitude_north = longitude[0], longitude[-1]
        
        return [(latitute_west, longitude_north),(latitute_east, longitude_south)]
        
    
    
    def get_bounding_box(self):
        
        if not bounding_box:
            raise FieldError("No bounding box information (you may need to split it beforehand)")
        
        return bounding_box
    
    
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
        


# In[ ]:




# In[ ]:

#Set global variables
input_directory = sys.argv[1] #directory path input
output_directory = sys.argv[-1] #directory path output

#Pass inputs into functions
field_coord = 

