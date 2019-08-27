#!/usr/bin/python
from __future__ import print_function

import io
import requests
from argparse     import ArgumentParser
from datetime     import datetime
from netrc        import netrc
from getpass      import getpass
from afu          import requester
from afu.adif     import ADIF
from afu.dbimport import ADIF_Uploader
try :
    from urllib.parse import urlparse, quote_plus, urlencode
except ImportError:
    from urlparse import urlparse
    from urllib   import quote as quote_plus, urlencode

class LOTW_Query (requester.Requester) :

    url = 'https://lotw.arrl.org/lotwuser/lotwreport.adi'
    date_format = '%Y-%m-%d.%H:%M:%S'

    def __init__ (self, username, password = None) :
        self.__super.__init__ (self.url, username, password)
    # end def __init__

    def get_qso (self, since = '2010-01-01', **args) :
        """ Get QSOs for the given parameters.
            Parameters are automagically prefixed with 'qso_'
            Allowed values according to
            https://lotw.arrl.org/lotw-help/developer-query-qsos-qsls/
            are owncall, callsign, mode, band, startdate, starttime,
            enddate, endtime, mydetail, withown.
            Note that the 'since' parameter specifies the date QSO were
            uploaded to LOTW, not the startdate/starttime of the QSO.
        """
        d = {}
        for a in args :
            d ['qso_' + a] = args [a]
        d ['qso_qsl']        = 'no'
        d ['qso_query']      = 1
        d ['qso_qsorxsince'] = since
        d ['login']          = self.user
        d ['password']       = self.get_pw ()
        t = self.get ('?' + urlencode (d), as_text = True)
        return t
    # end def get_qso

# end class LOTW_Query

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "adif"
        , help    = "ADIF file to import"
        )
    cmd.add_argument \
        ( "-a", "--antenna"
        , help    = "Antenna to use for band, colon separated "
                    "band:antenna, later values override earlier values, "
                    "default=%(default)s"
        , action  = 'append'
        , default = ['20m:Magnetic Loop D=98cm', '40m:Magnetic Loop D=3.5m']
        )
    cmd.add_argument \
        ( "-c", "--call"
        , help    = "Location name to use for local DB"
        , default = 'OE3RSU Weidling'
        )
    cmd.add_argument \
        ( "-D", "--upload-date"
        , help    = "Date when this list of QSLs was uploaded to LOTW"
        )
    cmd.add_argument \
        ( "-d", "--cutoff-date"
        , help    = "Import no QSOs starting before that date,"
                    " use last QSO date by default"
        )
    cmd.add_argument \
        ( "-e", "--encoding"
        , help    = "Encoding of ADIF file, default=%(default)s"
        , default = 'utf-8'
        )
    cmd.add_argument \
        ( "-n", "--dry-run"
        , help    = "Dry run, do nothing"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "-p", "--password"
        , help    = "Password, better use .netrc"
        )
    cmd.add_argument \
        ( "-U", "--url"
        , help    = "URL of tracker (without rest path) default: %(default)s"
        , default = 'http://bee.priv.zoo:8080/qso/'
        )
    cmd.add_argument \
        ( "-u", "--username"
        , help    = "LOTW-Username"
        , default = 'oe3rsu'
        )
    cmd.add_argument \
        ( "--db-username"
        , help    = "Username of hamlog database"
        , default = 'ralf'
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , help    = "Verbose output"
        , action  = 'store_true'
        )
    args   = cmd.parse_args ()
    #lq     = LOTW_Query (args.username, args.password)
    #adif   = lq.get_qso ('2010-01-01', mydetail = 'yes')
    #with io.open ('zoppel3', 'w', encoding = 'utf-8') as f :
    #    f.write (adif)
    #with io.StringIO (adif) as f :
    #    lotw_adif = ADIF (f)
    # For now get downloaded file
    with io.open ('zoppel3', 'r', encoding = 'utf-8') as f :
        lotw_adif  = ADIF (f)

    # Get the given ADIF file
    with io.open (args.adif, 'r', encoding = args.encoding) as f :
        adif  = ADIF (f)

    # Open dbimporter
    au = ADIF_Uploader (args.url, args.db_username)

    lotw_adif.set_date_format (au.date_format)
    adif.set_date_format      (au.date_format)

    dryrun = ''
    if args.dry_run :
        dryrun = '[dry run] '

    # Match QSOs and check if LOTW-QSL exists
    for r in adif.records :
        ds = r.get_date ()
        if ds <= args.cutoff_date :
            continue
        calls = lotw_adif.by_call.get (r.call, [])
        for lc in calls :
            if lc.get_date () == r.get_date () :
                break
        else :
            print ("Call: %s not in lotw" % r.call)
            continue
        print ("Found %s in lotw" % r.call)
        # look it up in DB
        qsl = au.find_qsl (r.call, r.get_date (), type = 'LOTW')
        if not qsl :
            print ("Call: %s not found in DB" % r.call)
            # Search QSO
            qso = au.find_qso (r.call, r.get_date ())
            if not qso :
                print ("Call: %s QSO not found in DB!!!!!" % r.call)
                continue
            print ("Found QSO")
            if args.upload_date :
                d = dict \
                    ( qso       = qso ['id']
                    , date_sent = args.upload_date
                    , qsl_type  = 'LOTW'
                    )
                if not args.dry_run :
                    result = au.post ('qsl', json = d)
                print ("%sCall %s: Created QSL" % (dryrun, r.call))
            continue
        print ("Found %s in DB" % r.call)
        #print (qsl)
        if args.upload_date :
            if args.upload_date != qsl ['date_sent'] :
                print \
                    ( "Dates do not match: %s in DB vs %s requested"
                    % (qsl ['date_sent'], args.upload_date)
                    )
                q = au.get ('qsl/%s' % qsl ['id'])
                etag = q ['data']['@etag']
                if not args.dry_run :
                    r = au.put \
                        ( 'qsl/%s' % qsl ['id']
                        , json = dict (date_sent = args.upload_date)
                        , etag = etag
                        )
# end def main

if __name__ == '__main__' :
    main ()
