#!/usr/bin/python
from __future__ import print_function

import sys
import os
import io
from argparse import ArgumentParser
from datetime import datetime
from adif     import ADIF
from roundup  import date
from roundup  import instance
from roundup.anypy.strings import u2s

def date_cvt (d, t = '0000') :
    s  = '.'.join ((d, t))
    dt = datetime.strptime (s, '%Y%m%d.%H%M')
    return date.Date (dt)
# end def date_cvt

def main () :
    parser = ArgumentParser ()
    parser.add_argument \
        ( "adif"
        , help    = "ADIF file to import"
        )
    parser.add_argument \
        ( "-c", "--call"
        , help    = "Callsign to use for local DB"
        , default = 'OE3RSU Weidling'
        )
    parser.add_argument \
        ( "-d", "--database-directory"
        , help    = "Directory of the roundup installation"
        , default = '.'
        )
    parser.add_argument \
        ( "-e", "--encoding"
        , help    = "Encoding of ADIF file, default=%(default)s"
        , default = 'utf-8'
        )
    parser.add_argument \
        ( "-n", "--dry-run"
        , help    = "Dry run, do nothing"
        , action  = 'store_true'
        )
    parser.add_argument \
        ( "-u", "--username"
        , help    = "Username of hamlog database"
        , default = 'admin'
        )
    parser.add_argument \
        ( "-v", "--verbose"
        , help    = "Verbose output"
        , action  = 'store_true'
        )
    args = parser.parse_args ()
    sys.path.insert (1, os.path.join (args.database_directory, 'lib'))
    tracker = instance.open (args.database_directory)
    db      = tracker.open (args.username)
    call    = db.ham_call.lookup (args.call)
    mycall  = db.ham_call.getnode (call)

    f = io.open (args.adif, 'r', encoding = args.encoding)
    adif  = ADIF (f)
    count = 0
    lotw  = db.qsl_type.lookup ('LOTW')
    for record in adif.records :
        aprops = set (('qso_date', 'time_on', 'time_off'))
        ds = date_cvt (record ['qso_date'], record ['time_on'])
        if 'qso_date_off' in record :
            aprops.add ('qso_date_off')
            de = date_cvt (record ['qso_date_off'], record ['time_off'])
        else :
            de = date_cvt (record ['qso_date'], record ['time_off'])
            if de < ds :
                print ("time correction")
                de += date.Interval ('1h')
        assert (de >= ds)
        pp = ';'.join ((str (de), str (de)))
        dr = db.qso.filter (None, dict (qso_end = pp, owner = call))
        if dr :
            dupe = False
            for d in dr :
                q = db.qso.getnode (d)
                if (q.call != record ['call']) :
                    print \
                        ( "Same end-time but different calls: %s %s %s"
                        % (de, q.call, record ['call'])
                        )
                else :
                    print ("Existing record:", de)
                    dupe = True
            if dupe :
                continue
        create_dict = dict (qso_start = ds, qso_end = de, owner = call)
        if 'band' in record :
            b = db.ham_band.lookup (record ['band'])
            create_dict ['band'] = b
            aprops.add ('band')
        if 'mode' in record :
            m = db.ham_mode.lookup (record ['mode'])
            create_dict ['mode'] = m
            aprops.add ('mode')
        if 'notes' in record :
            if not args.dry_run :
                m = db.msg.create (content = u2s (record ['notes']))
            else :
                m = '99999'
            create_dict ['messages'] = [m]
            aprops.add ('notes')
        if 'qslrdate' in record :
            qslrdate = record ['qslrdate']
            aprops.add ('qslrdate')
        if 'qslsdate' in record :
            qslsdate = record ['qslsdate']
            aprops.add ('qslsdate')
        if 'my_gridsquare' in record :
            if mycall.gridsquare.lower () != record ['my_gridsquare'].lower () :
                raise ValueError \
                    ( "Invalid grid %s, expected %s"
                    % (record ['my_gridsquare'], mycall.gridsquare)
                    )
            aprops.add ('my_gridsquare')
        if 'station_callsign' in record :
            if mycall.call.lower () != record ['station_callsign'].lower () :
                raise ValueError \
                    ( "Invalid call %s, expected %s"
                    % (record ['station_callsign'], mycall.call)
                    )
            aprops.add ('station_callsign')
        dryrun = ''
        if args.dry_run :
            dryrun = '[dry run] '
        for p in db.qso.properties :
            ap = p.lower ()
            if ap not in aprops and ap in record :
                aprops.add (ap)
                create_dict [p] = u2s (record [ap])
        missing_fields = set (record.dict.iterkeys ()) - aprops
        if missing_fields :
            raise RuntimeError ("Missing fields: %s" % str (missing_fields))
        if args.verbose :
            print ("%sCreate QSO: %s" % (dryrun, create_dict))
        if not args.dry_run :
            qso = db.qso.create (**create_dict)
        qsl = None
        if 'qslrdate' in aprops :
            dr = date_cvt (qslrdate)
            a  = dict (qsl_type = lotw, qso = qso, date_recv = dr)
            if verbose :
                print ("%sCreate QSL: %s" % (dryrun, a))
            if not args.dry_run :
                qsl = db.qsl.create (** a)
        if 'qslsdate' in aprops :
            ds = date_cvt (qslsdate)
            if not qsl :
                print ("Warning: no recv qsl: %s" % de)
            else :
                if not args.dry_run :
                    db.qsl.set (qsl, date_sent = ds)
                print ("%sSet QSL: date_sent = %s" % (dryrun, ds))
        count += 1
    if not args.dry_run :
        db.commit ()
    print ("Inserted %d records" % count)
# end def main

if __name__ == '__main__' :
    main ()
