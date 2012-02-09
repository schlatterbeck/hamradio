#!/usr/bin/python

from datetime          import datetime
from netrc             import netrc
from string            import maketrans
from rsclib.autosuper  import autosuper
from rsclib.HTML_Parse import Page_Tree, tag
from rsclib.ETree      import ETree

class QRZ_Login (Page_Tree) :
    site = 'http://qrz.com'
    url  = 'li/%s'

    def __init__ (self, *args, **kw) :
        username, password = self.get_auth ()
        self.url = self.url % datetime.now ().strftime ('%s')
        d = dict (username = username, password = password)
        self.__super.__init__ (*args, post = d, **kw)
    # end def __init__

    def get_auth (self, netrc_file = None, netrc_host = 'qrz.com') :
        n = netrc (netrc_file)
        a = n.authenticators (netrc_host)
        return a [0], a[2]
    # end def get_auth
# end class QRZ_Login

class QRZ_COM_Callsign (Page_Tree) :
    site = 'http://qrz.com'
    translation = maketrans (' -', '__')

    def __init__ (self, callsign, cookies = None, *args, **kw) :
        if cookies :
            self.cookies = cookies
        else :
            self.cookies = QRZ_Login ().cookies
        url         = 'db/%s' % callsign
        self.detail = {}
        self.__super.__init__ (*args, cookies = self.cookies, url = url, **kw)
    # end def __init__

    def parse (self) :
        for d in self.tree.getroot ().findall ('.//%s' % tag ('div')) :
            if d.get ('id') == 't_detail' :
                detail = d
                break
        else :
            raise ValueError, "No details found"
        for tbl in detail.findall ('.//%s' % tag ('table')) :
            if tbl.get ('id') == 'dt' :
                break
        for tr in tbl.findall ('.//%s' % tag ('tr')) :
            tds = tr.findall ('./%s' % tag ('td'))
            if len (tds) != 2 :
                continue
            key = ETree (tds [0]).get_text ()
            print repr (key)
            key = ETree (tds [0]).get_text ().translate (self.translation, '?')
            val = ETree (tds [1]).get_text ()
            self.detail [key] = val
    # end def parse
# end class QRZ_COM_Callsign

if __name__ == '__main__' :
    import sys
    q = QRZ_COM_Callsign ('oe4dns')
    print q.tree_as_string ()
    print q.cookies
    print q.detail
