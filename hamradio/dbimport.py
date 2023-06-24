#!/usr/bin/python
# Copyright (C) 2019-22 Dr. Ralf Schlatterbeck Open Source Consulting.
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
import os
import sys
import requests
from argparse import ArgumentParser
from datetime import datetime, timedelta
from netrc    import netrc
from getpass  import getpass
from hamradio      import requester
from hamradio.adif import ADIF, Native_ADIF_Record
from hamradio.lotw import LOTW_Query
from hamradio.eqsl import EQSL_Query
try :
    from urllib.parse import urlparse, quote_plus, urlencode
except ImportError:
    from urlparse import urlparse
    from urllib   import quote as quote_plus
    from urllib   import urlencode
from rsclib.autosuper import autosuper
from rsclib.pycompat  import text_type

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

class Log_Mixin (autosuper) :

    def __init__ (self, dry_run = False, verbose = False, **kw) :
        self.verbose = verbose
        self.dryrun = ''
        if dry_run :
            self.dryrun = '[dry run] '
        self.__super.__init__ (**kw)
    # end def __init__

    def info (self, *args) :
        if self.verbose :
            print (self.dryrun, end = '')
            print (*args)
    # end def info

    def animate_info (self, *args) :
        if self.verbose :
            print (*args, end = '\r')
            sys.stdout.flush ()
    # end def animate_info

    def notice (self, *args) :
        print (self.dryrun, end = '')
        print (*args)
    # end def notice

# end class Log_Mixin

