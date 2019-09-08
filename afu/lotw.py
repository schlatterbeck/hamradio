#!/usr/bin/python
from __future__ import print_function

import io
import sys
from argparse        import ArgumentParser
from rsclib.pycompat import text_type
from afu             import requester
from afu.adif        import ADIF
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
