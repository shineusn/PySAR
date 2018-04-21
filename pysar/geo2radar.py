#!/usr/bin/env python3
############################################################
# Program is part of PySAR                                 #
# Copyright(c) 2017, Zhang Yunjun                          #
# Author:  Zhang Yunjun, 2017                              #
############################################################


import os
import sys
import time
import argparse
import warnings
import numpy as np
from pysar.utils import readfile, writefile, utils as ut
from pysar.objects.resample import resample

######################################################################################
EXAMPLE = """example:
  geo2radar.py geo_velocity.h5
"""


def create_parser():
    parser = argparse.ArgumentParser(description='Resample geocoded files into radar coordinates',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=EXAMPLE)

    parser.add_argument('file', nargs='+', help='File(s) to be resampled into radar coordinates')
    parser.add_argument('-d','--dset', help='dataset to read, for example:\n'+
                        'height                        for geometryRadar.h5\n'+
                        'unwrapPhase-20100114_20101017 for ifgramStack.h5')
    parser.add_argument('-l', '--lookup', dest='lookupFile',
                        help='Lookup table file generated by InSAR processors.')

    parser.add_argument('-i', '--interpolate', dest='interpMethod', choices={'nearest', 'bilinear'},
                        help='interpolation/resampling method. Default: nearest', default='nearest')
    parser.add_argument('--fill', dest='fillValue', type=float, default=np.nan,
                        help='Value used for points outside of the interpolation domain.\n' +
                             'Default: np.nan')

    parser.add_argument('-o', '--output', dest='outfile',
                        help="output file name. Default: add prefix 'geo_'")

    return parser


def cmd_line_parse(iargs=None):
    parser = create_parser()
    inps = parser.parse_args(args=iargs)

    inps.file = ut.get_file_list(inps.file)
    if not inps.file:
        sys.exit('ERROR: no input file found!')
    elif len(inps.file) > 1:
        inps.outfile = None

    inps.lookupFile = ut.get_lookup_file(inps.lookupFile)
    if not inps.lookupFile:
        sys.exit('ERROR: No lookup table found! Can not geocode without it.')

    return inps


############################################################################################
def update_attribute(atr_in, inps, print_msg=True):
    atr = dict(atr_in)
    length, width = inps.outShape[-2:]
    atr['LENGTH'] = length
    atr['WIDTH'] = width
    for i in ['Y_FIRST','X_FIRST','Y_STEP','X_STEP','Y_UNIT','X_UNIT',
              'REF_Y','REF_X','REF_LAT','REF_LON']:
        try:
            atr.pop(i)
        except:
            pass

    return atr


def run_geo2radar(infile, inps, res_obj, outfile=None):
    print('-' * 50)
    print('resample file: {}'.format(infile))

    # read source data
    data, atr = readfile.read(infile, datasetName=inps.dset)
    if len(data.shape) == 3:
        data = np.moveaxis(data, 0, -1)

    # resample source data into target data
    geo_data = res_obj.resample(data, inps.src_def, inps.dest_def,
                                inps.interpMethod, inps.fillValue)
    if len(geo_data.shape) == 3:
        geo_data = np.moveaxis(geo_data, -1, 0)

    # update metadata
    inps.outShape = geo_data.shape
    atr = update_attribute(atr, inps)

    # write to file
    if not outfile:
        outfile = os.path.join(os.path.dirname(infile), 'rdr_' + os.path.basename(infile))
    if inps.dset:
        atr['FILE_TYPE'] = inps.dset
    writefile.write(geo_data, atr, outfile, infile)

    return outfile


######################################################################################
def main(iargs=None):
    inps = cmd_line_parse(iargs)
    if inps.templateFile:
        inps = read_template2inps(inps.templateFile, inps)

    start_time = time.time()

    # Prepare geometry for geocoding
    res_obj = resample(lookupFile=inps.lookupFile, dataFile=inps.file[0], SNWE=inps.SNWE,
                       laloStep=inps.latStep)
    inps.src_def, inps.dest_def, inps.SNWE = res_obj.get_geometry_definition()

    # Geocode input files
    for infile in inps.file:
        run_geo2radar(infile, inps, res_obj, inps.outfile)

    print('Done.\ntime used: {:.2f} secs'.format(time.time() - start_time))
    return


######################################################################################
if __name__ == '__main__':
    main()