class ADIF_Uploader (requester.Requester, Log_Mixin) :

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
        self.__super.__init__ \
            (url, username, password, dry_run = dry_run, verbose = verbose)
        self.dry_run = dry_run
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
        # Get mode with name, adif_mode, adif_submode
        mode  = self.get \
            ( 'ham_mode/%s?@fields=name,adif_mode,adif_submode'
            % qso ['mode']['id']
            )
        mode = mode ['data']['attributes']

        d = dict \
            ( call             = qso ['call']
            , mode             = mode ['adif_mode']
            , qso_date         = start.strftime ('%Y%m%d')
            , time_on          = start.strftime ('%H%M%S')
            , qso_date_off     = end.strftime ('%Y%m%d')
            , time_off         = end.strftime ('%H%M%S')
            , gridsquare       = qso ['gridsquare']
            , rst_sent         = qso ['rst_sent']
            , rst_rcvd         = qso ['rst_rcvd']
            , band             = qso ['band']['name']
            , freq             = qso ['freq']
            , station_callsign = owner ['call']
            , my_gridsquare    = owner ['gridsquare']
            , tx_pwr           = qso ['tx_pwr']
            )
        if mode ['adif_submode'] :
            d ['submode'] = mode ['adif_submode']
        if owner ['eqsl_nickname'] :
            d ['app_eqsl_qth_nickname'] = owner ['eqsl_nickname']
        rec = Native_ADIF_Record (**d)
        return rec
    # end def qso_as_adif

    def _mangle_mode (self, mode, submode) :
        """ Backwards compatibility for old ADIF files that contain
            something that is now a submode in the mode field and have
            an empty submode.
        """
        if not submode :
            if mode.startswith ('PSK') and len (mode) != 3 :
                return 'PSK', mode
            if mode.startswith ('QPSK') :
                if len (mode) == 4 :
                    return 'PSK', ''
                return 'PSK', mode
            if mode.startswith ('MFSK') and len (mode) != 4 :
                return 'MFSK', mode
            return mode, submode
        return mode, submode
    # end def _mangle_mode

    def find_qsl \
        ( self, call, qsodate
        , type    = None
        , mode    = None
        , submode = None
        , fuzzy   = False
        ) :
        """ Find a QSL via parameters, these typically come from and
            ADIF file and follow ADIF conventions.
            The fuzzy match is mainly used for eQSL: This doesn't return
            the exact start time of *my* QSO but seems to return the
            start of the peer which usually differs. In case fuzzy was
            requested we relax matching of the start time to
            +/- 5 Minutes.
        """
        fields = \
            [ 'date_sent', 'date_recv', 'qso'
            , 'files', 'qso_time', 'gridsquare', 'rst_rcvd'
            ]
        d = { '@fields'       : ','.join (fields)
            , 'qso.call:'     : call
            , 'qso.qso_start' : self.mangle_date (qsodate, fuzzy)
            }
        mode, submode = self._mangle_mode (mode, submode)
        if type :
            d ['qsl_type'] = type
        if mode :
            d ['qso.mode.adif_mode']    = mode
        if submode :
            d ['qso.mode.adif_submode'] = submode
        r = self.get ('qsl?' + urlencode (d)) ['data']['collection']
        if type and mode :
            if len (r) == 1 :
                return r [0]
            # retry with qsl.qso_time instead of qso.qso_start
            # if the fuzzy match didn't return anything (fuzzy means
            # we're using eQSL). So if we already manually inserted the
            # eQSL start time it will match.
            if fuzzy :
                del d ['qso.qso_start']
                d ['qso_time'] = self.mangle_date (qsodate, False)
                r = self.get ('qsl?' + urlencode (d)) ['data']['collection']
            if len (r) > 1 :
                raise ValueError \
                    ( "Duplicate QSL: %s %s Mode: %s/%s"
                    % (call, qsodate, mode, submode or '')
                    )
            if len (r) == 1 :
                return r [0]
        else :
            return r
    # end def find_qsl

    def find_qso (self, call, qsodate, mode=None, submode=None) :
        d = { '@fields'   : 'call'
            , 'call:'     : call
            , 'qso_start' : self.mangle_date (qsodate)
            }
        mode, submode = self._mangle_mode (mode, submode)
        if mode :
            d ['mode.adif_mode']    = mode
        if submode :
            d ['mode.adif_submode'] = submode
        r = self.get ('qso?' + urlencode (d)) ['data']['collection']
        assert len (r) <= 1
        if len (r) == 1 :
            return r [0]
    # end def find_qso

    def mangle_date (self, date, fuzzy = False) :
        """ Compute a date range.
            Typically dates should include the second. But if the date
            string is shorter and includes no seconds, we add seconds
            for the end-date of the range (59 should be fine).
            If fuzzy is True we match date +/- 5 Minutes.
        >>> au = ADIF_Uploader ('http://example.com', '', dry_run = 1)
        >>> au.mangle_date ('2019-09-02.18:57')
        '2019-09-02.18:57;2019-09-02.18:57:59'
        >>> au.mangle_date ('2019-09-02.18:57', fuzzy = True)
        '2019-09-02.18:52:00;2019-09-02.19:02:00'
        """
        if fuzzy :
            if len (date) == 16 :
                date = date + ':00'
            fmt = self.date_format
            dt = datetime.strptime (date, fmt)
            td = timedelta (minutes = 5)
            d1 = dt - td
            d2 = dt + td
            return self.format_date (d1.strftime (fmt), d2.strftime (fmt))
        else :
            if len (date) == 16 :
                return self.format_date (date, date + ':59')
            return self.format_date (date, date)
    # end def mangle_date

    @staticmethod
    def format_date (date1, date2 = None) :
        if date2 is None :
            date2 = ''
        if not date1 :
            date1 = ''
        return ';'.join ((date1, date2))
    # end def format_date

    def import_adif (self, adif) :
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
            d = { 'qso_end' : pp
                , 'owner'   : self.id_call
                }
            dr = self.get ('qso?' + urlencode (d))
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
            missing_fields = set (record.dict.keys ()) - aprops
            if missing_fields :
                raise RuntimeError ("Missing fields: %s" % str (missing_fields))
            self.info ("Create QSO: %s" % create_dict)
            if not self.dry_run :
                qso = self.post ('qso', json = create_dict)
                qso = qso ['data']['id']
            count += 1
        self.notice ("Inserted %d records" % count)
    # end def import_adif

    def set_call (self, call) :
        d = { 'name:'   : call
            , '@fields' : 'name,call,gridsquare,eqsl_nickname'
            }
        call = self.get ('ham_call?' + urlencode (d))
        collection = call ['data']['collection']
        if len (collection) == 0 :
            raise ValueError ('Invalid call: %s' % call)
        assert len (collection) == 1
        self.call    = collection [0]
        self.id_call = self.call ['id']
    # end def set_call

    def set_cutoff_date (self, cutoff_date = None) :
        """ cutoff_date is a datetime instance
        """
        if cutoff_date :
            self.cutoff = cutoff_date.strftime (self.date_format)
        else :
            # Get QSO with latest start date
            d = { 'owner'      : self.id_call
                , '@fields'    : 'qso_start'
                , '@sort'      : '-qso_start'
                , '@page_size' : 1
                }
            qso = self.get ('qso?' + urlencode (d))
            qso = qso ['data']['collection']
            if len (qso) == 0 :
                raise ValueError ("No QSO found to determine cutoff")
            assert len (qso) == 1
            d = qso [0]['qso_start']
            self.cutoff = d
    # end def set_cutoff_date

