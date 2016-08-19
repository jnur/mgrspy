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
import itertools

from osgeo import osr


LETTERS = {l: c for c, l in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}

ONEHT = 100000.0
TWOMIL = 2000000.0

MAX_PRECISION = 5         # Maximum precision of easting & northing
MIN_EAST_NORTH = 0
MAX_EAST_NORTH = 4000000

# letter, 2nd letter range - low, 2nd letter range - high, 3rd letter range - high (UPS), false easting based on 2nd letter, false northing based on 3rd letter
UPS_Constants = {0: (LETTERS['A'], LETTERS['J'], LETTERS['Z'], LETTERS['Z'], 800000.0, 800000.0),
                 1: (LETTERS['B'], LETTERS['A'], LETTERS['R'], LETTERS['Z'], 2000000.0, 800000.0),
                 2: (LETTERS['Y'], LETTERS['J'], LETTERS['Z'], LETTERS['P'], 800000.0, 1300000.0),
                 3: (LETTERS['Z'], LETTERS['A'], LETTERS['J'], LETTERS['P'], 2000000.0, 1300000.0)
                }

# letter, minimum northing, upper latitude, lower latitude, northing offset
Latitude_Bands = [(LETTERS['C'], 1100000.0, -72.0, -80.5, 0.0),
                  (LETTERS['D'], 2000000.0, -64.0, -72.0, 2000000.0),
                  (LETTERS['E'], 2800000.0, -56.0, -64.0, 2000000.0),
                  (LETTERS['F'], 3700000.0, -48.0, -56.0, 2000000.0),
                  (LETTERS['G'], 4600000.0, -40.0, -48.0, 4000000.0),
                  (LETTERS['H'], 5500000.0, -32.0, -40.0, 4000000.0),
                  (LETTERS['J'], 6400000.0, -24.0, -32.0, 6000000.0),
                  (LETTERS['K'], 7300000.0, -16.0, -24.0, 6000000.0),
                  (LETTERS['L'], 8200000.0, -8.0, -16.0, 8000000.0),
                  (LETTERS['M'], 9100000.0, 0.0, -8.0, 8000000.0),
                  (LETTERS['N'], 0.0, 8.0, 0.0, 0.0),
                  (LETTERS['P'], 800000.0, 16.0, 8.0, 0.0),
                  (LETTERS['Q'], 1700000.0, 24.0, 16.0, 0.0),
                  (LETTERS['R'], 2600000.0, 32.0, 24.0, 2000000.0),
                  (LETTERS['S'], 3500000.0, 40.0, 32.0, 2000000.0),
                  (LETTERS['T'], 4400000.0, 48.0, 40.0, 4000000.0),
                  (LETTERS['U'], 5300000.0, 56.0, 48.0, 4000000.0),
                  (LETTERS['V'], 6200000.0, 64.0, 56.0, 6000000.0),
                  (LETTERS['W'], 7000000.0, 72.0, 64.0, 6000000.0),
                  (LETTERS['X'], 7900000.0, 84.5, 72.0, 6000000.0)]


class MgrsException(Exception):
    pass


def toMgrs(latitude, longitude, precision):
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

    hemisphere, zone, epsg = _epsgForWgs(latitude, longitude)
    src = osr.SpatialReference()
    src.ImportFromEPSG(4326)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(epsg)
    ct = osr.CoordinateTransformation(src, dst)
    x, y, z = ct.TransformPoint(longitude, latitude)

    if (latitude < -80) or (latitude > 84):
        # Convert to UPS
        mgrs = _upsToMgrs(hemisphere, x, y, precision)
    else:
        # Convert to UTM
        mgrs = _utmToMgrs(zone, hemisphere, latitude, longitude, x, y, precision)

    return mgrs


def toWgs(mgrs):
    """ Converts an MGRS coordinate string to geodetic (latitude and longitude)
    coordinates

    @param mgrs - MGRS coordinate string
    @returns - tuple containning latitude and longitude values
    """
    if _checkZone(mgrs):
        zone, hemisphere, easting, northing = _mgrsToUtm(mgrs)
    else:
        zone, hemisphere, easting, northing = _mgrsToUps(mgrs)

    epsg = _epsgForUtm(zone, hemisphere)
    src = osr.SpatialReference()
    src.ImportFromEPSG(epsg)
    dst = osr.SpatialReference()
    dst.ImportFromEPSG(4326)
    ct = osr.CoordinateTransformation(src, dst)
    longitude, latitude, z = ct.TransformPoint(easting, northing)

    return latitude, longitude


def _upsToMgrs(hemisphere, easting, northing, precision):
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

    return _mgrsString(0, mgrsLetters, easting, northing, precision)


