#!/usr/bin/python
from __future__ import print_function

import re
from argparse        import ArgumentParser
from afu             import requester
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
        fields = ['qso.call', 'qso.owner.cq_zone', 'qso.owner.itu_zone']
        fields.extend (['qso.owner.iota', 'qso.owner.owner.realname'])
        fields.extend (['qso.owner.call', 'qso.owner.qth', 'qso.qso_start'])
        fields.extend (['qso.owner.gridsquare', 'qso.qso_end'])
        fields.extend (['qso.band.name', 'qso.owner.cardname'])
        fields.extend (['qso.rst_sent', 'qso.mode.name', 'qso.tx_pwr'])
        fields.extend (['qso.antenna.name', 'qso.owner.name'])
        fields.extend (['qso.qsl_via', 'qso.swl'])
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
        return self.pattern.sub \
            (lambda m: self.rep [re.escape (m.group (0))], v)
        #for k in self.replacements :
        #    v = v.replace (k, self.replacements [k])
        #return v
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
                s = ( (r'\begin{qslcard}{' + ','.join (['%s=%s'] * 8))
                    % ( 'ocall',    self.quoted ('qso.owner.call')
                      , 'oname',    self.quoted ('qso.owner.owner.realname')
                      , 'cardname', self.quoted ('qso.owner.cardname')
                      , 'qthname',  self.quoted ('qso.owner.qth')
                      , 'grid',     self.quoted ('qso.owner.gridsquare')
                      , 'cq',       self.quoted ('qso.owner.cq_zone')
                      , 'itu',      self.quoted ('qso.owner.itu_zone')
                      , 'call',     self.quoted ('qso.call')
                      )
                    )
                if qsl ['qso.owner.iota'] :
                    s += ',iota=%s' % self.quoted ('qso.owner.iota')
                if qsl ['qso.qsl_via'] :
                    s += ',via=%s' % self.quoted ('qso.qsl_via')
                if qsl ['qso.swl'] :
                    s += ',swl=y'
                r.append (s + '}')
            dt, time = qsl ['qso.qso_start'].split ('.')
            time_end = qsl ['qso.qso_end'].split ('.')[-1]
            if qsl ['qso.swl'] :
                rst_or_call = qslfor ['call']
            else :
                rst_or_call = self.quoted ('qso.rst_sent')
            r.append \
                ( r'\qso' + ('{%s}' * 7)
                % ( dt, time
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

# end class QSL_Exporter

def main () :
    cmd  = ArgumentParser ()
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
        ( "-p", "--password"
        , help    = "Password, better use .netrc"
        )
    cmd.add_argument \
        ( "-q", "--qsl-type"
        , help    = "QSL type, default=%(default)s"
        , default = 'Bureau'
        )
    args = cmd.parse_args ()
    e    = QSL_Exporter (args)
    print (e.as_tex ())

if __name__ == '__main__' :
    main ()