# end class ADIF_Uploader

class DB_Importer (Log_Mixin) :

    # Minutes only for qso start comparison, some logging services
    # ignore minutes
    minute_date_format = '%Y-%m-%d.%H:%M'

    def __init__ (self, args) :
        self.__super.__init__ (args.dry_run, args.verbose)
        self.args = args
        self.au = ADIF_Uploader \
            ( args.url
            , args.username
            , args.password
            , args.dry_run
            , args.verbose
            , args.antenna
            )
        self.au.set_call (args.call)
        cutoff = None
        if args.cutoff_date :
            cutoff = parse_cutoff (args.cutoff_date)
        self.cutoff = cutoff
        self.adif = None
        if args.adiffile :
            with io.open (args.adiffile, 'r', encoding = args.encoding) as f :
                adif = ADIF (f)
                adif.set_date_format (self.au.date_format)
                self.adif = adif
        self.logbook = None
        if args.qsl_type :
            if args.qsl_type == 'LOTW' :
                self.logbook = LOTW_Query \
                    (args.lotw_username, args.lotw_password)
            elif args.qsl_type == 'eQSL' :
                self.logbook = EQSL_Query \
                    ( self.au.call ['eqsl_nickname']
                    , self.au.call ['call'] # need to use call as username!
                    , args.eqsl_password
                    )
            else :
                assert 0
    # end def __init__

    def execute (self) :
        method = getattr (self, 'do_' + self.args.command)
        method ()
    # end def execute

    # Command methods start with 'do'

    def do_import (self) :
        self.au.set_cutoff_date (self.cutoff)
        self.au.import_adif (self.adif)
    # end def do_import

    def do_import_qsl (self) :
        """ Match QSOs and check that QSL exists for specified qsl_type
            Update date if it is given and does not match
            Create QSL if it doesn't exist, a date must be given
        """
        qtype    = self.args.qsl_type
        qslsdate = self.args.upload_date
        cutoff   = None
        if self.cutoff :
            cutoff = self.cutoff.strftime ('%Y-%m-%d.%H:%M:%S')
        if not qslsdate :
            raise ValueError ("Need QSL Sent date")
        if not self.adif :
            raise ValueError ("No ADIF file specified")
        self.adif.set_date_format (self.minute_date_format)
        ladif = self.logbook.get_qso (since = self.cutoff, mydetail = 'yes')
        ladif.set_date_format (self.minute_date_format)
        for r in self.adif.records :
            ds = r.get_date ()
            if cutoff and ds <= cutoff :
                continue
            calls = ladif.by_call.get (r.call, [])
            for lc in calls :
                if lc.get_date () == r.get_date () :
                    break
            else :
                self.notice ("Call: %s not in %s" % (r.call, qtype))
                continue
            self.info ("Found %s in %s" % (r.call, qtype))
            # look it up in DB
            submode = r.dict.get ('submode', None)
            qsl = self.au.find_qsl \
                ( r.call
                , r.get_date ()
                , type    = qtype
                , mode    = r.get_mode ()
                , submode = submode
                )
            if not qsl :
                self.info ("Call: %s not found in DB" % r.call)
                # Search QSO
                qso = self.au.find_qso \
                    ( r.call
                    , r.get_date ()
                    , mode    = r.get_mode ()
                    , submode = submode
                    )
                if not qso :
                    self.notice ("Call: %s QSO not found in DB!!!!!" % r.call)
                    continue
                self.info ("Found QSO")
                if qslsdate :
                    d = dict \
                        ( qso       = qso ['id']
                        , date_sent = qslsdate
                        , qsl_type  = qtype
                        )
                    if not self.args.dry_run :
                        result = self.au.post ('qsl', json = d)
                    self.notice ("Call %s: Created QSL" % (r.call))
                continue
            self.info ("Found %s in DB" % r.call)
            if qslsdate :
                if qslsdate != qsl ['date_sent'] :
                    self.notice \
                        ( "Dates do not match: %s in DB vs %s requested"
                        % (qsl ['date_sent'], qslsdate)
                        )
                    q = self.au.get ('qsl/%s' % qsl ['id'])
                    etag = q ['data']['@etag']
                    if not self.args.dry_run :
                        r = self.au.put \
                            ( 'qsl/%s' % qsl ['id']
                            , json = dict (date_sent = qslsdate)
                            , etag = etag
                            )
    # end def do_import_qsl

    def do_check_db_qsl_against_log_app (self) :
        """ Get all DB records since the db cutoff (qsl-sent-date).
            Retrieve all QSOs from logbook app since that cutoff date
            and check if all local QSLs exist as QSO in logbook.
            FIXME: At some point we want to export this as ADIF.
        """
        qtype = self.args.qsl_type
        # look it up in DB
        d = { 'date_sent' : self.au.format_date (self.cutoff)
            , 'qso.owner' : self.au.id_call
            , 'qsl_type'  : qtype
            , '@fields'   : 'qso'
            }
        qsl = self.au.get ('qsl?' + urlencode (d))['data']['collection']
        adif = self.logbook.get_qso (since = self.cutoff, mydetail = 'yes')
        adif.set_date_format (self.au.date_format)
        for n, q in enumerate (qsl) :
            qso = self.au.get ('qso/%s' % q ['qso']['id'])
            q ['QSO'] = qso ['data']['attributes']
            # Look it up by call in logbook
            call = q ['QSO']['call']
            date = q ['QSO']['qso_start']
            for a in adif.by_call.get (call, []) :
                assert a.call == call
                if a.get_date ()[:16] == date [:16] :
                    self.animate_info ("%s: found: %s   " % (n, call))
                    break
            else :
                if q ['QSO']['swl'] :
                    self.notice ("%s: %s: SWL       " % (n, call))
                else :
                    self.notice ("Call: %s %s not in %s" % (date, call, qtype))
    # end def do_check_db_qsl_against_log_app

    def do_check_log_app_against_qsl (self) :
        """ Loop over all logbook app QSOs since cutoff date and check
            they exist as SQL records (correct qsl type) in local DB.
        """
        qtype = self.args.qsl_type
        adif = self.logbook.get_qso (since = self.cutoff, mydetail = 'yes')
        adif.set_date_format (self.au.date_format)
        for n, a in enumerate (adif) :
            submode = a.dict.get ('submode', None)
            qsl = self.au.find_qsl \
                ( a.call
                , a.get_date () [:16]
                , type    = qtype
                , mode    = a.get_mode ()
                , submode = submode
                )
            if not qsl :
                self.notice \
                    ( "Call: %s %s: no %s QSL found in DB"
                    % (a.call, a.get_date (), qtype)
                    )
            else :
                self.animate_info ("%s: found: %s         " % (n, a.call))
    # end def do_check_log_app_against_qsl

    def do_check_log_app_dupes (self) :
        qtype = self.args.qsl_type
        adif = self.logbook.get_qso (since = self.cutoff, mydetail = 'yes')
        adif.set_date_format (self.au.date_format)
        for k, key in enumerate (adif.by_call) :
            calls = adif.by_call [key]
            if len (calls) == 1 :
                c = calls [0]
                self.animate_info ("%s: no dupe: %s       " % (k, c.call))
                continue
            for n, c1 in enumerate (calls) :
                for c2 in calls [n+1:] :
                    assert c1.call == c2.call
                    if c1.get_date () == c2.get_date () :
                        self.notice ("Duplicate %s record:" % qtype)
                        self.notice ("First:\n",  c1)
                        self.notice ("Second:\n", c2)
    # end def do_check_log_app_dupes

    def do_check_qsl (self) :
        """ Get all QSL from log app with given cutoff date.
            Check them all against DB:
            Find QSL, check qsl received time against local DB
            it's an error if QSL is not found (the qsl record should
            have been created when submitted to the log app).
        """
        qtype = self.args.qsl_type
        now   = datetime.now ().strftime (self.au.date_format)
        dxcc = self.au.get ('dxcc_entity?@fields=code')
        dxcc = dxcc ['data']['collection']
        dxcc_by_id   = {}
        dxcc_by_code = {}
        for entry in dxcc :
            dxcc_by_id   [entry ['id']]   = entry ['code']
            dxcc_by_code [entry ['code']] = entry ['id']
        archived = 0
        # No error check if something wrong comes along stay at default
        if self.args.archived != 'no' :
            if self.args.archived == 'yes' :
                archived = 1
            elif self.args.archived == 'all' :
                archived = None
        adif = self.logbook.get_qsl \
            (since = self.cutoff, mydetail = 'yes', archived = archived)
        adif.set_date_format (self.au.date_format)
        for a in adif :
            date = a.get_date ()
            submode = a.dict.get ('submode', None)
            # eQSL returns the start time of the peer for QSLs
            # So no exact match, we need to specify fuzzy.
            qsl = self.au.find_qsl \
                ( a.call
                , date [:16]
                , type    = qtype
                , mode    = a.get_mode ()
                , submode = submode
                , fuzzy   = (qtype == 'eQSL')
                )
            if not qsl :
                self.notice \
                    ( 'Error: QSL not found: %s %s mode: %s/%s'
                    % (date, a.call, a.get_mode (), submode or '')
                    )
                continue
            cmpd  = True
            rdate = a.get_qsl_rdate ()
            if rdate is None :
                rdate = now
                cmpd  = False
            set_recv_date = False
            if not qsl ['date_recv'] :
                set_recv_date = True
                self.notice \
                    ( "QSL received, updating: %s %s date: %s"
                    % (date, a.call, rdate)
                    )
                q  = self.au.get ('qsl/%s' % qsl ['id'])
                q  = q ['data']
                if not self.args.dry_run :
                    d = dict (date_recv = rdate)
                    self.au.put \
                        ('qsl/%s' % qsl ['id'], json = d, etag = q ['@etag'])
            elif cmpd and qsl ['date_recv'][:10] != rdate [:10] :
                # We only compare the date, not the time
                # (time is always empty in LOTW)
                self.info \
                    ( "QSL receive time not matching: %s %s %s vs %s"
                    % (date, a.call, qsl ['date_sent'], a.get_qsl_rdate ())
                    )
            qso  = self.au.get ('qso/%s' % qsl ['qso']['id'])
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
                        self.notice \
                            ("QSO %s %s Field %s differs: %s vs %s"
                            % (date, a.call, k, f, v)
                            )
            # Append QSL message if any, only when qsl was first seen
            # Ignore common auto message
            com_msg = ('TNX For QSO TU 73!.', 'TNX For QSL TU 73!.')
            if  ( set_recv_date
                and a.dict.get ('qslmsg')
                and a.qslmsg not in com_msg
                ) :
                    m  = 'QSL message:\n'
                    md = dict \
                        ( content = m + a.qslmsg
                        , type    = 'text/plain'
                        , author  = self.args.username
                        , date    = rdate
                        )
                    if self.args.dry_run :
                        id = '99999'
                    else :
                        r  = self.au.post ('msg', json = md)
                        id = r ['data']['id']
                    m  = list (x ['id'] for x in qso ['messages'])
                    m.append (id)
                    d ['messages'] = m
            if d :
                if not self.args.dry_run :
                    self.au.put ('qso/%s' % q_id, json = d, etag = etag)
                self.notice \
                    ("QSO %s %s updated: %s" % (date, a.call, d))
            qsl_dict = {}
            # Add QSL QSO-Date (peer date) if available
            if a.dict.get ('time_on') and not qsl ['qso_time'] :
                qsl_dict ['qso_time'] = a.get_date ()
            # Add grid if available
            if a.dict.get ('gridsquare') and not qsl ['gridsquare'] :
                qsl_dict ['gridsquare'] = a.gridsquare
            # Add rst_sent (= qsl.rst_rcvd) if available
            # The log (from eqsl at least) if from the perspective of
            # the qso partner.
            if a.dict.get ('rst_sent') and not qsl ['rst_rcvd'] :
                qsl_dict ['rst_rcvd'] = a.rst_sent
            # Add QSL Card from eQSL
            if getattr (self.logbook, 'get_qslcard', 0) and not qsl ['files'] :
                content = self.logbook.get_qslcard (a, self.args.eqsl_username)
                if content :
                    df = dict (type = 'image/png', name = 'qsl')
                    cn = dict (content = content)
                    r  = self.au.post ('file', data = df, files = cn)
                    qsl_dict ['files'] = [r ['data']['id']]
                else :
                    self.notice ("QSL %s %s has no QSL card" % (date, a.call))
            if qsl_dict :
                qsid = qsl ['id']
                # Retrieve qsl and get etag
                r    = self.au.get ('qsl/%s' % qsid)
                etag = r ['data']['@etag']
                if not self.args.dry_run :
                    self.au.put ('qsl/%s' % qsid, json = qsl_dict, etag = etag)
                self.notice \
                    ("QSL %s %s updated: %s" % (date, a.call, qsl_dict))
    # end def do_check_qsl

    def do_export_adif_from_list (self) :
        """ Needs listfile option, this contains a listing that is
            output by the find_qso_without_qsl check of the form
            Call: <date.time> Callsign not in <logservice>
            e.g.
            Call: 2011-06-16.08:53:00 CALLSIGN not in lotw
            This is parsed and an ADIF is generated for upload into the
            respective logging service.
        """
        adif = ADIF ()
        adif.header = 'ADIF export RSC-QSO'
        with open (self.args.listfile) as f :
            for line in f :
                if line.startswith ('Call:') :
                    line = line.split (' ', 1)[1]
                date, call = line.split () [:2]
                qso = self.au.find_qso (call, date)
                adif.append (self.au.qso_as_adif (qso ['id']))
        if self.args.export_adif :
            fn = self.args.export_adif
            with io.open (fn, 'w', encoding = self.args.encoding) as f :
                f.write (text_type (adif))
        else :
            print (adif)
    # end def do_export_adif_from_list

    def do_export_adif_from_query (self) :
        """ Needs adif-query option, this contains a query that used for
            retrieving QSOs.
        """
        adif = ADIF ()
        adif.header = 'ADIF export RSC-QSO'
        q = self.au.get ('qso?' + self.args.adif_query)
        q = q ['data']['collection']
        for k in q :
            adif.append (self.au.qso_as_adif (k ['id']))
        if self.args.export_adif :
            fn = self.args.export_adif
            with io.open (fn, 'w', encoding = self.args.encoding) as f :
                f.write (text_type (adif))
        else :
            print (adif)
    # end def do_export_adif_from_query

    def do_find_qso_without_qsl_in_db (self) :
        """ Loop over all QSOs and find those that do not have a
            corresponding logbook-app QSL. Use the cutoff date for
            selecting the qso_start.
        """
        qtype = self.args.qsl_type
        d = { '@fields' : 'call,qso_start,swl'
            , 'owner'   : self.au.id_call
        }
        if self.cutoff :
            d ['qso_start'] = self.cutoff.strftime (self.au.date_format)
        qso = self.au.get ('qso?' + urlencode (d))
        qso = qso ['data']['collection']
        if self.args.export_adif :
            adif = ADIF ()
            adif.header = 'ADIF export RSC-QSO'
        for n, q in enumerate (qso) :
            call = q ['call']
            qsl = self.au.get ('qsl?qso=%s&qsl_type=%s' % (q ['id'], qtype))
            qsl = qsl ['data']['collection']
            assert len (qsl) <= 1
            if not qsl :
                if q ['swl'] :
                    self.notice ("%s: %s: SWL       " % (n, call))
                else :
                    self.notice \
                        ( "Call: %s %s has no %s qsl"
                        % (q ['qso_start'], call, qtype)
                        )
                    if self.args.export_adif :
                        adif.append (self.au.qso_as_adif (q ['id']))
            else :
                self.animate_info ("%s: found: %s         " % (n, call))
        if self.args.export_adif :
            fn = self.args.export_adif
            with io.open (fn, 'w', encoding = self.args.encoding) as f :
                f.write (text_type (adif))
    # end def do_find_qso_without_qsl_in_db