def _mgrsToUps(mgrs):
    """ Converts an MGRS coordinate string to UTM projection (zone, hemisphere,
    easting and northing) coordinates

    @param mgrs - MGRS coordinate string
    @returns - tuple containing UTM zone, hemisphere, easting and northing
    """
    zone, mgrsLetters, easting, northing, precision = _breakMgrsString(mgrs)

    if zone != 0:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    if mgrsLetters[0] >= LETTERS['Y']:
        hemisphere = 'N'

        idx = mgrsLetters[0] - 22
        ltr2LowValue = UPS_Constants[idx][1]
        ltr2HighValue = UPS_Constants[idx][2]
        ltr3HighValue = UPS_Constants[idx][3]
        falseEasting = UPS_Constants[idx][4]
        falseNorthing = UPS_Constants[idx][5]
    else:
        hemisphere = 'S'

        ltr2LowValue = UPS_Constants[0][1]
        ltr2HighValue = UPS_Constants[0][2]
        ltr3HighValue = UPS_Constants[0][3]
        falseEasting = UPS_Constants[0][4]
        falseNorthing = UPS_Constants[0][5]

    # Check that the second letter of the MGRS string is within the range
    # of valid second letter values. Also check that the third letter is valid
    invalid = [LETTERS['D'], LETTERS['E'], LETTERS['M'], LETTERS['N'], LETTERS['V'], LETTERS['W']]
    if (mgrsLetters[1] < ltr2LowValue) or (mgrsLetters[1] > ltr2HighValue) or (mgrsLetters[1] in []) or (mgrsLetters[2] > ltr3HighValue):
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    gridNorthing = float(mgrsLetters[2] * ONEHT + falseNorthing)
    if mgrsLetters[2] > LETTERS['I']:
        gridNorthing = gridNorthing - ONEHT

    if mgrsLetters[2] > LETTERS['O']:
        gridNorthing = gridNorthing - ONEHT

    gridEasting = float((mgrsLetters[1] - ltr2LowValue) * ONEHT + falseEasting)
    if ltr2LowValue != LETTERS['A']:
        if mgrsLetters[1] > LETTERS['L']:
            gridEasting = gridEasting - 300000.0

        if mgrsLetters[1] > LETTERS['U']:
            gridEasting = gridEasting - 200000.0
    else:
        if mgrsLetters[1] > LETTERS['C']:
            gridEasting = gridEasting - 200000.0

        if mgrsLetters[1] > LETTERS['I']:
            gridEasting = gridEasting - ONEHT

        if mgrsLetters[1] > LETTERS['L']:
            gridEasting = gridEasting - 300000.0

    easting += gridEasting
    northing += gridNorthing

    return zone, hemisphere, easting, northing


def _utmToMgrs(zone, hemisphere, latitude, longitude, easting, northing, precision):
    """ Calculates an MGRS coordinate string based on the UTM zone, latitude,
    easting and northing values.

    @param zone - UTM zone number
    @param hemisphere - hemisphere either 'N' or 'S'
    @param latitude - latitude value
    @param longitude - longitude value
    @param easting - easting/X in meters
    @param northing - northing/Y in meters
    @param precision - precision level of MGRS string
    @returns - MGRS coordinate string
    """
    # Special check for rounding to (truncated) eastern edge of zone 31V
    # TODO: do we really need this?
    if (zone == 31) and (((latitude >= 56.0) and (latitude < 64.0)) and ((longitude >= 3.0) or (easting >= 500000.0))):
        pass

    if latitude <= 0.0 and northing == 1.0e7:
        latitude = 0
        northing = 0

    ltr2LowValue, ltr2HighValue, patternOffset = _gridValues(zone)

    mgrsLetters = [_latitudeLetter(latitude), None, None]

    while northing >= TWOMIL:
        northing = northing - TWOMIL

    northing += patternOffset
    if northing >= TWOMIL:
        northing = northing - TWOMIL

    mgrsLetters[2] = int(northing / ONEHT)
    if mgrsLetters[2] > LETTERS['H']:
        mgrsLetters[2] += 1

    if mgrsLetters[2] > LETTERS['N']:
        mgrsLetters[2] += 1

    if ((mgrsLetters[0] == LETTERS['V']) and (zone == 31)) and (easting == 500000.0):
        easting = easting - 1.0  # Substract 1 meter

    mgrsLetters[1] = ltr2LowValue + int((easting / ONEHT) - 1)
    if ltr2LowValue == LETTERS['J'] and mgrsLetters[1] > LETTERS['N']:
        letters[1] += 1

    return _mgrsString(zone, mgrsLetters, easting, northing, precision)


