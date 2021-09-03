#!/usr/bin/python
from __future__ import print_function

from argparse        import ArgumentParser
from afu             import requester
try :
    from urllib.parse import urlencode
except ImportError :
    from urllib import urlencode

class QSL_Exporter (requester.Requester) :

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

    def _arg (self, n) :
        return '{' + '{%s}' * n + '}'
    # end def _arg

    def as_tex (self) :
        r = []
        r.append (r'\documentclass[12pt,german]{qsl}')
        r.append (r'\begin{document}')
        lastcall  = None
        lastowner = None
        for qsl in self.qsl_iter () :
            if qsl ['qso.swl'] :
                qslfor = self.get ('qso/%s' % qsl ['qso.swl']['id'])
                qslfor = qslfor ['data']['attributes']
            if  (  lastcall  != qsl ['qso.call']
                or lastowner != qsl ['qso.owner.name']
                ) :
                if lastcall :
                    r.append (r'\end{qslcard}')
                is_swl = ''
                if qsl ['qso.swl'] :
                    is_swl = 'y'
                r.append \
                    ( ( r'\begin{qslcard}'
                      + self._arg (3) # owner info
                      + self._arg (2) # qth + grid
                      + self._arg (3) # zones + iota
                      + self._arg (3) # call, via, swl
                      )
                    % ( qsl ['qso.owner.call']
                      , qsl ['qso.owner.owner.realname']
                      , qsl ['qso.owner.cardname']
                      , qsl ['qso.owner.qth']
                      , qsl ['qso.owner.gridsquare']
                      , qsl ['qso.owner.cq_zone']
                      , qsl ['qso.owner.itu_zone']
                      , qsl ['qso.owner.iota'] or ''
                      , qsl ['qso.call']
                      , qsl ['qso.qsl_via'] or ''
                      , is_swl
                      )
                    )
            dt, time = qsl ['qso.qso_start'].split ('.')
            time_end = qsl ['qso.qso_end'].split ('.')[-1]
            rst_or_call = qsl ['qso.rst_sent']
            if qsl ['qso.swl'] :
                rst_or_call = qslfor ['call']
            r.append \
                ( r'\qso' + ('{%s}' * 7)
                % ( dt, time
                  , qsl ['qso.band.name']
                  , qsl ['qso.rst_sent']
                  , qsl ['qso.mode.name']
                  , qsl ['qso.tx_pwr']
                  , qsl ['qso.antenna.name']
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
