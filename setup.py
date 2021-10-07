#!/usr/bin/env python
# Copyright (C) 2019-21 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# All rights reserved
# ****************************************************************************
#
# This library is free software; you can redistribute it and/or modify
# it under the terms of the GNU Library General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Library General Public License for more details.
#
# You should have received a copy of the GNU Library General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
# ****************************************************************************

try :
    from hamradio.Version import VERSION
except :
    VERSION = None
from distutils.core import setup, Extension

license     = 'GNU Library or Lesser General Public License (LGPL)'
setup \
    ( name             = "hamradio"
    , version          = VERSION
    , description      = "Utilities for Ham radio"
    , license          = license
    , author           = "Ralf Schlatterbeck"
    , author_email     = "rsc@runtux.com"
    , install_requires = ['<rsclib>']
    , packages         = ['hamradio']
    , package_data     = dict
        (hamradio = ['data/*.txt', 'data/*.dat', 'data/*.html'])
    , platforms        = 'Any'
    , python_requires  = '>=3.6'
    , scripts          = [ 'bin/qso-import'
                         , 'bin/callsign_lookup'
                         , 'bin/qsl-export'
                         ]
    , url              = 'https://github.com/schlatterbeck/afu'
    , classifiers      =
        [ 'Development Status :: 5 - Production/Stable'
        , 'License :: OSI Approved :: ' + license
        , 'Operating System :: OS Independent'
        , 'Programming Language :: Python'
        , 'Intended Audience :: Developers'
        , 'Programming Language :: Python :: 2'
        , 'Programming Language :: Python :: 2.7'
        , 'Programming Language :: Python :: 3'
        , 'Programming Language :: Python :: 3.5'
        , 'Programming Language :: Python :: 3.6'
        , 'Programming Language :: Python :: 3.7'
        , 'Programming Language :: Python :: 3.8'
        , 'Programming Language :: Python :: 3.9'
        ]
    )
