#!/usr/bin/python3
# Copyright (C) 2019 Dr. Ralf Schlatterbeck Open Source Consulting.
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

from rsclib.iter_recipes import grouper

class Maidenhead_Locator (object) :
    """ Represent a location with LAT/LON as Maidenhead Locator
    >>> cls = Maidenhead_Locator
    >>> loc = cls (48.208525, 16.373146)
    >>> loc
    48°12'30.69"N 16°22'23.33"E
    >>> loc.as_locator (precision = 4)
    'JN88EF40'
    >>> loc = cls (48, 16, 12, 22, 30.69, 23.33)
    >>> loc
    48°12'30.69"N 16°22'23.33"E
    >>> loc = cls.from_locator ('JN88', round_vhf = True)
    >>> loc.as_locator (3)
    'JN88LL'
    >>> loc.as_locator (4)
    'JN88LL44'
    >>> loc.as_locator (5)
    'JN88LL44LL'
    >>> loc.as_locator (6)
    'JN88LL44LL44'
    >>> loc
    48°28'37.16"N 16°57'14.33"E
    >>> cls (48, 16, 28, 57, 37.16, 14.33).as_locator (6)
    'JN88LL44LL44'
    >>> loc = cls.from_locator ('JN88ef40', round_vhf = True)
    >>> loc
    48°12'37.15"N 16°22'14.31"E
    >>> print ("(%2.5f, %2.5f)" % (loc.lat, loc.lon))
    (48.21032, 16.37064)
    >>> loc.as_locator (5)
    'JN88EF40LL'
    >>> loc = cls.from_locator ('JN88', round_vhf = False)
    >>> loc.as_locator (7)
    'JN88MM00AA00AA'
    """

    def __init__ (self, lat, lon, lat_m = 0, lon_m = 0, lat_s = 0, lon_s = 0) :
        self.lat = lat
        self.lon = lon
        if lat_m :
            self.lat += lat_m / 60.
        if lon_m :
            self.lon += lon_m / 60.
        if lat_s :
            self.lat += lat_s / 3600.
        if lon_s :
            self.lon += lon_s / 3600.
    # end def __init__

    def as_locator (self, precision = 3) :
        """ Output position as precision maidenhead pairs, e.g., with
            precision=3 we get JN88EF for Stefansdom Wien.
        """
        loc = []
        pos = ((self.lon + 180.) / 2., self.lat + 90.)
        div = 10
        for k in range (precision) :
            np = []
            for p in pos :
                q, r = divmod (p, div)
                if k % 2 :
                    loc.append (str (int (q)))
                    np.append (r * 10)
                else :
                    loc.append (chr (ord ('A') + int (q)))
                    np.append (r * 24)
            pos = np
            if k % 2 :
                div = 10
            else :
                div = 24
        return ''.join (loc)
    # end def as_locator

    @classmethod
    def from_locator (cls, loc, round_vhf = True) :
        """ See VHF Handbook V 8.5
            https://www.iaru-r1.org/index.php/downloads/func-startdown/1018/
            for the rounding constant (empirically derived here).
            They specify that to make a locator "longer" we have to
            append 'LL' or '44' for the letter or digit part,
            respectively. This is slightly lower than the middle.
        """
        rounding_constant = 0.47699
        if not round_vhf :
            rounding_constant = .5
        pos = [0.0, 0.0]
        mul = 10
        for n, l in enumerate (grouper (2, loc)) :
            npos = []
            for idx, k in enumerate (l) :
                if not k.isdigit () :
                    k = ord (k.upper ()) - ord ('A')
                else :
                    k = int (k)
                pos [idx] += k * mul
            if n % 2 :
                newmul = 24
            else :
                newmul = 10
            mul = mul / newmul
        pos [0] += mul * newmul * rounding_constant
        pos [1] += mul * newmul * rounding_constant
        return cls (lon = pos [0] * 2 - 180, lat = pos [1] - 90)
    # end def from_locator

    def _format (self, value, suffices) :
        r      = []
        suffix = suffices [value > 0]
        value  = abs (value)
        r.append (int (value))
        r.append ('°')
        for s in ("'", '"') :
            value -= int (value)
            value *= 60
            if s == '"' :
                r.append ("%2.2f" % value)
            else :
                r.append (int (value))
            r.append (s)
        r.append (suffix)
        return ''.join (str (x) for x in r)
    # end def _format

    def __str__ (self) :
        r = []
        for v, s in ((self.lat, 'SN'), (self.lon, 'WE')) :
            r.append (self._format (v, s))
        return ' '.join (r)
    # end def __str__
    __repr__ = __str__

# end class Maidenhead_Locator