def _mgrsToUtm(mgrs):
    """ Converts an MGRS coordinate string to UTM projection (zone, hemisphere,
    easting and northing) coordinates.

    @param mgrs - MGRS coordinate string
    @returns - tuple containing UTM zone, hemisphere, easting, northing
    """
    zone, mgrsLetters, easting, northing, precision = _breakMgrsString(mgrs)
    if zone == 0:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    if mgrsLetters == LETTERS['X'] and zone in [32, 34, 36]:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    if mgrsLetters[0] < LETTERS['N']:
        hemisphere = 'S'
    else:
        hemisphere = 'N'

    ltr2LowValue, ltr2HighValue, patternOffset = _gridValues(zone)

    # Check that the second letter of the MGRS string is within the range
    # of valid second letter values. Also check that the third letter is valid
    if (mgrsLetters[1] < ltr2LowValue) or (mgrsLetters[1] > ltr2HighValue) or (mgrsLetters[2] > LETTERS['V']):
        raise  MgrsException('An MGRS string error: string too long, too short, or badly formed')

    rowLetterNorthing = float(mgrsLetters[2] * ONEHT)
    gridEasting = float((mgrsLetters[1] - ltr2LowValue + 1) * ONEHT)
    if ltr2LowValue == LETTERS['J'] and mgrsLetters[1] > LETTERS['O']:
        gridEasting = gridEasting - ONEHT

    if mgrsLetters[2] > LETTERS['O']:
        rowLetterNorthing = rowLetterNorthing - ONEHT

    if mgrsLetters[2] > LETTERS['I']:
        rowLetterNorthing = rowLetterNorthing - ONEHT

    if rowLetterNorthing >= TWOMIL:
        rowLetterNorthing = rowLetterNorthing - TWOMIL

    minNorthing, northingOffset = _latitudeBandMinNorthing(mgrsLetters[0])

    gridNorthing = rowLetterNorthing - patternOffset
    if gridNorthing < 0:
        gridNorthing += TWOMIL

    gridNorthing += northingOffset

    if gridNorthing < minNorthing:
        gridNorthing += TWOMIL

    easting += gridEasting
    northing += gridNorthing

    return zone, hemisphere, easting, northing


def _mgrsString(zone, mgrsLetters, easting, northing, precision):
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
        tmp = unicode(zone)
        mgrs = tmp.zfill(3 - len(tmp))
    else:
        mgrs = '  '

    for i in xrange(3):
        mgrs += LETTERS.keys()[LETTERS.values().index(mgrsLetters[i])]

    easting = math.fmod(round(easting, 1), 100000.0)
    if easting >= 99999.5:
        easting = 99999.0
    mgrs += unicode(int(easting)).rjust(5, '0')[:precision]

    northing = math.fmod(round(northing, 1), 100000.0)
    if northing >= 99999.5:
        northing = 99999.0
    mgrs += unicode(int(northing)).rjust(5, '0')[:precision]

    return mgrs


def _epsgForWgs(latitude, longitude):
    """ Returns corresponding UTM or UPS EPSG code from WGS84 coordinates
    @param latitude - latitude value
    @param longitude - longitude value
    @returns - tuple containing hemisphere, UTM zone and EPSG code
    """

    if math.fabs(latitude) > 90:
        raise MgrsException('Latitude outside of valid range (-90 to 90 degrees).')

    if longitude < -180 or longitude > 360:
        return MgrsException('Longitude outside of valid range (-180 to 360 degrees).')

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

    # North or South hemisphere
    if latitude >= 0:
        ns = 600
    else:
        ns = 700

    return hemisphere, zone, 32000 + ns + zone


def _epsgForUtm(zone, hemisphere):
    """ Returen EPSG code for given UTM zone and hemisphere

    @param zone - UTM zone
    @param hemisphere - hemisphere either 'N' or 'S'
    @returns - corresponding EPSG code
    """
    if hemisphere not in ['N', 'S']:
        raise MgrsException('Invalid hemisphere ("N" or "S").')

    if zone < 0 or zone > 60:
        raise MgrsException('UTM zone ouside valid range.')

    if hemisphere == 'N':
        ns = 600
    else:
        ns = 700

    if zone == 0:
        zone = 61

    return 32000 + ns + zone


