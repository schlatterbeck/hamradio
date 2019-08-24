#!/usr/bin/python
from __future__ import print_function

import sys
import os
import io
import requests
from argparse import ArgumentParser
from datetime import datetime
from netrc    import netrc
from getpass  import getpass
try :
    from urllib.parse import urlparse, quote_plus
except ImportError:
    from urlparse import urlparse
    from urllib   import quote as quote_plus
from adif     import ADIF

class ADIF_Uploader (object) :

    date_format = '%Y-%m-%d.%H:%M:%S'

    def __init__ (self, args) :
        self.args    = args
        self.session = requests.session ()
        self.user    = args.username
        self.url     = args.url
        self.baseurl = args.url
        # Basic Auth: user, password
        self.session.auth = (self.user, self.get_pw ())
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
        if args.dry_run :
            self.dryrun = '[dry run] '
        call = self.get \
            ('ham_call?name=%s&@fields=name,call,gridsquare' % args.call)
        collection = call ['data']['collection']
        if len (collection) == 0 :
            raise ValueError ('Invalid call: %s' % args.call)
        if len (collection) > 1 :
            raise ValueError \
                ( 'Too many calls matched for %s:\n%s'
                % ( args.call, '\n'.join (x ['name'] for x in collection))
                )
        self.call    = collection [0]
        self.id_call = self.call ['id']
        if args.cutoff_date :
            fmts = \
                ("%Y-%m-%d.%H:%M:%S", "%Y-%m-%dT%H:%M:%S"
                , "%Y-%m-%d.%H:%M",   "%Y-%m-%dT%H:%M"
                , "%Y-%m-%d"
                )
            for fmt in fmts :
                try :
                    dt = datetime.strptime (args.cutoff_date, fmt)
                    break
                except ValueError :
                    pass
            else :
                raise ValueError \
                    ("Unrecognized date format for %s" % args.cutoff_date)
            self.cutoff = dt.strftime (self.date_format)
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
    # end def __init__

    def date_cvt (self, d, t = '0000') :
	s  = '.'.join ((d, t))
        fmt = '%Y%m%d.%H%M'
        if len (s) > 13 :
            fmt = '%Y%m%d.%H%M%S'
	dt = datetime.strptime (s, fmt)
	return dt.strftime (self.date_format)
    # end def date_cvt

    def get (self, s) :
        r = self.session.get (self.url + s, headers = self.headers)
        if not (200 <= r.status_code <= 299) :
            raise RuntimeError \
                ( 'Invalid get result: %s: %s\n    %s'
                % (r.status_code, r.reason, r.text)
                )
        return r.json ()
    # end def get

    def get_pw (self) :
        """ Password given as option takes precedence.
            Next we try password via .netrc. If that doesn't work we ask.
        """
        if self.args.password :
            return self.args.password
        a = n = None
        try :
            n = netrc ()
        except IOError :
            pass
        if n and self.args.url :
            t = urlparse (self.args.url)
            a = n.authenticators (t.netloc)
        if a :
            un, d, pw = a
            if un != self.user :
                raise ValueError ("Netrc username doesn't match")
            return pw
        pw = getpass ('Password: ')
        return pw
    # end def get_pw

    def post_or_put (self, method, s, data = None, json = None, etag = None) :
        d = {}
        if data :
            d ['data'] = data
        if json :
            d ['json'] = json
        h = dict (self.headers)
        if etag :
            h ['If-Match'] = etag
        r = method (self.url + s, headers = h, **d)
        if not (200 <= r.status_code <= 299) :
            raise RuntimeError \
                ( 'Invalid put/post result: %s: %s\n    %s'
                % (r.status_code, r.reason, r.text)
                )
        return r.json ()
    # end def post_or_put

    def post (self, s, data = None, json = None, etag = None) :
        return self.post_or_put (self.session.post, s, data, json, etag)
    # end def post

    def put (self, s, data = None, json = None, etag = None) :
        return self.post_or_put (self.session.put, s, data, json, etag)
    # end def put

    def import_adif (self) :
        f = io.open (self.args.adif, 'r', encoding = self.args.encoding)
        adif  = ADIF (f)
        count = 0
        for record in adif.records :
            aprops = set (('qso_date', 'time_on', 'time_off'))
            ds = self.date_cvt (record ['qso_date'], record ['time_on'])
            if ds <= self.cutoff :
                continue
            if 'qso_date_off' in record :
                aprops.add ('qso_date_off')
                de = self.date_cvt \
                    (record ['qso_date_off'], record ['time_off'])
            else :
                de = self.date_cvt (record ['qso_date'], record ['time_off'])
                if de < ds :
                    notice ("time correction")
                    de = ds
            assert (de >= ds)
            pp = '%3b'.join ((de, de))
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
                if not self.args.dry_run :
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
            if 'my_gridsquare' in record :
                if  (  self.call ['gridsquare'].lower ()
                    != record ['my_gridsquare'].lower ()
                    ) :
                    raise ValueError \
                        ( "Invalid grid %s, expected %s"
                        % (record ['my_gridsquare'], self.call % ['gridsquare'])
                        )
                aprops.add ('my_gridsquare')
            if 'station_callsign' in record :
                if  (  self.call ['call'].lower ()
                    != record ['station_callsign'].lower ()
                    ) :
                    raise ValueError \
                        ( "Invalid call %s, expected %s"
                        % (record ['station_callsign'], self.call ['call'])
                        )
                aprops.add ('station_callsign')
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
            if not self.args.dry_run :
                qso = self.post ('qso', json = create_dict)
                qso = qso ['data']['id']
            count += 1
        self.notice ("Inserted %d records" % count)
    # end def import_adif

    def info (self, *args) :
        if self.args.verbose :
            print (self.dryrun, end = '')
            print (*args)
    # end def info

    def notice (self, *args) :
        print (self.dryrun, end = '')
        print (*args)
    # end def notice

# end class ADIF_Uploader

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "adif"
        , help    = "ADIF file to import"
        )
    cmd.add_argument \
        ( "-c", "--call"
        , help    = "Location name to use for local DB"
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
    au     = ADIF_Uploader (args)
    au.import_adif ()

# end def main

if __name__ == '__main__' :
    main ()