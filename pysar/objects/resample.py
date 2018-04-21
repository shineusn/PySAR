############################################################
# Program is part of PySAR                                 #
# Copyright(c) 2018, Zhang Yunjun                          #
# Author:  Zhang Yunjun, 2018                              #
############################################################
# Recommended usage:
#     from pysar.objects.resample import resample


import sys
import numpy as np
import pyresample as pr
from pysar.utils import readfile


class resample:
    """
    Geometry Definition objects for geocoding using pyresample (http://pyresample.readthedocs.org)

    Example:
        resObj = resample(lookupFile='./INPUTS/geometryRadar.h5')
        resObj = resample(lookupFile='./INPUTS/geometryGeo.h5', dataFile='velocity.h5')
    """
    def __init__(self, lookupFile, dataFile=None, SNWE=None, laloStep=None):
        self.file = lookupFile
        self.dataFile = dataFile
        self.SNWE = SNWE
        self.laloStep = laloStep


    def get_geometry_definition(self):
        self.lut_metadata = readfile.read_attribute(self.file)
        self.src_metadata = readfile.read_attribute(self.dataFile)

        if 'Y_FIRST' in self.lut_metadata.keys():
            src_def, dest_def = self.get_geometry_definition4geo_lookup_table()
        else:
            src_def, dest_def = self.get_geometry_definition4radar_lookup_table()
        return src_def, dest_def, self.SNWE


    def get_geometry_definition4radar_lookup_table(self):
        '''Get src_def and dest_def for lookup table from ISCE, DORIS'''

        # radar2geo
        if 'Y_FIRST' not in self.src_metadata.keys():
            # src_def
            src_lat = readfile.read(self.file, datasetName='latitude')[0]
            src_lon = readfile.read(self.file, datasetName='longitude')[0]
            src_def = pr.geometry.SwathDefinition(lons=src_lon, lats=src_lat)

            # laloStep
            SNWE = (np.nanmin(src_lat), np.nanmax(src_lat), np.nanmin(src_lon), np.nanmax(src_lon))
            if self.laloStep is None:
                self.laloStep = ((SNWE[0] - SNWE[1]) / src_lat.shape[0], (SNWE[3] - SNWE[2]) / src_lat.shape[1])
            else:
                self.laloStep = (-1.*abs(self.laloStep[0]), 1.*abs(self.laloStep[1]))
            print('output pixel size in (lat, lon) in degree: {}'.format(self.laloStep))

            # SNWE
            if self.SNWE is None:
                self.SNWE = SNWE
            print('output area extent in (S N W E) in degree: {}'.format(self.SNWE))

            # dest_def
            dest_lat = np.arange(self.SNWE[1], self.SNWE[0], self.laloStep[0])
            dest_lon = np.arange(self.SNWE[2], self.SNWE[3], self.laloStep[1])
            dest_def = pr.geometry.GridDefinition(lons=np.tile(dest_lon.reshape(1, -1), (dest_lat.size, 1)),
                                                  lats=np.tile(dest_lat.reshape(-1, 1), (1, dest_lon.size)))

        # geo2radar
        else:
            # dest_def
            dest_lat = readfile.read(self.file, datasetName='latitude')[0]
            dest_lon = readfile.read(self.file, datasetName='longitude')[0]
            dest_def = pr.geometry.GridDefinition(lons=dest_lon, lats=dest_lat)

            # src_def
            lat0 = float(self.src_metadata['Y_FIRST'])
            lon0 = float(self.src_metadata['X_FIRST'])
            lat_step = float(self.src_metadata['Y_STEP'])
            lon_step = float(self.src_metadata['X_STEP'])
            lat_num = int(self.src_metadata['LENGTH'])
            lon_num = int(self.src_metadata['WIDTH'])
            lat1 = lat0 + lat_step * (lat_num - 1)
            lon1 = lon0 + lon_step * (lon_num - 1)

            src_lat, src_lon = np.mgrid[lat0:lat1:lat_num*1j, lon0:lon1:lon_num*1j]
            src_def = pr.geometry.SwathDefinition(lons=src_lon, lats=src_lat)

        return src_def, dest_def


    def get_geometry_definition4geo_lookup_table(self):
        '''Get src_def and dest_def for lookup table from Gamma and ROI_PAC.'''
        def project_yx2lalo(yy, xx, SNWE, laloStep):
            """scale/project coordinates in pixel number into lat/lon based on bbox and step"""
            lats = SNWE[1] + yy * laloStep[0]
            lons = SNWE[2] + xx * laloStep[1]
            lats[np.isnan(lats)] = 90.
            lats[np.isnan(lons)] = 90.
            lons[lats==90.] = 0
            return lats, lons

        # radar2geo
        if 'Y_FIRST' not in self.src_metadata.keys():
            lat0 = float(self.lut_metadata['Y_FIRST'])
            lon0 = float(self.lut_metadata['X_FIRST'])
            lat_step = float(self.lut_metadata['Y_STEP'])
            lon_step = float(self.lut_metadata['X_STEP'])
            lat_num = int(self.lut_metadata['LENGTH'])
            lon_num = int(self.lut_metadata['WIDTH'])

            # laloStep
            if self.laloStep is None:
                self.laloStep = (lat_step, lon_step)
            else:
                self.laloStep = (-1.*abs(self.laloStep[0]), 1.*abs(self.laloStep[1]))
            print('output pixel size in (lat, lon) in degree: {}'.format(self.laloStep))

            # SNWE
            if self.SNWE is None:
                self.SNWE = (lat0 + lat_step * lat_num, lat0, lon0, lon0 + lon_step * lon_num)
                dest_box = None
            else:
                dest_box = ((self.SNWE[2] - lon0) / lon_step, (self.SNWE[1] - lat0) / lat_step,
                            (self.SNWE[3] - lon0) / lon_step, (self.SNWE[0] - lat0) / lat_step,)
            print('output area extent in (S N W E) in degree: {}'.format(self.SNWE))

            # src_y/x
            length = int(self.src_metadata['LENGTH'])
            width = int(self.src_metadata['WIDTH'])
            src_y, src_x = np.mgrid[0:length-1:length*1j, 0:width-1:width*1j]

            # dest_y/x
            dest_y = readfile.read(self.file, datasetName='azimuthCoord', box=dest_box)[0]
            dest_x = readfile.read(self.file, datasetName='rangeCoord', box=dest_box)[0]
            if 'SUBSET_XMIN' in self.src_metadata.keys():
                print('input data file was cropped before.')
                dest_y[dest_y!=0.] -= float(self.src_metadata['SUBSET_YMIN'])
                dest_x[dest_x!=0.] -= float(self.src_metadata['SUBSET_XMIN'])

            # Convert y/x to lat/lon to be able to use pyresample.geometryDefinition
            idx_row, idx_col = np.where(np.multiply(np.multiply(dest_y > 0, dest_y < length+1),
                                                    np.multiply(dest_x > 0, dest_x < width+1)))
            SNWEcomm = (np.max(idx_row) * lat_step + lat0,
                        np.min(idx_row) * lat_step + lat0,
                        np.min(idx_col) * lon_step + lon0,
                        np.max(idx_col) * lon_step + lon0)
            laloStep = [(SNWEcomm[0] - SNWEcomm[1]) / length, (SNWEcomm[3] - SNWEcomm[2]) / width]
            # print('converting az/rgCoord to lat/lon based on common SNWE: {}'.format(SNWEcomm))
            src_lat, src_lon = project_yx2lalo(src_y, src_x, SNWEcomm, laloStep)
            dest_y[dest_y==0.] = np.nan
            dest_x[dest_x==0.] = np.nan
            dest_lat, dest_lon = project_yx2lalo(dest_y, dest_x, SNWEcomm, laloStep)

        # geo2radar
        else:
            # src_y/x
            print('Not implemented yet for GAMMA and ROIPAC products')
            sys.exit(-1)
            

        # src_def and dest_def
        src_def = pr.geometry.SwathDefinition(lons=src_lon, lats=src_lat)
        dest_def = pr.geometry.GridDefinition(lons=dest_lon, lats=dest_lat)
        return src_def, dest_def


    def resample(self, data, src_def, dest_def, interp_method='nearest', fill_value=np.nan, nprocs=None, print_msg=True):
        """
        Resample input radar coded data into geocoded data
        Parameters: data : 2D np.array
                    src_def : pyresample.geometryDefinition objects
                    dest_def : pyresample.geometryDefinition objects
                    interp_method : str,
                    fill_value : number
                    nprocs : int
                    print_msg : bool
        Returns:    res_data
        Example:    res_data = reObj.resample(data, src_def, dest_def, interp_method=inps.interpMethod,\
                                              fill_value=np.fillValue, nprocs=4)
        """
        if 'Y_FIRST' in self.src_metadata.keys():
            radius = 100e3     # geo2radar
        else:
            radius = 200       # radar2geo

        if interp_method.startswith('near'):
            if print_msg:
                print('nearest resampling using {} processor cores ...'.format(nprocs))
            res_data = pr.kd_tree.resample_nearest(src_def, data, dest_def, nprocs=nprocs, fill_value=fill_value,\
                                                   radius_of_influence=radius, epsilon=0)
        elif interp_method.endswith('linear'):
            if print_msg:
                print('bilinear resampling using {} processor cores ...'.format(nprocs))
            res_data = pr.bilinear.resample_bilinear(data, src_def, dest_def, nprocs=nprocs, fill_value=fill_value,\
                                                     radius=radius, neighbours=32, epsilon=0, reduce_data=True)
        return res_data
