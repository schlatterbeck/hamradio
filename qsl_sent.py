import sys
import os
from optparse import OptionParser
from datetime import datetime
from adif     import ADIF, TQ8
from roundup  import date
from roundup  import instance

def date_cvt (d, t = '0000') :
    s  = '.'.join ((d, t))
    dt = datetime.strptime (s, '%Y%m%d.%H%M')
    return date.Date (dt)
# end def date_cvt

def main () :
    global uni
    parser = OptionParser ()
    parser.add_option \
        ( "-8", "--tq8"
        , dest    = "tq8"
        , help    = "tq8 file to import"
        , default = None
        )
    parser.add_option \
        ( "-a", "--adif"
        , dest    = "adif"
        , help    = "ADIF file to import (default: read from stdin)"
        , default = None
        )
    parser.add_option \
        ( "-d", "--database-directory"
        , dest    = "database_directory"
        , help    = "Directory of the roundup installation"
        , default = '.'
        )
    parser.add_option \
        ( "-r", "--qsl-recv"
        , dest    = "date_recv"
        , help    = "Timestamp when QSL was received"
        , default = None
        )
    parser.add_option \
        ( "-s", "--qsl-sent"
        , dest    = "date_sent"
        , help    = "Timestamp when QSL was sent"
        , default = None
        )
    parser.add_option \
        ( "-t", "--qsl-type"
        , dest    = "qsl_type"
        , help    = "Type of QSL (e.g. eQSL or LOTW)"
        , default = 'eQSL'
        )
    parser.add_option \
        ( "-u", "--username"
        , dest    = "username"
        , help    = "Username of hamlog database"
        , default = 'admin'
        )
    opt, args = parser.parse_args ()
    sys.path.insert (1, os.path.join (opt.database_directory, 'lib'))
    from rup_utils import uni
    tracker = instance.open (opt.database_directory)
    db      = tracker.open (opt.username)

    type    = db.qsl_type.lookup (opt.qsl_type)
    if not (opt.date_recv or opt.date_sent) :
        parser.error ("Either sent or recv timestamp must be given")
        sys.exit (1)

    if opt.tq8 :
        f = open (opt.tq8, 'r')
    elif opt.adif :
        f = open (opt.adif, 'r')
    else :
        f = sys.stdin
    if opt.tq8 :
        adif = TQ8 (f)
    else :
        adif = ADIF (f)
    ccount = ucount = 0
    for record in adif.records :
        if 'TIME_ON' not in record :
            ds = date.Date \
                ('.'.join ((record ['QSO_DATE'], record ['QSO_TIME'][:-1])))
        else :
            ds = date_cvt (record ['QSO_DATE'], record ['TIME_ON'])
        if 'TIME_OFF' in record :
            if 'QSO_DATE_OFF' in record :
                de = date_cvt (record ['QSO_DATE_OFF'], record ['TIME_OFF'])
            else :
                de = date_cvt (record ['QSO_DATE'], record ['TIME_OFF'])
                if de < ds :
                    print "time correction"
                    de += date.Interval ('1h')
            assert (de >= ds)
        else :
            de = None
        call = record ['CALL']
        if de :
            pp = ';'.join ((str (de), str (de)))
            dr = db.qso.filter (None, dict (qso_end = pp, call = call))
        else :
            pp = ';'.join ((str (ds), str (ds)))
            dr = db.qso.filter (None, dict (qso_start = pp, call = call))
        assert (len (dr) <= 1)
        if not dr :
            x = 'ending'
            d = de
            if not de :
                x = 'starting'
                d = ds
            print "No QSO found for %s %s %s" % (record ['CALL'], x, str (d))
            continue
        qso = dr [0]
        qsl = db.qsl.filter (None, dict (qso = qso, qsl_type = type))
        assert (len (qsl) <= 1)
        if qsl :
            qsl   = qsl [0]
            cdict = {}
        else :
            cdict = dict (qso = qso, qsl_type = type)
        if opt.date_sent :
            cdict ['date_sent'] = date.Date (opt.date_sent)
        if opt.date_recv :
            cdict ['date_recv'] = date.Date (opt.date_recv)
        if not qsl :
            db.qsl.create (**cdict)
            ccount += 1
        else :
            n = db.qsl.getnode (qsl)
            for k in 'date_sent', 'date_recv' :
                if n [k] and k in cdict :
                    print "Not changing QSL for QSO %s" % qso
                    break
            else :
                db.qsl.set (qsl, **cdict)
    db.commit ()
    print "created %s QSLs, updated %s QSLs" % (ccount, ucount)
# end def main

if __name__ == '__main__' :
    main ()
