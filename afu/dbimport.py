#!/usr/bin/python
from __future__ import print_function

import io
import requests
from argparse import ArgumentParser
from datetime import datetime
from netrc    import netrc
from getpass  import getpass
from afu      import requester
from afu.adif import ADIF, Native_ADIF_Record
try :
    from urllib.parse import urlparse, quote_plus
except ImportError:
    from urlparse import urlparse
    from urllib   import quote as quote_plus

def parse_cutoff (cutoff) :
    fmts = \
        ("%Y-%m-%d.%H:%M:%S", "%Y-%m-%dT%H:%M:%S"
        , "%Y-%m-%d.%H:%M",   "%Y-%m-%dT%H:%M"
        , "%Y-%m-%d"
        )
    for fmt in fmts :
        try :
            dt = datetime.strptime (cutoff, fmt)
            break
        except ValueError :
            pass
    else :
        raise ValueError \
            ("Unrecognized date format for %s" % cutoff)
    return dt
#end parse_cutoff

class ADIF_Uploader (requester.Requester) :

    date_format = '%Y-%m-%d.%H:%M:%S'

    def __init__ \
        ( self
        , url
        , username
        , password = None
        , dry_run  = False
        , verbose  = False
        , antenna  = []
        ) :
        self.__super.__init__ (url, username, password)
        self.dry_run = dry_run
        self.verbose = verbose
        self.set_basic_auth ()
        if self.url.endswith ('/') :
            orig = self.url.rstrip ('/')
        else :
            orig = self.url
            self.url += '/'
        self.headers = dict \
            ( Origin  = orig
            , Referer = self.url
            )
        self.headers ['X-Requested-With'] = 'requests library'
        self.url += 'rest/data/'
        self.dryrun = ''
        if dry_run :
            self.dryrun = '[dry run] '
        self.antenna = {}
        for a in antenna :
            k, v = a.split (':', 1)
            self.antenna [k] = v
        for band in self.antenna :
            a = self.antenna [band]
            v = self.get ('antenna?name=%s' % quote_plus (a))
            collection = v ['data']['collection']
            if len (collection) == 0 :
                raise ValueError ('Invalid antenna: %s' % a)
            if len (collection) > 1 :
                raise ValueError ('No exact match for antenna: %s' % a)
            antenna = collection [0]['id']
            v = self.get ('ham_band?name=%s' % quote_plus (band))
            collection = v ['data']['collection']
            if len (collection) == 0 :
                raise ValueError ('Invalid band: %s' % band)
            if len (collection) > 1 :
                raise ValueError ('No exact match for band: %s' % band)
            self.antenna [band] = antenna
    # end def __init__

    def qso_as_adif (self, id) :
        """ Retrieve QSO with id and output it as ADIF.
        """
        qso   = self.get ('qso/%s?@verbose=3' % id) ['data']['attributes']
        start = datetime.strptime (qso ['qso_start'], self.date_format)
        end   = datetime.strptime (qso ['qso_end'], self.date_format)
        owner = self.get ('ham_call/%s' % qso ['owner']['id'])
        owner = owner ['data']['attributes']

        rec   = Native_ADIF_Record \
            ( call             = qso ['call']
            , mode             = qso ['mode']['name']
            , qso_date         = start.strftime ('%Y%m%d')
            , time_on          = start.strftime ('%H%M%S')
            , qso_date_off     = end.strftime ('%Y%m%d')
            , time_off         = end.strftime ('%H%M%S')
            , gridsquare       = qso ['gridsquare']
            , rst_sent         = qso ['rst_sent']
            , rst_rcvd         = qso ['rst_rcvd']
            , band             = qso ['band']['name']
            , freq             = qso ['freq']
            , station_callsign = owner['call']
            , my_gridsquare    = owner['gridsquare']
            , tx_pwr           = qso ['tx_pwr']
            )
        return rec
    # end def qso_as_adif

    def find_qsl (self, call, qsodate, type = None, mode = None) :
        d = self.format_date (qsodate, qsodate)
        s = 'qsl?@fields=date_sent,date_recv,qso&qso.call:=%s&qso.qso_start=%s'
        s = s % (call, d)
        if type :
            s += '&qsl_type=%s' % type
        if mode :
            # Search for both, PSKxxx and QPSKxxx
            if mode.startswith ('PSK') :
                mode = mode + ',Q%s' % mode
            s += '&qso.mode=%s' % mode
        r = self.get (s) ['data']['collection']
        if type and mode :
            assert len (r) <= 1
            if len (r) == 1 :
                return r [0]
        else :
            return r
    # end def find_qsl

    def find_qso (self, call, qsodate) :
        d = self.format_date (qsodate, qsodate)
        s = 'qso?@fields=call&call:=%s&qso_start=%s'
        s = s % (call, d)
        r = self.get (s) ['data']['collection']
        assert len (r) <= 1
        if len (r) == 1 :
            return r [0]
    # end def find_qso

    @staticmethod
    def format_date (date1, date2 = None) :
        if date2 is None :
            date2 = ''
        if not date1 :
            date1 = ''
        return quote_plus (';').join ((date1, date2))
    # end def format_date

    def import_adif (self, adif, encoding) :
        f = io.open (adif, 'r', encoding = encoding)
        adif  = ADIF (f)
        count = 0
        for record in adif.records :
            aprops = set (('qso_date', 'time_on', 'time_off'))
            ds = ADIF.date_cvt \
                ( record ['qso_date']
                , record ['time_on']
                , date_format = self.date_format
                )
            if ds <= self.cutoff :
                continue
            if 'qso_date_off' in record :
                aprops.add ('qso_date_off')
                de = ADIF.date_cvt \
                    ( record ['qso_date_off']
                    , record ['time_off']
                    , date_format = self.date_format
                    )
            else :
                de = ADIF.date_cvt \
                    ( record ['qso_date']
                    , record ['time_off']
                    , date_format = self.date_format
                    )
                if de < ds :
                    notice ("time correction")
                    de = ds
            assert (de >= ds)
            pp = self.format_date (de, de)
            dr = self.get ('qso?qso_end=%s&owner=%s' % (pp, self.id_call))
            if dr ['data']['collection'] :
                dupe = False
                for d in dr ['data']['collection'] :
                    q = self.get ('qso/%s' % d ['id'])
                    q = q ['data']['attributes']
                    if (q ['call'] != record ['call']) :
                        self.notice \
                            ( "Same end-time but different calls: %s %s %s"
                            % (de, q ['call'], record ['call'])
                            )
                    else :
                        self.notice ("Existing record:", de)
                        dupe = True
                if dupe :
                    continue
            create_dict = dict \
                (qso_start = ds, qso_end = de, owner = self.id_call)
            if 'band' in record :
                create_dict ['band'] = record ['band']
                if record ['band'] in self.antenna :
                    create_dict ['antenna'] = self.antenna [record ['band']]
                aprops.add ('band')
            if 'mode' in record :
                create_dict ['mode'] = record ['mode']
                aprops.add ('mode')
            if 'notes' in record or 'comment' in record :
                n = []
                if 'notes' in record :
                    n.append (record ['notes'])
                    aprops.add ('notes')
                if 'comment' in record :
                    n.append (record ['comment'])
                    aprops.add ('comment')
                if not self.dry_run :
                    j = self.post ('msg', data = dict (content = '\n'.join (n)))
                    m = j ['data']['id']
                else :
                    m = '99999'
                create_dict ['messages'] = [m]
            if 'qslrdate' in record :
                qslrdate = record ['qslrdate']
                aprops.add ('qslrdate')
            if 'qslsdate' in record :
                qslsdate = record ['qslsdate']
                aprops.add ('qslsdate')
            if 'station_callsign' in record :
                if  (  self.call ['call'].lower ()
                    != record ['station_callsign'].lower ()
                    ) :
                    raise ValueError \
                        ( "Invalid call %s, expected %s"
                        % (record ['station_callsign'], self.call ['call'])
                        )
                aprops.add ('station_callsign')
            if 'my_gridsquare' in record :
                if  (  self.call ['gridsquare'].lower ()
                    != record ['my_gridsquare'].lower ()
                    ) :
                    raise ValueError \
                        ( "Invalid grid %s, expected %s"
                        % (record ['my_gridsquare'], self.call ['gridsquare'])
                        )
                aprops.add ('my_gridsquare')
            # Ignore srx field (contest serial number)
            if 'srx' in record :
                aprops.add ('srx')
            if 'srx_string' in record :
                aprops.add ('srx_string')
            # Ignore stx field (contest serial number)
            if 'stx' in record :
                aprops.add ('stx')
            if 'stx_string' in record :
                aprops.add ('stx_string')
            # Get qso1 for schema
            schema_qso = self.get ('qso/1')
            schema_qso = list \
                (k for k in schema_qso ['data']['attributes'] if k != 'id')
            for p in schema_qso :
                ap = p.lower ()
                if ap not in aprops and ap in record :
                    aprops.add (ap)
                    # Insert strings only if non-empty
                    if record [ap] :
                        create_dict [p] = record [ap]
                    else :
                        assert ap not in ('call', 'mode')
            missing_fields = set (record.dict.iterkeys ()) - aprops
            if missing_fields :
                raise RuntimeError ("Missing fields: %s" % str (missing_fields))
            self.info ("Create QSO: %s" % create_dict)
            if not self.dry_run :
                qso = self.post ('qso', json = create_dict)
                qso = qso ['data']['id']
            count += 1
        self.notice ("Inserted %d records" % count)
    # end def import_adif

    def info (self, *args) :
        if self.verbose :
            print (self.dryrun, end = '')
            print (*args)
    # end def info

    def notice (self, *args) :
        print (self.dryrun, end = '')
        print (*args)
    # end def notice

    def set_call (self, call) :
        call = self.get \
            ('ham_call?name=%s&@fields=name,call,gridsquare' % call)
        collection = call ['data']['collection']
        if len (collection) == 0 :
            raise ValueError ('Invalid call: %s' % call)
        if len (collection) > 1 :
            raise ValueError \
                ( 'Too many calls matched for %s:\n%s'
                % ( call, '\n'.join (x ['name'] for x in collection))
                )
        self.call    = collection [0]
        self.id_call = self.call ['id']
    # end def set_call

    def set_cutoff_date (self, cutoff_date = None) :
        if cutoff_date :
            self.cutoff = parse_cutoff (cutoff_date).strftime (self.date_format)
        else :
            # Get QSO with latest start date unfortunately we have to
            # retrieve *all* qsos and sort ourselves.
            # Should be fixed once we can.
            qso = self.get ('qso?@fields=qso_start')
            d = ''
            for q in qso ['data']['collection'] :
                if q ['qso_start'] > d :
                    d = q ['qso_start']
            self.cutoff = d
    # end def set_cutoff_date

# end class ADIF_Uploader

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
        , help    = "Location name to use for local DB, default=%(default)s"
        , default = 'OE3RSU Weidling'
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
        , help    = "Username of hamlog database"
        , default = 'ralf'
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , help    = "Verbose output"
        , action  = 'store_true'
        )
    args   = cmd.parse_args ()
    au     = ADIF_Uploader \
        ( args.url
        , args.username
        , args.password
        , args.dry_run
        , args.verbose
        , args.antenna
        )
    au.set_call        (args.call)
    au.set_cutoff_date (args.cutoff_date)
    au.import_adif (args.adif, args.encoding)

# end def main

if __name__ == '__main__' :
    main ()
