#!/usr/bin/python
# Copyright (C) 2019-22 Dr. Ralf Schlatterbeck Open Source Consulting.
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

import requests
from netrc    import netrc
from getpass  import getpass
try :
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
from rsclib.autosuper import autosuper

class Requester (autosuper) :

    def __init__ (self, url, username, password = None, **kw) :
        self.session     = requests.session ()
        self.url         = url
        self.username    = username
        self.password    = password
        self.headers     = {}
        self._pw         = None
        self.relax_check = False
        self.cookies     = None
        if kw.get ('relax_username_check', False) :
            self.relax_check = True
        self.__super.__init__ (**kw)
    # end def __init__

    def get (self, s, as_text=False, as_result = False, **kw) :
        r = self.session.get (self.url + s, headers = self.headers, **kw)
        if not (200 <= r.status_code <= 299) :
            raise RuntimeError \
                ( 'Invalid get result: %s: %s\n    %s'
                % (r.status_code, r.reason, r.text)
                )
        if as_result :
            return r
        if as_text :
            return r.text
        return r.json ()
    # end def get

    def get_pw (self) :
        """ Password given as option takes precedence.
            Next we try password via .netrc. If that doesn't work we ask.
        """
        if self._pw :
            return self._pw
        if self.password :
            self._pw = self.password
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
            if not self.relax_check and un != self.username :
                raise ValueError \
                    ( "Netrc username for %s doesn't match (expected: %s)"
                    % (t.netloc, un)
                    )
            self._pw = pw
            return pw
        pw = getpass ('Password: ')
        self._pw = pw
        return pw
    # end def get_pw

    def post_or_put \
        ( self, method, s
        , data      = None
        , json      = None
        , etag      = None
        , as_text   = False
        , as_result = False
        , **kw
        ) :
        d = {}
        d.update (kw)
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
        if as_result :
            return r
        if as_text :
            return r.text
        return r.json ()
    # end def post_or_put

    def post (self, s, **kw) :
        return self.post_or_put (self.session.post, s, ** kw)
    # end def post

    def put (self, s, **kw) :
        return self.post_or_put (self.session.put, s, ** kw)
    # end def put

    def set_basic_auth (self) :
        # Basic Auth: user, password
        self.session.auth = (self.username, self.get_pw ())
    # end def set_basic_auth

# end class Requester
