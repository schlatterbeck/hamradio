#!/usr/bin/python3
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

import sys
from bisect import bisect_right

class Band :

    def __init__ (self, bandplan, name, f_start, f_end) :
        self.name    = name
        self.f_start = f_start
        self.f_end   = f_end
        self.plan    = bandplan
    # end def __init__

    def __str__ (self) :
        if self.f_start > 1e9 :
            range = '%.3f GHz-%.3f GHz' % (self.f_start / 1e9, self.f_end / 1e9)
        elif self.f_start > 1e6 :
            range = '%.3f MHz-%.3f MHz' % (self.f_start / 1e6, self.f_end / 1e6)
        elif self.f_start > 1e3 :
            range = '%.3f kHz-%.3f kHz' % (self.f_start / 1e3, self.f_end / 1e3)
        else :
            range = '%.3f Hz-%.3f Hz' % (self.f_start, self.f_end)
        return 'Band %s %s' % (self.name, range)
    # end def __str__
    __repr__ = __str__

    def __lt__ (self, other) :
        return self.f_start < other.f_start
    # end def __lt__

# end class Band

class Overlap_Error (ValueError) :
    """ This is raised if an inserted band overlaps an existing one
    """
    pass

class Bandplan :
    """ Keep track of a set of Band objects.
        These typically constitute a national band plan.
    """

    def __init__ (self) :
        """ This is kept sorted for a little faster lookup
        """
        self.bands = []
    # end def __init__

    def add_band (self, band) :
        idx = bisect_right (self.bands, band)
        l   = len (self.bands)
        if idx > 0 and idx < l and self.bands [idx].end > band.start :
            raise Overlap_Error \
                ('New band %s overlaps existing %s' % (band, self.bands [idx]))
        self.bands.insert (idx, band)
    # end def add_band

    def lookup (self, frq) :
        b   = Band (None, 'dummy', frq, frq)
        idx = bisect_right (self.bands, b) - 1
        if idx < 0 :
            return
        entry = self.bands [idx]
        if idx and entry.f_start <= frq <= entry.f_end :
            return entry
    # end def

# end class Bandplan

# Sources:
# https://www.oevsv.at/funkbetrieb/amateurfunkfrequenzen/hf-referat/
# https://www.oevsv.at/export/shared/.content/.galleries/Downloads_Referate/UKW-Referat-Downloads/UKW-Bandplan.pdf
# https://www.oevsv.at/oevsv/aktuelles/60m-Band-und-630m-Band-nun-in-Oesterreich-fuer-den-Amateurfunk-freigegeben/
bandplan_austria = bpa = Bandplan ()
bpa.add_band (Band (bpa, '2.2km',   135.7e3,   137.8e3))
bpa.add_band (Band (bpa, '630m',    472.0e3,   479.0e3))
bpa.add_band (Band (bpa, '160m',   1810.0e3,  2000.0e3))
bpa.add_band (Band (bpa, '80m',    3500.0e3,  3800.0e3))
bpa.add_band (Band (bpa, '60m',    5351.3e3,  5366.5e3))
bpa.add_band (Band (bpa, '40m',    7000.0e3,  7200.0e3))
bpa.add_band (Band (bpa, '30m',   10100.0e3, 10150.0e3))
bpa.add_band (Band (bpa, '20m',   14000.0e3, 14350.0e3))
bpa.add_band (Band (bpa, '17m',   18068.0e3, 18168.0e3))
bpa.add_band (Band (bpa, '15m',   21000.0e3, 21450.0e3))
bpa.add_band (Band (bpa, '12m',   24890.0e3, 24990.0e3))
bpa.add_band (Band (bpa, '10m',   28000.0e3, 29700.0e3))
bpa.add_band (Band (bpa, '6m',       50.0e6,    52.0e6))
bpa.add_band (Band (bpa, '2m',      144.0e6,   146.0e6))
bpa.add_band (Band (bpa, '70cm',    430.0e6,   440.0e6))

__all__ = ['bandplan_austria', 'Band', 'Bandplan', 'Overlap_Error']

if __name__ == '__main__' :
    #for b in bandplan_austria.bands :
    #    print (b)
    band = bandplan_austria.lookup (float (sys.argv [1]))
    print (band)
