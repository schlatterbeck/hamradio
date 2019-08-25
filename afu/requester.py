#!/usr/bin/python
from __future__ import print_function

import requests
from netrc    import netrc
from getpass  import getpass
try :
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from rsclib.autosuper import autosuper

class Requester (autosuper) :

    def __init__ (self, url, username, password = None) :
        self.session  = requests.session ()
        self.url      = url
        self.user     = username
        self.password = password
        self.headers  = {}
    # end def __init__

    def get (self, s) :
        r = self.session.get (self.url + s, headers = self.headers)
        if not (200 <= r.status_code <= 299) :
            raise RuntimeError \
                ( 'Invalid get result: %s: %s\n    %s'
                % (r.status_code, r.reason, r.text)
                )
        return r.json ()
    # end def get

    def get_pw (self) :
        """ Password given as option takes precedence.
            Next we try password via .netrc. If that doesn't work we ask.
        """
        if self.password :
            return self.password
        a = n = None
        try :
            n = netrc ()
        except IOError :
            pass
        if n :
            t = urlparse (self.url)
            a = n.authenticators (t.netloc)
        if a :
            un, d, pw = a
            if un != self.user :
                raise ValueError ("Netrc username doesn't match")
            return pw
        pw = getpass ('Password: ')
        return pw
    # end def get_pw

    def post_or_put (self, method, s, data = None, json = None, etag = None) :
        d = {}
        if data :
            d ['data'] = data
        if json :
            d ['json'] = json
        h = dict (self.headers)
        if etag :
            h ['If-Match'] = etag
        r = method (self.url + s, headers = h, **d)
        if not (200 <= r.status_code <= 299) :
            raise RuntimeError \
                ( 'Invalid put/post result: %s: %s\n    %s'
                % (r.status_code, r.reason, r.text)
                )
        return r.json ()
    # end def post_or_put

    def post (self, s, data = None, json = None, etag = None) :
        return self.post_or_put (self.session.post, s, data, json, etag)
    # end def post

    def put (self, s, data = None, json = None, etag = None) :
        return self.post_or_put (self.session.put, s, data, json, etag)
    # end def put

    def set_basic_auth (self) :
        # Basic Auth: user, password
        self.session.auth = (self.user, self.get_pw ())
    # end def set_basic_auth

# end class Requester
