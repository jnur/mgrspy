# -*- coding: utf-8 -*-

"""
***************************************************************************
    mgrs.py
    ---------------------
    Date                 : August 2016
    Copyright            : (C) 2016 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Alexander Bruy'
__date__ = 'August 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import math

from osgeo import osr


ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LETTERS = {l: c for c, l in enumerate(ALPHABET)}

ONEHT = 100000.0
TWOMIL = 2000000.0

MIN_EASTING = 100000
MAX_EASTING = 900000
MIN_NORTHING = 0
MAX_NORTHING = 10000000
MAX_PRECISION = 5                    # Maximum precision of easting & northing
MIN_EAST_NORTH = 0
MAX_EAST_NORTH = 4000000

UPS_Constants = {0: [LETTERS['A'], LETTERS['J'], LETTERS['Z'], LETTERS['Z'], 800000.0, 800000.0],
                 1: [LETTERS['B'], LETTERS['A'], LETTERS['R'], LETTERS['Z'], 2000000.0, 800000.0],
                 2: [LETTERS['Y'], LETTERS['J'], LETTERS['Z'], LETTERS['P'], 800000.0, 1300000.0],
                 3: [LETTERS['Z'], LETTERS['A'], LETTERS['J'], LETTERS['P'], 2000000.0, 1300000.0]
                }


class MgrsException(Exception):
    pass


def wgsToMgrs(latitude, longitude, precision):
    """ Converts geodetic (latitude and longitude) coordinates to an MGRS
    coordinate string, according to the current ellipsoid parameters.

    @param latitude - latitude value
    @param longitude - longitude value
    @param precision - precision level of MGRS string
    @returns - MGRS coordinate string
    """
    if math.fabs(latitude) > 90:
        raise MgrsException('Latitude outside of valid range (-90 to 90 degrees).')

    if (longitude < -180) or (longitude > 360):
        raise MgrsException('Longitude outside of valid range (-180 to 360 degrees).')

    if (precision < 0) or (precision > MAX_PRECISION):
        raise MgrsException('The precision must be between 0 and 5 inclusive.')

    if (latitude < -80) or (latitude > 84):
        # Convert to UPS
        hemisphere, zone, epsg = _epsgForWgs(latitude, longitude)
        src = osr.SpatialReference()
        src.ImportFromEPSG(4326)
        dst = osr.SpatialReference()
        dst.ImportFromEPSG(epsg)
        ct = osr.CoordinateTransformation(src, dst)
        x, y, z = ct.TransformPoint(longitude, latitude)
        mgrs = upsToMgrs(hemisphere, x, y, precision)
    else:
        # Convert to UTM
        pass

    return mgrs


def upsToMgrs(hemisphere, easting, northing, precision):
    """ Converts UPS (hemisphere, easting, and northing) coordinates
    to an MGRS coordinate string.

    @param hemisphere - hemisphere either 'N' or 'S'
    @param easting - easting/X in meters
    @param northing - northing/Y in meters
    @param precision - precision level of MGRS string
    @returns - MGRS coordinate string
    """
    if hemisphere not in ['N', 'S']:
        raise MgrsException('Invalid hemisphere ("N" or "S").')

    if (easting < MIN_EAST_NORTH) or (easting > MAX_EAST_NORTH):
        raise MgrsException('Easting outside of valid range (100,000 to 900,000 meters for UTM, 0 to 4,000,000 meters for UPS).')

    if (northing < MIN_EAST_NORTH) or (northing > MAX_EAST_NORTH):
        raise MgrsException('Northing outside of valid range (0 to 10,000,000 meters for UTM, 0 to 4,000,000 meters for UPS).')

    if (precision < 0) or (precision > MAX_PRECISION):
        raise MgrsException('The precision must be between 0 and 5 inclusive.')

    mgrsLetters = [None, None, None]
    if hemisphere == 'N':
        if easting >= TWOMIL:
            mgrsLetters[0] = LETTERS['Z']
        else:
            mgrsLetters[0] = LETTERS['Y']

        idx = mgrsLetters[0] - 22
        ltr2LowValue = UPS_Constants[idx][1]
        falseEasting = UPS_Constants[idx][4]
        falseNorthing = UPS_Constants[idx][5]
    else:
        if easting >= TWOMIL:
            mgrsLetters[0] = LETTERS['B']
        else:
            mgrsLetters[0] = LETTERS['A']

        ltr2LowValue = UPS_Constants[0][1]
        falseEasting = UPS_Constants[0][4]
        falseNorthing = UPS_Constants[0][5]

    gridNorthing = northing
    gridNorthing = gridNorthing - falseNorthing

    mgrsLetters[2] = int(gridNorthing / ONEHT)

    if mgrsLetters[2] > LETTERS['H']:
        mgrsLetters[2] = mgrsLetters[2] + 1

    if mgrsLetters[2] > LETTERS['N']:
        mgrsLetters[2] = mgrsLetters[2] + 1

    gridEasting = easting
    gridEasting = gridEasting - falseEasting;
    mgrsLetters[1] = ltr2LowValue + int(gridEasting / ONEHT)

    if easting < TWOMIL:
        if mgrsLetters[1] > LETTERS['L']:
            mgrsLetters[1] = mgrsLetters[1] + 3

        if mgrsLetters[1] > LETTERS['U']:
            mgrsLetters[1] = mgrsLetters[1] + 2
    else:
        if mgrsLetters[1] > LETTERS['C']:
            mgrsLetters[1] = mgrsLetters[1] + 2

        if mgrsLetters[1] > LETTERS['H']:
            mgrsLetters[1] = mgrsLetters[1] + 1

        if mgrsLetters[1] > LETTERS['L']:
            mgrsLetters[1] = mgrsLetters[1] + 3

    return mgrsString(0, mgrsLetters, easting, northing, precision)

def utmToMgrs():
    pass


def mgrsString(zone, mgrsLetters, easting, northing, precision):
    """ Constructs an MGRS string from its component parts
    @param zone - UTM zone
    @param letters - MGRS coordinate string letters
    @param easting - easting value
    @param northing - northing value
    @param precision - precision level of MGRS string
    @returns - MGRS coordinate string
    """
    mrgs = ''
    if zone:
        mgrs = unicode(zone)
    else:
        mgrs = '  '

    for i in xrange(3):
        mgrs += ALPHABET[mgrsLetters[i]]

    divisor = math.pow(10.0, 5 - precision)
    easting = math.fmod(easting, 100000.0)
    if easting >= 99999.5:
        easting = 99999.0
    east = int(easting / divisor)
    mgrs += unicode(east)[:precision]

    northing = math.fmod(northing, 100000.0)
    if northing >= 99999.5:
        northing = 99999.0
    north = int(northing / divisor)
    mgrs += unicode(north)[:precision]

    return mgrs


def _epsgForWgs(latitude, longitude):
    """ Returns corresponding UTM or UPS EPSG code from WGS84 coordinates
    @param latitude - latitude value
    @param longitude - longitude value
    @returns - EPSG code
    """

    if math.fabs(latitude) > 90 or math.fabs(longitude) > 180:
        return None

    # hemisphere
    if latitude < 0:
        hemisphere = 'S'
    else:
        hemisphere = 'N'

    # UTM zone
    if latitude <= -80 or latitude >= 84:
        # Coordinates falls under UPS system
        zone = 61
    else:
        # Coordinates falls under UTM system
        #~ zone = int(longitude / 6.0) + 30
#~
        #~ # -180 special case
        #~ if zone == 0:
            #~ zone = 60
        if longitude < 180:
            zone = int(31 + (longitude / 6.0))
        else:
            zone = int((longitude / 6) - 29)

        if zone > 60:
            zone = 1

        # Handle UTM special cases
        if (latitude > 55) and (latitude < 63) and (longitude > -1) and (longitude < 3):
            zone = 31
        elif (latitude > 55) and (latitude < 64) and (longitude > 2) and (longitude < 12):
            zone = 32
        elif (latitude > 71) and (longitude > -1) and (longitude < 9):
            zone = 31
        elif (latitude > 71) and (longitude > 8) and (longitude < 21):
            zone = 33
        elif (latitude > 71) and (longitude > 20) and (longitude < 33):
            zone = 35
        elif (latitude > 71) and (longitude > 32) and (longitude < 42):
            zone = 37

    # North or South
    if latitude >= 0:
        ns = 600
    else:
        ns = 700

    return hemisphere, zone, 32000 + ns + zone
