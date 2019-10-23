#!/usr/bin/python
from __future__ import print_function

import io
import sys
import requests
from locale          import setlocale, LC_TIME
from datetime        import datetime
from argparse        import ArgumentParser
from afu             import requester
from afu.adif        import ADIF
from bs4             import BeautifulSoup
try :
    from urllib.parse import urlencode, urljoin
except ImportError:
    from urllib   import quote as quote_plus
    from urllib   import urlencode
    from urlparse import urljoin

class EQSL_Query (requester.Requester) :

    base_url        = 'https://www.eqsl.cc/qslcard/'
    import_url      = base_url + 'ImportADIF.cfm'
    out_url         = base_url + 'DownloadADIF.cfm'
    in_url          = base_url + 'DownloadInBox.cfm'
    last_upload_url = base_url + 'DisplayLastUploadDate.cfm'

    date_format = '%Y-%m-%d.%H:%M:%S'

    def __init__ (self, nickname, username, password = None) :
        self.nickname = nickname
        self.__super.__init__ \
            (self.import_url, username, password, relax_username_check = True)
    # end def __init__

    def _get_adif (self, linkpage, type = 'Outbox') :
        if 'Your ADIF log file has been built' not in linkpage :
            raise ValueError ("Error getting %s:\n%s" % (type, linkpage))
        soup = BeautifulSoup (linkpage, 'html.parser')
        for a in soup.find_all ('a') :
            href = a.get ('href')
            if 'downloaded' not in href :
                continue
            if not href.endswith ('.adi') :
                continue
            break
        else :
            raise ValueError ("Error getting %s: ADIF url not found" % type)
        self.url = urljoin (self.base_url, href)
        t = self.get ('', as_text = True)
        with io.StringIO (t) as f :
            adif = ADIF (f)
        return adif
    # end def _get_adif

    def get_qso (self, **kw) :
        """ Get whole Outbox as ADIF
            'since' and other parameters are ignored, currently eQSL
            can't limit the downloaded QSOs
        """
        self.url = self.out_url
        d = {}
        d ['UserName']    = self.username
        d ['Password']    = self.get_pw ()
        d ['QTHNickname'] = self.nickname
        t = self.get ('?' + urlencode (d), as_text = True)
        return self._get_adif (t)
    # end def get_qso

    def get_qsl (self, since = '', archived = None, **kw) :
        """ Get Inbox as ADIF
            'since' is a datetime instance
        """
        self.url = self.in_url
        d = {}
        d ['UserName']      = self.username
        d ['Password']      = self.get_pw ()
        d ['QTHNickname']   = self.nickname
        d ['ConfirmedOnly'] = 'yes'
        if since :
            since = since.strftime ('%Y%m%d%H%M')
            d ['RcvdSince'] = since
        if archived is not None :
            d ['Archive']   = int (bool (archived))
        t = self.get ('?' + urlencode (d), as_text = True)
        return self._get_adif (t, 'Inbox')
    # end def get_qsl

    def last_upload (self) :
        self.url = self.last_upload_url
        d = {}
        d ['UserName']      = self.username
        d ['Password']      = self.get_pw ()
        d ['QTHNickname']   = self.nickname
        t = self.get ('?' + urlencode (d), as_text = True)
        oldloc = setlocale (LC_TIME)
        setlocale (LC_TIME, 'C')
        fmt = '%d-%b-%Y at %H:%M:%S'
        soup = BeautifulSoup (t, 'html.parser')
        body = soup.find ('body').get_text ()
        text = 'Your last ADIF upload was'
        for line in body.split ('\n') :
            line = line.strip ()
            if line.startswith (text) :
                l  = line [len (text) + 1:]
                if not l.endswith ('M UTC') :
                    raise ValueError ('Invalid timestamp format encountered')
                l = l [:-7]
                dt = datetime.strptime (l, fmt)
                break
        else :
            raise ValueError ('Did not find Timestamp in page:\n%s' % body)
        setlocale (LC_TIME, oldloc)
        return dt
    # end def last_upload

# end class EQSL_Query

def main () :
    e = EQSL_Query (sys.argv [1], sys.argv [2])
    print (e.last_upload ().strftime ('%Y-%m-%d.%H:%M:%S'))
    #print (e.get_qso ())

if __name__ == '__main__' :
    main ()
