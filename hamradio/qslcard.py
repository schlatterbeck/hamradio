#!/usr/bin/python
# Copyright (C) 2021 Dr. Ralf Schlatterbeck Open Source Consulting.
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

import re
import sys
from argparse        import ArgumentParser
from hamradio        import requester
try :
    from urllib.parse import urlencode
except ImportError :
    from urllib import urlencode

class QSL_Exporter (requester.Requester) :

    replacements = dict \
        (( ('<', '$<$')
        ,  ('>', '$>$')
        ,  (',', '{,}')
        ))
    rep = dict ((re.escape (k), v) for k, v in replacements.items ())
    pattern = re.compile ('|'.join (rep.keys ()))

    def __init__ (self, args) :
        self.args = args
        self.__super.__init__ (args.url, args.username, args.password)
        self.set_basic_auth ()
        if not self.url.endswith ('/') :
            self.url += '/'
        self.url += 'rest/data/'
    # end def __init__

    def qsl_iter (self) :
        """ Iterate over all non-sent paper QSL
        """
        bureau = self.get ('qsl_type?name:=%s' % self.args.qsl_type)
        assert len (bureau) == 1
        bureau = bureau ['data']['collection'][0]['id']
        d = dict (date_sent = '-', qsl_type = bureau)
        fields = \
            [ 'qso.call', 'qso.owner.cq_zone', 'qso.owner.itu_zone'
            , 'qso.owner.iota', 'qso.owner.owner.realname'
            , 'qso.owner.call', 'qso.owner.qth', 'qso.qso_start'
            , 'qso.owner.gridsquare', 'qso.qso_end', 'qso.band.name'
            , 'qso.owner.cardname', 'qso.rst_sent', 'qso.mode.name'
            , 'qso.tx_pwr', 'qso.antenna.name', 'qso.owner.name'
            , 'qso.qsl_via', 'qso.swl', 'qso.remarks', 'date_recv'
            , 'qso.owner.dxcc_entity.name', 'qso.owner.dxcc_entity.shortname'
            ]
        d ['@fields'] = ','.join (fields)
        d ['@sort'] = 'qso.owner.name,qso.call,qso.qso_start'
        r = self.get ('qsl?' + urlencode (d)) ['data']['collection']
        for k in r :
            yield (k)
    # end def qsl_iter

    def quoted (self, key) :
        v = self.qsl [key]
        if isinstance (v, int) :
            v = str (v)
        if isinstance (v, type (None)) :
            print ("Warning: Got None object for key=%s" % key, file=sys.stderr)
            return ''
        return self.pattern.sub \
            (lambda m: self.rep [re.escape (m.group (0))], v)
    # end def quoted

    def as_tex (self) :
        r = []
        r.append (r'\documentclass[12pt,german]{qsl}')
        r.append (r'\begin{document}')
        lastcall  = None
        lastowner = None
        for qsl in self.qsl_iter () :
            self.qsl = qsl
            if qsl ['qso.swl'] :
                qslfor = self.get ('qso/%s' % qsl ['qso.swl']['id'])
                qslfor = qslfor ['data']['attributes']
            if  (  lastcall  != qsl ['qso.call']
                or lastowner != qsl ['qso.owner.name']
                ) :
                if lastcall :
                    r.append (r'\end{qslcard}')
                if qsl ['qso.owner.dxcc_entity.shortname'] :
                    country = self.quoted ('qso.owner.dxcc_entity.shortname')
                else :
                    country = self.quoted ('qso.owner.dxcc_entity.name')
                s = ( (r'\begin{qslcard}{' + ','.join (['%s=%s'] * 9))
                    % ( 'ocall',    self.quoted ('qso.owner.call')
                      , 'oname',    self.quoted ('qso.owner.owner.realname')
                      , 'cardname', self.quoted ('qso.owner.cardname')
                      , 'qthname',  self.quoted ('qso.owner.qth')
                      , 'grid',     self.quoted ('qso.owner.gridsquare')
                      , 'cq',       self.quoted ('qso.owner.cq_zone')
                      , 'itu',      self.quoted ('qso.owner.itu_zone')
                      , 'call',     self.quoted ('qso.call')
                      , 'country',  country
                      )
                    )
                if qsl ['qso.owner.iota'] :
                    s += ',iota=%s' % self.quoted ('qso.owner.iota')
                if qsl ['qso.qsl_via'] :
                    s += ',via=%s' % self.quoted ('qso.qsl_via')
                if qsl ['qso.remarks'] :
                    s += ',remarks=%s' % self.quoted ('qso.remarks')
                if qsl ['qso.swl'] :
                    s += ',swl=y'
                if not qsl ['date_recv'] :
                    s += ',wantqsl=y'
                r.append (s + '}')
            dt, tstart = qsl ['qso.qso_start'].split ('.')
            tend       = qsl ['qso.qso_end'].split ('.')[-1]
            # Limit to Minutes
            tstart     = ':'.join (tstart.split (':')[:2])
            if qsl ['qso.swl'] :
                rst_or_call = qslfor ['call']
            else :
                rst_or_call = self.quoted ('qso.rst_sent')
            r.append \
                ( r'\qso' + ('{%s}' * 7)
                % ( dt, tstart
                  , self.quoted ('qso.band.name')
                  , rst_or_call
                  , self.quoted ('qso.mode.name')
                  , self.quoted ('qso.tx_pwr')
                  , self.quoted ('qso.antenna.name')
                  )
                )
            lastcall  = qsl ['qso.call']
            lastowner = qsl ['qso.owner.name']
        r.append (r'\end{qslcard}')
        r.append (r'\end{document}')
        return '\n'.join (r)
    # end def as_tex

    def set_sent_date (self) :
        for qsl in self.qsl_iter () :
            # Get the qsl again to get etag
            q = self.get ('qsl/%s' % qsl ['id'])
            etag = q ['data']['@etag']
            d = dict (date_sent = self.args.sent_date)
            if not self.args.dry_run :
                self.put ('qsl/%s' % qsl ['id'], json = d, etag = etag)
            if self.args.verbose :
                dry = ''
                if self.args.dry_run :
                    dry = ' (dry run)'
                print ('Set %s%s' % (d, dry), file = sys.stderr)
    # end def set_sent_date

# end class QSL_Exporter

def main () :
    cmd  = ArgumentParser ()
    cmd.add_argument \
        ( "-d", "--sent-date", "--send-date"
        , help    = "Set the sending-date of the QSL-Card"
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
        , help    = "QSL type, default=%(default)s"
        , default = 'Bureau'
        )
    cmd.add_argument \
        ( "-U", "--url"
        , help    = "URL of tracker (without rest path) default: %(default)s"
        , default = 'http://bee.priv.zoo:7070/qso/'
        )
    cmd.add_argument \
        ( "-u", "--username"
        , help    = "Username of hamlog database"
        , default = 'ralf'
        )
    cmd.add_argument \
        ( "-v", "--verbose"
        , help    = "Set verbose reporting (only when setting)"
        , action  = 'store_true'
        )
    args = cmd.parse_args ()
    e    = QSL_Exporter (args)
    print (e.as_tex ())
    if args.sent_date :
        e.set_sent_date ()

if __name__ == '__main__' :
    main ()
