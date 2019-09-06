#!/usr/bin/python
from __future__ import print_function

import io
import sys
import requests
from argparse        import ArgumentParser
from datetime        import datetime
from netrc           import netrc
from getpass         import getpass
from rsclib.pycompat import text_type
from afu             import requester
from afu.adif        import ADIF
from afu.dbimport    import ADIF_Uploader
try :
    from urllib.parse import urlparse, urlencode
except ImportError:
    from urlparse import urlparse
    from urllib   import quote as urlencode

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
        d = {}
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
            qsl = self.uploader.find_qsl \
                (r.call, r.get_date (), type = 'LOTW', mode = r.get_mode ())
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
    # end def check_db_qsl_against_lotw

    def check_lotw_qso_against_qsl (self) :
        """ Loop over all LOTW QSOs sind lotw_cuttoff date and check
            they exist as SQL records (type LOTW) in local DB.
        """
        adif = self.lotwq.get_qso (since = self.lotw_cutoff, mydetail = 'yes')
        adif.set_date_format (self.uploader.date_format)
        for n, a in enumerate (adif) :
            qsl = self.uploader.find_qsl \
                (a.call, a.get_date (), type = 'LOTW', mode = a.get_mode ())
            if not qsl :
                print ("Call: %s: no LOTW QSL found in DB" % a.call)
                print (a)
            if self.verbose :
                print ("%s: found: %s         " % (n, a.call), end = '\r')
                sys.stdout.flush ()
    # end def check_lotw_qso_against_qsl

    def check_lotw_dupes (self) :
        adif = self.lotwq.get_qso (since = self.lotw_cutoff, mydetail = 'yes')
        adif.set_date_format (self.uploader.date_format)
        for k, key in enumerate (adif.by_call) :
            calls = adif.by_call [key]
            if len (calls) == 1 :
                c = calls [0]
                if self.verbose :
                    print ("%s: no dupe: %s       " % (k, c.call), end = '\r')
                    sys.stdout.flush ()
                continue
            for n, c1 in enumerate (calls) :
                for c2 in calls [n+1:] :
                    assert c1.call == c2.call
                    if c1.get_date () == c2.get_date () :
                        print ("Duplicate LOTW record:")
                        print ("First:\n",  c1)
                        print ("Second:\n", c2)
    # end def check_lotw_dupes

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

    def export_adif_from_list (self, listfile) :
        adif = ADIF ()
        adif.header = 'ADIF export RSC-QSO'
        with open (listfile) as f :
            for line in f :
                if line.startswith ('Call:') :
                    line = line.split (' ', 1)[1]
                date, call = line.split () [:2]
                qso = self.uploader.find_qso (call, date)
                adif.append (self.uploader.qso_as_adif (qso ['id']))
        return adif
    # end def export_adif_from_list

    def check_qsl (self) :
        """ Get all QSL from LOTW with given lotw_cutoff date.
            Check them all against DB:
            Find QSL, check qsl received time against local DB
            it's an error if QSL is not found (the qsl record should
            have been created when submitted to lotw).
        """
        dxcc = self.uploader.get ('dxcc_entity?@fields=code')
        dxcc = dxcc ['data']['collection']
        dxcc_by_id   = {}
        dxcc_by_code = {}
        for entry in dxcc :
            dxcc_by_id   [entry ['id']]   = entry ['code']
            dxcc_by_code [entry ['code']] = entry ['id']

        adif = self.lotwq.get_qsl (since = self.lotw_cutoff, mydetail = 'yes')
        adif.set_date_format (self.uploader.date_format)
        for a in adif :
            date = a.get_date ()
            qsl = self.uploader.find_qsl \
                (a.call, date, type = 'LOTW', mode = a.get_mode ())
            if not qsl :
                print ('Error: QSL not found: %s %s' % (date, a.call))
                continue
            if not qsl ['date_recv'] :
                print \
                    ( "%sQSL received, updating: %s %s date: %s"
                    % (self.dryrun, date, a.call, a.get_qsl_rdate ())
                    )
                q  = self.uploader.get ('qsl/%s' % qsl ['id'])
                q  = q ['data']
                if not self.dry_run :
                    d = dict (date_recv = a.get_qsl_rdate ())
                    self.uploader.put \
                        ('qsl/%s' % qsl ['id'], json = d, etag = q ['@etag'])
            elif qsl ['date_recv'][:10] != a.get_qsl_rdate ()[:10] :
                # We only compare the date, not the time
                # (time is always empty in LOTW)
                print \
                    ( "QSL receive time not matching: %s %s %s vs %s"
                    % (date, a.call, qsl ['date_sent'], a.get_qsl_rdate ())
                    )
            qso  = self.uploader.get ('qso/%s' % qsl ['qso']['id'])
            qso  = qso ['data']
            etag = qso ['@etag']
            q_id = qso ['id']
            qso  = qso ['attributes']

            fields = dict \
                ( iota = 'iota'
                , cqz  = 'cq_zone'
                , ituz = 'itu_zone'
                , dxcc = 'dxcc_entity'
                )
            d = {}
            for k in fields :
                if k in a :
                    f = qso [fields [k]]
                    v = val = a [k]
                    if isinstance (f, type ({})) :
                        f = dxcc_by_id [f ['id']]
                    if k == 'dxcc' :
                        v = "%03d" % int (a [k])
                        val = dxcc_by_code [v]
                    if k == 'cqz' or k == 'ituz' :
                        v = int (a [k], 10)
                    if not f :
                        d [fields [k]] = val
                    elif text_type (f) != text_type (v) :
                        if k == 'dxcc' :
                            # Update dxcc in any case
                            d [fields [k]] = val
                        print \
                            ("QSO %s %s Field %s differs: %s vs %s"
                            % (date, a.call, k, f, v)
                            )
            if d :
                if not self.dry_run :
                    self.uploader.put ('qso/%s' % q_id, json = d, etag = etag)
                print \
                    ("%sQSO %s %s updated: %s" % (self.dryrun, date, a.call, d))
    # end def check_qsl

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
        ( "--check-lotw-qso-against-qsl"
        , help    = "Loop over all LOTW QSOs and check if LOTW-QSL is in DB"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "--check-lotw-dupes"
        , help    = "Loop over all LOTW QSOs and check if there are"
                    " duplicate call/start-date/start-time entries"
        , action  = 'store_true'
        )
    cmd.add_argument \
        ( "--check-qsl"
        , help    = "Check QSLs in LOTW against local DB."
                    " Compare times and iota, cq-zone, itu-zone infos."
                    " Create if missing."
        , action  = 'store_true'
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
        ( "--export-adif-from-list"
        , help    = "Export list of <date, call> as adif"
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
    elif args.export_adif_from_list :
        adif = lu.export_adif_from_list (args.export_adif_from_list)
        print (adif)
    elif args.check_lotw_qso_against_qsl :
        lu.check_lotw_qso_against_qsl ()
    elif args.check_lotw_dupes :
        lu.check_lotw_dupes ()
    elif args.check_qsl :
        lu.check_qsl ()
    elif args.adif :
        lu.check_adif (qslsdate = args.upload_date)
    else :
        lu.check_db_qsl_against_lotw ()
# end def main

if __name__ == '__main__' :
    main ()
