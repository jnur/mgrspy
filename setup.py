# -*- coding: utf-8 -*-

import codecs
from setuptools import setup

with codecs.open('README', encoding='utf-8') as f:
    readme_text = f.read()


setup(
    name='mgrspy',
    version='0.2.2',
    install_requires=['GDAL>=1.10.0', 'future'],
    author='Alexander Bruy',
    author_email='abruy@boundlessgeo.com',
    description='Convert WGS84 coordinates to MGRS and back',
    long_description=(readme_text),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: OS Independent',
        'Topic :: Scientific/Engineering :: GIS'
    ],
    license="GPLv2+",
    keywords='mgrs wgs gis coordinate conversion',
    url='https://github.com/boundlessgeo/mgrspy',
    package_dir={'': '.'},
    test_suite='tests.suite',
    packages=['mgrspy',]
)