def _gridValues(zone):
    """ Sets the letter range used for the 2nd letter in the MGRS coordinate
    string, based on the set number of the UTM zone. It also sets the pattern
    offset using a value of A for the second letter of the grid square, based
    on the grid pattern and set number of the UTM zone.

    @param zone - UTM zone number
    @returns - tuple containing 2nd letter low number, 2nd letter high number
    and pattern offset
    """
    setNumber = zone % 6

    if not setNumber:
        setNumber = 6

    if setNumber in [1, 4]:
        ltr2LowValue = LETTERS['A']
        ltr2HighValue = LETTERS['H']
    elif setNumber in [2, 5]:
        ltr2LowValue = LETTERS['J']
        ltr2HighValue = LETTERS['R']
    elif setNumber in [3, 6]:
        ltr2LowValue = LETTERS['S']
        ltr2HighValue = LETTERS['Z']

    if setNumber % 2:
        patternOffset = 0.0
    else:
        patternOffset = 500000.0

    return ltr2LowValue, ltr2HighValue, patternOffset


def _latitudeLetter(latitude):
    """ Returns the latitude band letter for given latitude

    @param latitude - latitude value
    @returns - latitude band letter
    """
    if latitude >= 72 and latitude < 84.5:
        return LETTERS['X']
    elif latitude > -80.5 and latitude < 72:
        idx = int(((latitude + 80.0) / 8.0) + 1.0e-12)
        return Latitude_Bands[idx][0]


def _checkZone(mgrs):
    """ Checks if MGRS coordinate string contains UTM zone definition

    @param mgrs - MGRS coordinate string
    @returns - True if zone is given, False otherwise
    """
    mgrs = mgrs.lstrip()
    count = sum(1 for c in itertools.takewhile(str.isdigit, mgrs))
    if count <= 2:
        return count > 0
    else:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')


def _breakMgrsString(mgrs):
    """ Breaks down an MGRS coordinate string into its component parts.

    @param mgrs - MGRS coordinate string
    @returns - tuple containing MGRS string componets: UTM zone,
    MGRS coordinate string letters, easting, northing and precision
    """
    mgrs = mgrs.lstrip()
    # Number of zone digits
    count = sum(1 for c in itertools.takewhile(str.isdigit, mgrs))
    if count <= 2:
        if count > 0:
            zone = int(mgrs[:2])
            if zone < 1 or zone > 60:
                raise MgrsException('An MGRS string error: string too long, too short, or badly formed')
        else:
            zone = 0
    else:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    idx = count
    # MGRS letters
    count = sum(1 for c in itertools.takewhile(str.isalpha, itertools.islice(mgrs, idx, None)))
    if count == 3:
        a = ord('A')
        invalid = [LETTERS['I'], LETTERS['O']]

        mgrsLetters = []
        ch = ord(mgrs[idx:idx + 1].upper()) - a
        if ch in invalid:
            raise MgrsException('An MGRS string error: string too long, too short, or badly formed')
        idx += 1
        mgrsLetters.append(ch)

        ch = ord(mgrs[idx:idx + 1].upper()) - a
        if ch in invalid:
            raise MgrsException('An MGRS string error: string too long, too short, or badly formed')
        idx += 1
        mgrsLetters.append(ch)

        ch = ord(mgrs[idx:idx + 1].upper()) - a
        if ch in invalid:
            raise MgrsException('An MGRS string error: string too long, too short, or badly formed')
        idx += 1
        mgrsLetters.append(ch)
    else:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    # Easting and Northing
    count = sum(1 for c in itertools.takewhile(str.isdigit, itertools.islice(mgrs, idx, None)))
    if count <= 10 and count % 2 == 0:
        precision = count / 2
        if precision > 0:
            easting = float(mgrs[idx:idx + precision])
            northing = float(mgrs[idx + precision:])
        else:
            easting = 0
            northing = 0
    else:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    return zone, mgrsLetters, easting, northing, precision


def _latitudeBandMinNorthing(letter):
    """ Determines the minimum northing and northing offset
    for given latitude band letter.

    @param letter - latitude band letter
    @returns - tuple containing minimum northing and northing offset
    for that letter
    """
    if letter >= LETTERS['C'] and letter <= LETTERS['H']:
        minNorthing = Latitude_Bands[letter - 2][1]
        northingOffset = Latitude_Bands[letter - 2][4]
    elif letter >= LETTERS['J'] and letter <= LETTERS['N']:
        minNorthing = Latitude_Bands[letter - 3][1]
        northingOffset = Latitude_Bands[letter - 3][4]
    elif letter >= LETTERS['P'] and letter <= LETTERS['X']:
        minNorthing = Latitude_Bands[letter - 4][1]
        northingOffset = Latitude_Bands[letter - 4][4]
    else:
        raise MgrsException('An MGRS string error: string too long, too short, or badly formed')

    return minNorthing, northingOffset