# end class DB_Importer

def main () :
    methods = [x [3:] for x in DB_Importer.__dict__ if x.startswith ('do_')]
    qsl_types = ['LOTW', 'eQSL']
    default_url = os.environ.get ('WBF_DBURL', 'http://bee.priv.zoo:8080/qso/')
    antenna_defaults = \
        [ '20m:Magnetic Loop D=88cm'
        , '17m:Magnetic Loop D=88cm'
        , '40m:Magnetic Loop D=3.5m'
        , '30m:Magnetic Loop D=1.9m'
        , '15m:Magnetic Loop D=57cm'
        , '12m:Magnetic Loop D=57cm'
        , '10m:Magnetic Loop D=57cm'
        ]
    ant = os.environ.get ('WBF_ANTENNA', '')
    if ant:
        ant = [x.strip () for x in ant.split (',', 1)]
        # Since we're appending to the end these will overwrite existing
        # defaults
        antenna_defaults.extend (ant)
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "command"
        , help    = "Command to execute, allowed: %s" % ', '.join (methods)
        )
    cmd.add_argument \
        ( "adiffile"
        , help    = "ADIF file to import"
        , nargs   = '?'
        )
    cmd.add_argument \
        ( "-a", "--antenna"
        , help    = "Antenna to use for band, colon separated "
                    "band:antenna, later values override earlier values, "
                    "default=%(default)s"
        , action  = 'append'
        , default = antenna_defaults
        )
    cmd.add_argument \
        ( "--archived"
        , help    = "Retrieve archived (value 'yes'), non-archived "
                    "(value 'no') or all records (value 'all') for "
                    "eQSL, default=%(default)s"
        , default = "no"
        )
    cmd.add_argument \
        ( "-A", "--adif-query"
        , help    = "Query to perform for ADIF export with "
                    "export_adif_from_query command"
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
        ( "-D", "--upload-date"
        , help    = "Date when this list of QSLs was uploaded to LOTW"
        )
    cmd.add_argument \
        ( "-e", "--encoding"
        , help    = "Encoding of ADIF file, default=%(default)s"
        , default = 'utf-8'
        )
    cmd.add_argument \
        ( "-E", "--eqsl-username"
        , help    = 'eQSL Username, default="%(default)s"'
        , default = 'oe3rsu'
        )
    cmd.add_argument \
        ( "--eqsl-password"
        , help    = "eQSL Password, better use .netrc"
        )
    cmd.add_argument \
        ( "--export-adif"
        , help    = "Export ADIF to the given file, usable for comands "
                    "export_adif_from_list, find_qso_without_qsl"
        )
    cmd.add_argument \
        ( "--listfile"
        , help    = "File listing QSL records missing in DB"
                    " needed for export_adif_from_list command"
        )
    cmd.add_argument \
        ( "-L", "--lotw-username"
        , help    = 'LOTW Username, default="%(default)s"'
        , default = 'oe3rsu'
        )
    cmd.add_argument \
        ( "--lotw-password"
        , help    = "LOTW Password, better use .netrc"
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
        ( "-q", "--qsl-type"
        , help    = 'QSL type for some actions, allowed: '
                    '%s' % ', '.join (qsl_types)
        )
    cmd.add_argument \
        ( "-U", "--url"
        , help    = "URL of tracker (without rest path) default: %(default)s"
        , default = default_url
        )
    cmd.add_argument \
        ( "-u", "--username"
        , help    = 'Username of hamlog database, default="%(default)s"'
        , default = 'ralf'
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , help    = "Verbose output"
        , action  = 'store_true'
        )
    args   = cmd.parse_args ()
    if args.qsl_type and args.qsl_type not in qsl_types :
        print ("Invalid qsl-type: %s" % args.qsl_type, file = sys.stderr)
        sys.exit (1)
    db = DB_Importer (args)
    try :
        db.execute ()
    except ValueError as e :
        raise
        print ("Error:", e)
# end def main

if __name__ == '__main__' :
    main ()
