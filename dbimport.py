import sys
import os
from optparse import OptionParser
from datetime import datetime
from adif     import ADIF
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
        ( "-d", "--database-directory"
        , dest    = "database_directory"
        , help    = "Directory of the roundup installation"
        , default = '.'
        )
    parser.add_option \
        ( "-u", "--username"
        , dest    = "username"
        , help    = "Username of hamlog database"
        , default = 'admin'
        )
    parser.add_option \
        ( "-a", "--adif"
        , dest    = "adif"
        , help    = "ADIF file to import (default: read from stdin)"
        , default = None
        )
    opt, args = parser.parse_args ()
    if len (args) != 1 :
        parser.error ('Call-name must be given')
        exit (23)
    sys.path.insert (1, os.path.join (opt.database_directory, 'lib'))
    from rup_utils import uni
    tracker = instance.open (opt.database_directory)
    db      = tracker.open (opt.username)
    call    = db.ham_call.lookup (args [0])

    if opt.adif :
        f = open (opt.adif, 'r')
    else :
        f = sys.stdin
    adif  = ADIF (f)
    count = 0
    lotw  = db.qsl_type.lookup ('LOTW')
    for record in adif.records :
        aprops = set (('QSO_DATE', 'TIME_ON', 'TIME_OFF'))
        ds = date_cvt (record ['QSO_DATE'], record ['TIME_ON'])
        if 'QSO_DATE_OFF' in record :
            aprops.add ('QSO_DATE_OFF')
            de = date_cvt (record ['QSO_DATE_OFF'], record ['TIME_OFF'])
        else :
            de = date_cvt (record ['QSO_DATE'], record ['TIME_OFF'])
            if de < ds :
                print "time correction"
                de += date.Interval ('1h')
        assert (de >= ds)
        pp = ';'.join ((str (de), str (de)))
        dr = db.qso.filter (None, dict (qso_end = pp))
        if dr :
            print "Existing record:", de
            continue
        create_dict = dict (qso_start = ds, qso_end = de, owner = call)
        if 'BAND' in record :
            b = db.ham_band.lookup (record ['BAND'])
            create_dict ['band'] = b
            aprops.add ('BAND')
        if 'MODE' in record :
            m = db.ham_mode.lookup (record ['MODE'])
            create_dict ['mode'] = m
            aprops.add ('MODE')
        if 'NOTES' in record :
            m = db.msg.create (content = uni (record ['NOTES']))
            create_dict ['messages'] = [m]
            aprops.add ('NOTES')
        if 'QSLRDATE' in record :
            qslrdate = record ['QSLRDATE']
            aprops.add ('QSLRDATE')
        if 'QSLSDATE' in record :
            qslsdate = record ['QSLSDATE']
            aprops.add ('QSLSDATE')
        for p in db.qso.properties :
            ap = p.upper ()
            if ap not in aprops and ap in record :
                aprops.add (ap)
                create_dict [p] = uni (record [ap])
        missing_fields = set (record.dict.iterkeys ()) - aprops
        if missing_fields :
            raise RuntimeError, "Missing fields: %s" % str (missing_fields)
        qso = db.qso.create (**create_dict)
        qsl = None
        if 'QSLRDATE' in aprops :
            dr = date_cvt (qslrdate)
            qsl = db.qsl.create (qsl_type = lotw, qso = qso, date_recv = dr)
        if 'QSLSDATE' in aprops :
            ds = date_cvt (qslsdate)
            if not qsl :
                print "Warning: no recv qsl: %s" % de
            else :
                db.qsl.set (qsl, date_sent = ds)
        count += 1
    db.commit ()
    print "Inserted %d records" % count
# end def main

if __name__ == '__main__' :
    main ()
