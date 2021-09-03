#!/usr/bin/python
from __future__ import print_function

from argparse        import ArgumentParser
from afu             import requester
try :
    from urllib.parse import urlencode
except ImportError :
    from urllib import urlencode

class QSL_Exporter (requester.Requester) :

    def __init__ (self, url, username, password = None) :
        self.__super.__init__ (url, username, password)
        self.set_basic_auth ()
        if not self.url.endswith ('/') :
            self.url += '/'
        self.url += 'rest/data/'
    # end def __init__

    def qsl_iter (self) :
        """ Iterate over all non-sent paper QSL
        """
        bureau = self.get ('qsl_type?name:=Bureau')
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
        d ['@fields'] = ','.join (fields)
        d ['@sort'] = 'qso.owner.name,qso.call'
        r = self.get ('qsl?' + urlencode (d)) ['data']['collection']
        for k in r :
            yield (k)
    # end def qsl_iter

    def as_tex (self) :
        r = []
        r.append (r'\documentclass[12pt,german]{qsl}')
        r.append (r'\begin{document}')
        lastcall  = None
        lastowner = None
        for qsl in self.qsl_iter () :
            if  (  lastcall  != qsl ['qso.call']
                or lastowner != qsl ['qso.owner.name']
                ) :
                if lastcall :
                    r.append (r'\end{qslcard}')
                r.append \
                    ( r'\begin{qslcard}' + ('{%s}' * 9)
                    % ( qsl ['qso.owner.call']
                      , qsl ['qso.owner.owner.realname']
                      , qsl ['qso.owner.qth']
                      , qsl ['qso.owner.gridsquare']
                      , qsl ['qso.owner.cq_zone']
                      , qsl ['qso.owner.itu_zone']
                      , qsl ['qso.owner.iota'] or ''
                      , qsl ['qso.owner.cardname']
                      , qsl ['qso.call']
                      )
                    )
            dt, time = qsl ['qso.qso_start'].split ('.')
            time_end = qsl ['qso.qso_end'].split ('.')[-1]
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
    e = QSL_Exporter (url = 'http://bee.priv.zoo:8080/qso/', username = 'ralf', password = 'xyzzy')
    #e.qsl_iter ()
    print (e.as_tex ())

if __name__ == '__main__' :
    main ()
