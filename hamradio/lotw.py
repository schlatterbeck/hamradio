#!/usr/bin/python
# Copyright (C) 2019 Dr. Ralf Schlatterbeck Open Source Consulting.
# Reichergasse 131, A-3411 Weidling.
# Web: http://www.runtux.com Email: office@runtux.com
# ****************************************************************************
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS
# IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# ****************************************************************************

from __future__ import print_function

import io
import sys
from argparse        import ArgumentParser
from rsclib.pycompat import text_type
from hamradio        import requester
from hamradio.adif   import ADIF
try :
    from urllib.parse import urlencode
except ImportError:
    from urllib   import quote as quote_plus
    from urllib   import urlencode

class LOTW_Query (requester.Requester) :

    url = 'https://lotw.arrl.org/lotwuser/lotwreport.adi'
    date_format = '%Y-%m-%d.%H:%M:%S'

    def __init__ (self, username, password = None) :
        self.__super.__init__ (self.url, username, password)
    # end def __init__

    def get_qso (self, since = None, **args) :
        """ Get QSOs for the given parameters.
            Parameters are automagically prefixed with 'qso_'
            Allowed values according to
            https://lotw.arrl.org/lotw-help/developer-query-qsos-qsls/
            are owncall, callsign, mode, band, startdate, starttime,
            enddate, endtime, mydetail, withown.
            Note that the 'since' parameter specifies the date QSO were
            uploaded to LOTW, not the startdate/starttime of the QSO.
            We directly return an ADIF object.
        """
        d = {}
        for a in args :
            d ['qso_' + a] = args [a]
        d ['login']          = self.username
        d ['password']       = self.get_pw ()
        d ['qso_qsl']        = 'no'
        d ['qso_query']      = 1
        if since :
            d ['qso_qsorxsince'] = since.strftime ('%Y-%m-%d')
        t = self.get ('?' + urlencode (d), as_text = True)
        with io.StringIO (t) as f :
            adif = ADIF (f)
        return adif
    # end def get_qso

    def get_qsl (self, since = None, **args) :
        """ Get QSLs for the given parameters.
            Parameters are automagically prefixed with 'qso_'
            according the the lotw API.
            Allowed values according to
            https://lotw.arrl.org/lotw-help/developer-query-qsos-qsls/
            are owncall, callsign, mode, band, startdate, starttime,
            enddate, endtime, mydetail, withown.
            Note that the 'since' parameter specifies the date QSL were
            uploaded to LOTW, not the startdate/starttime of the QSO.
            We directly return an ADIF object.
        """
        d = {}
        for a in args :
            d ['qso_' + a] = args [a]
        d ['login']          = self.username
        d ['password']       = self.get_pw ()
        d ['qso_qsl']        = 'yes'
        d ['qso_query']      = 1
        if since :
            d ['qso_qslsince'] = since.strftime ('%Y-%m-%d')
        d ['qso_qsldetail']  = 'yes'
        t = self.get ('?' + urlencode (d), as_text = True)
        with io.StringIO (t) as f :
            adif = ADIF (f)
        return adif
    # end def get_qsl

# end class LOTW_Query
