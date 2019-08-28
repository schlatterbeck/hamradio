#!/usr/bin/python
from __future__ import print_function

import io
import sys
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
            We directly return an ADIF object.
        """
        d = {}
        for a in args :
            d ['qso_' + a] = args [a]
        d ['login']          = self.user
        d ['password']       = self.get_pw ()
        d ['qso_qsl']        = 'no'
        d ['qso_query']      = 1
        d ['qso_qsorxsince'] = since
        t = self.get ('?' + urlencode (d), as_text = True)
        with io.StringIO (t) as f :
            adif = ADIF (f)
        return adif
    # end def get_qso

    def get_qsl (self, since = '2010-01-01', **args) :
        """ Get QSLs for the given parameters.
            Parameters are automagically prefixed with 'qso_'
            according the the lotw API.
            Allowed values according to
            https://lotw.arrl.org/lotw-help/developer-query-qsos-qsls/
            are owncall, callsign, mode, band, startdate, starttime,
            enddate, endtime, mydetail, withown.
            Note that the 'since' parameter specifies the date QSO were
            uploaded to LOTW, not the startdate/starttime of the QSO.
            We directly return an ADIF object.
        """
        for a in args :
            d ['qso_' + a] = args [a]
        d ['login']          = self.user
        d ['password']       = self.get_pw ()
        d ['qso_qsl']        = 'yes'
        d ['qso_query']      = 1
        d ['qso_qslsince']   = since
        d ['qso_qsldetail']  = 'yes'
        t = self.get ('?' + urlencode (d), as_text = True)
        with io.StringIO (t) as f :
            adif = ADIF (f)
        return adif
    # end def get_qsl

# end class LOTW_Query

class LOTW_Downloader (object) :

    def __init__ \
        ( self
        , url
        , db_username
        , username
        , password
        , dry_run     = False
        , verbose     = False
        , adif        = None
        , cutoff      = None
        , lotw_cutoff = None
        , encoding    = 'utf-8'
        ) :
        self.url         = url
        self.db_username = db_username
        self.dry_run     = dry_run
        self.verbose     = verbose
        self.adiffile    = adif
        self.cutoff      = cutoff
        self.lotw_cutoff = lotw_cutoff
        self.encoding    = encoding

        # Open dbimporter
        self.uploader = ADIF_Uploader (self.url, self.db_username)
        self.lotwq    = LOTW_Query (username, password)

        self.adif = None
        # Get the given ADIF file
        if self.adiffile :
            with io.open (self.adiffile, 'r', encoding = self.encoding) as f :
                adif  = ADIF (f)
                adif.set_date_format (self.uploader.date_format)
                self.adif = adif

        self.dryrun = ''
        if self.dry_run :
            self.dryrun = '[dry run] '
    # end def __init__

    def check_adif (self, qslsdate = None) :
        """ Match QSOs and check if LOTW-QSL exists
            Update date if it is given and does not match
            Create QSL if it doesn't exist and a date is given
        """
        if not self.adif :
            print ("No ADIF file specified")
            return

        ladif = self.lotwq.get_qso (since = self.lotw_cutoff, mydetail = 'yes')
        #with io.open ('zoppel3', 'w', encoding = 'utf-8') as f :
        #    f.write (adif)
        # For now get downloaded file
        #with io.open ('zoppel3', 'r', encoding = 'utf-8') as f :
        #    ladif  = ADIF (f)
        ladif.set_date_format (self.uploader.date_format)

        for r in self.adif.records :
            ds = r.get_date ()
            if ds <= self.cutoff :
                continue
            calls = ladif.by_call.get (r.call, [])
            for lc in calls :
                if lc.get_date () == r.get_date () :
                    break
            else :
                print ("Call: %s not in lotw" % r.call)
                continue
            if self.verbose :
                print ("Found %s in lotw" % r.call)
            # look it up in DB
            qsl = self.uploader.find_qsl (r.call, r.get_date (), type = 'LOTW')
            if not qsl :
                if self.verbose :
                    print ("Call: %s not found in DB" % r.call)
                # Search QSO
                qso = self.uploader.find_qso (r.call, r.get_date ())
                if not qso :
                    print ("Call: %s QSO not found in DB!!!!!" % r.call)
                    continue
                if self.verbose :
                    print ("Found QSO")
                if qslsdate :
                    d = dict \
                        ( qso       = qso ['id']
                        , date_sent = qslsdate
                        , qsl_type  = 'LOTW'
                        )
                    if not self.dry_run :
                        result = self.uploader.post ('qsl', json = d)
                    print ("%sCall %s: Created QSL" % (self.dryrun, r.call))
                continue
            if self.verbose :
                print ("Found %s in DB" % r.call)
            if qslsdate :
                if qslsdate != qsl ['date_sent'] :
                    print \
                        ( "Dates do not match: %s in DB vs %s requested"
                        % (qsl ['date_sent'], qslsdate)
                        )
                    q = self.uploader.get ('qsl/%s' % qsl ['id'])
                    etag = q ['data']['@etag']
                    if not self.dry_run :
                        r = self.uploader.put \
                            ( 'qsl/%s' % qsl ['id']
                            , json = dict (date_sent = qslsdate)
                            , etag = etag
                            )
    # end def check_adif

    def check_db_qsl_against_lotw (self) :
        """ Get all DB records since the db cutoff (qsl-sent-date).
            Retrieve all QSOs from LOTW since that cutoff date (the
            lotw_cutoff is ignored) and check if all local QSLs exist as
            QSO in LOTW.
        """
        # look it up in DB
        cut = self.uploader.format_date (self.cutoff)
        qsl = self.uploader.get \
            ('qsl?date_sent=%s&qsl_type=LOTW&@fields=qso' % cut)
        qsl = qsl ['data']['collection']
        adif = self.lotwq.get_qso (since = self.cutoff, mydetail = 'yes')
        adif.set_date_format (self.uploader.date_format)
        for n, q in enumerate (qsl) :
            qso = self.uploader.get ('qso/%s' % q ['qso']['id'])
            q ['QSO'] = qso ['data']['attributes']
            # Look it up by call in lotw
            call = q ['QSO']['call']
            date = q ['QSO']['qso_start']
            for a in adif.by_call.get (call, []) :
                assert a.call == call
                if a.get_date () == date :
                    if self.verbose :
                        print ("%s: found: %s         " % (n, call), end = '\r')
                        sys.stdout.flush ()
                    break
            else :
                print ("Call: %s %s not in lotw" % (date, call))

    def find_qso_without_qsl (self) :
        """ Loop over all QSOs and find those that do not have a
            corresponding LOTW QSL. Use the cutoff date for selecting
            the qso_start.
        """
        cut = self.uploader.format_date (self.cutoff)
        qso = self.uploader.get \
            ('qso?qso_start=%s&@fields=call,qso_start,swl' % cut)
        qso = qso ['data']['collection']
        for n, q in enumerate (qso) :
            call = q ['call']
            qsl = self.uploader.get ('qsl?qso=%s&qsl_type=LOTW' % q ['id'])
            qsl = qsl ['data']['collection']
            assert len (qsl) <= 1
            if not qsl :
                if q ['swl'] :
                    print ("%s: %s: SWL       " % (n, call))
                else :
                    print \
                        ( "Call: %s %s has no LOTW qsl"
                        % (q ['qso_start'], call)
                        )
            elif self.verbose :
                print ("%s: found: %s         " % (n, call), end = '\r')
                sys.stdout.flush ()
    # end def find_qso_without_qsl

    def check_qsl (self) :
        """ Get all QSL starting with as qsl-s-date of the given DB
            cutoff date. Get the QSOs for these QSLs, too. Check them
            one-by-one against the QSLs from LOTW.
        """
        #lotw_qsl = self.
        #adif = self.lotwq.get_qsl (since = self.lotw_cutoff, mydetail = 'yes')
        pass

# end class LOTW_Downloader

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "adif"
        , help    = "ADIF file to import"
        , nargs   = '?'
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
        , help    = "Check no QSLs starting before that date in ADIF"
                    " default = %(default)s"
        , default = "2010-01-01"
        )
    cmd.add_argument \
        ( "-e", "--encoding"
        , help    = "Encoding of ADIF file, default=%(default)s"
        , default = 'utf-8'
        )
    cmd.add_argument \
        ( "--find-qso-without-qsl"
        , help    = "Find all QSOs in local DB that don't have an LOTW qsl"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "-l", "--lotw-cutoff-date"
        , help    = "Check no QSLs from LOTS starting before that date,"
                    " default = %(default)s"
        , default = '2010-01-01'
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
    args = cmd.parse_args ()
    lu   = LOTW_Downloader \
        ( args.url
        , args.db_username
        , args.username
        , args.password
        , dry_run     = args.dry_run
        , adif        = args.adif
        , cutoff      = args.cutoff_date
        , lotw_cutoff = args.lotw_cutoff_date
        , verbose     = args.verbose
        , encoding    = args.encoding
        )
    if args.find_qso_without_qsl :
        lu.find_qso_without_qsl ()
    elif args.adif :
        lu.check_adif (qslsdate = args.upload_date)
    else :
        lu.check_db_qsl_against_lotw ()
# end def main

if __name__ == '__main__' :
    main ()
