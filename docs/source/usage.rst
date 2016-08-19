Using the mgrspy
================

All you need is to import mgrspy with following command:

::

    >>> from mgrspy import mgrs


Converting WGS84 to MGRS
------------------------

To convert WGS84 coordinates (latitude and longitude) to MGRS use ``toMrgs()``
function:

::

    >>> lat = 42.0
    >>> lon = -93.0
    >>> mgrs.toMgrs(lat, lon)
    '15TVG0000049776'

By default ``toMgrs()`` function returns MGRS string with maximum precision
level. If you need less precise result --- pass additional ``precision``
parameter:

::

    >>> lat = 42.0
    >>> lon = -93.0
    >>> mgrs.toMgrs(lat, lon, 3)
    '15TVG000497'
    >>> mgrs.toMgrs(lat, lon, 0)
    '15TVG'

If any of the passed values is outside of valid range or in case of errors
an ``MgrsException`` will be raised.

Convering MGRS to WGS84
-----------------------

To convert MGRS coordinate string to WGS84 coordinates (latitude and longitude)
use ``toWgs()`` function:

::

    >>> mgrs.toWgs('15TVG0000049776')
    (41.99364855788585, -94.20734290469866)

Function ``toWgs()`` supports different precision levels of MGRS coordinate
string:

::

    >>> mgrs.toWgs('15TVG000497')
    (41.54988934568494, -94.19904899028688)

If passed MGRS coordinate string is malformed or in case of errors an
 ``MgrsException`` will be raised.
