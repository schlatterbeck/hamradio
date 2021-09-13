#!/usr/bin/python3

import io
import sys
import os

# Sources
# Big CTY list:
# https://www.country-files.com/big-cty-06-september-2021/
# Official WAE:
# https://www.darc.de/en/der-club/referate/committee-dx/diplome/wae-award/wae-country-list/

# These are different ways to render the same thing in cty.dat vs. ARRLs
# DXCC list.
cty_to_dxcc = dict \
    (( ('Agalega & St. Brandon',    'Agalega & St. Brandon Is.')
    ,  ('Aland Islands',            'Aland Is.')
    ,  ('Annobon Island',           'Annobon I.')
    ,  ('Ascension Island',         'Ascension I.')
    ,  ('Asiatic Turkey',           'Turkey')
    ,  ('Austral Islands',          'Austral I.')
    ,  ('Aves Island',              'Aves I.')
    ,  ('Baker & Howland Islands',  'Baker & Howland Is.')
    ,  ('Balearic Islands',         'Balearic Is.')
    ,  ('Banaba Island',            'Banaba I. (Ocean I.)')
    ,  ('British Virgin Islands',   'British Virgin Is.')
    ,  ('Canary Islands',           'Canary Is.')
    ,  ('Cayman Islands',           'Cayman Is.')
    ,  ('Central African Republic', 'Central Africa')
    ,  ('Central Kiribati',         'C. Kiribati (British Phoenix Is.)')
    ,  ('Chagos Islands',           'Chagos Is.')
    ,  ('Chatham Islands',          'Chatham Is.')
    ,  ('Chesterfield Islands',     'Chesterfield Is.')
    ,  ('Christmas Island',         'Christmas I.')
    ,  ('Clipperton Island',        'Clipperton I.')
    ,  ('Cocos (Keeling) Islands',  'Cocos (Keeling) Is.')
    ,  ('Cocos Island',             'Cocos I.')
    ,  ('Crozet Island',            'Crozet I.')
    ,  ('DPR of Korea',             "Democratic People's Rep. of Korea")
    ,  ('Dem. Rep. of the Congo',   'Democratic Republic of the Congo')
    ,  ('Desecheo Island',          'Desecheo I.')
    ,  ('Ducie Island',             'Ducie I.')
    ,  ('Easter Island',            'Easter I.')
    ,  ('Eastern Kiribati',         'E. Kiribati (Line Is.)')
    ,  ('Falkland Islands',         'Falkland Is.')
    ,  ('Faroe Islands',            'Faroe Is.')
    ,  ('Fed. Rep. of Germany',     'Federal Republic of Germany')
    ,  ('Galapagos Islands',        'Galapagos Is.')
    ,  ('Glorioso Islands',         'Glorioso Is.')
    ,  ('Heard Island',             'Heard I.')
    ,  ('Johnston Island',          'Johnston I.')
    ,  ('Juan Fernandez Islands',   'Juan Fernandez Is.')
    ,  ('Kerguelen Islands',        'Kerguelen Is.')
    ,  ('Kermadec Islands',         'Kermadec Is.')
    ,  ('Kingdom of Eswatini',      'Swaziland')
    ,  ('Kure Island',              'Kure I.')
    ,  ('Lakshadweep Islands',      'Lakshadweep Is.')
    ,  ('Lord Howe Island',         'Lord Howe I.')
    ,  ('Macquarie Island',         'Macquarie I.')
    ,  ('Madeira Islands',          'Madeira Is.')
    ,  ('Malpelo Island',           'Malpelo I.')
    ,  ('Mariana Islands',          'Mariana Is.')
    ,  ('Marquesas Islands',        'Marquesas Is.')
    ,  ('Marshall Islands',         'Marshall Is.')
    ,  ('Midway Island',            'Midway I.')
    ,  ('N.Z. Subantarctic Is.',    'New Zealand Subantarctic Islands')
    ,  ('Navassa Island',           'Navassa I.')
    ,  ('Norfolk Island',           'Norfolk I.')
    ,  ('North Cook Islands',       'North Cook Is.')
    ,  ('North Macedonia',          'North Macedonia (Republic of)')
    ,  ('Palmyra & Jarvis Islands', 'Palmyra & Jarvis Is')
    ,  ('Peter 1 Island',           'Peter 1 I.')
    ,  ('Pitcairn Island',          'Pitcairn I.')
    ,  ('Pr. Edward & Marion Is.',  'Prince Edward & Marion Is.')
    ,  ('Pratas Island',            'Pratas I.')
    ,  ('Republic of South Sudan',  'South Sudan (Republic of)')
    ,  ('Reunion Island',           'Reunion I.')
    ,  ('Rodriguez Island',         'Rodrigues I.')
    ,  ('Rotuma Island',            'Rotuma I.')
    ,  ('Sable Island',             'Sable I.')
    ,  ('Solomon Islands',          'Solomon Is.')
    ,  ('South Cook Islands',       'South Cook Is.')
    ,  ('South Georgia Island',     'South Georgia I.')
    ,  ('South Orkney Islands',     'South Orkney Is.')
    ,  ('South Sandwich Islands',   'South Sandwich Is.')
    ,  ('South Shetland Islands',   'South Shetland Is.')
    ,  ('Sov Mil Order of Malta',   'Sovereign Military Order of Malta')
    ,  ('Spratly Islands',          'Spratly Is.')
    ,  ('St. Barthelemy',           'Saint Barthelemy')
    ,  ('St. Martin',               'Saint Martin')
    ,  ('St. Paul Island',          'St. Paul I.')
    ,  ('St. Peter & St. Paul',     'St. Peter & St. Paul Rocks')
    ,  ('Swains Island',            'Swains I.')
    ,  ('Timor - Leste',            'Timor-Leste')
    ,  ('Tokelau Islands',          'Tokelau Is.')
    ,  ('Trindade & Martim Vaz',    'Trindade & Martim Vaz Is.')
    ,  ('Tristan da Cunha & Gough', 'Tristan da Cunha & Gough I.')
    ,  ('Tromelin Island',          'Tromelin I.')
    ,  ('Turks & Caicos Islands',   'Turks & Caicos Is.')
    ,  ('UK Base Areas on Cyprus',  'UK Sovereign Base Areas on Cyprus')
    ,  ('US Virgin Islands',        'Virgin Is.')
    ,  ('United States',            'United States of America')
    ,  ('Vatican City',             'Vatican')
    ,  ('Vietnam',                  'Viet Nam')
    ,  ('Wake Island',              'Wake I.')
    ,  ('Wallis & Futuna Islands',  'Wallis & Futuna Is.')
    ,  ('Western Kiribati',         'W. Kiribati (Gilbert Is. )')
    ,  ('Willis Island',            'Willis I.')
    ))

# Map those to DXCC
darc_waedc_dxcc = dict \
    (( ('African Italy',            'Italy')    # *IG9 not in official list
    ,  ('Bear Island',              'Svalbard') # *JW/b
    ,  ('European Turkey',          'Turkey')   # *TA1
    ,  ('Shetland Islands',         'Scotland') # *GM/s
    ,  ('Sicily',                   'Italy')    # *IT
    ,  ('Vienna Intl Ctr',          'Austria')  # *4U1V
    ))

class CTY :
    """ Parse Country information in cty.dat format
        Docs: https://www.country-files.com/cty-dat-format/
    """

    data = os.path.join (os.path.dirname (__file__), 'data', 'cty.dat')

    # After prefix, additional info can be appended enclosed in the
    # following suffix markup. We ignore those currently.
    suffixes = '()', '[]', '<>', '{}', '~~'

    def __init__ (self, filename) :
        self.exact_callsign = {}
        self.prefix         = {}
        self.prf_max        = 0
        self.countries      = {}
        country = None
        with io.open (filename, 'r') as f :
            for line in f :
                line = line.strip ()
                if country is None :
                    assert line.endswith (':')
                    line = line.rstrip (':')
                    l = [x.lstrip () for x in line.split (':')]
                    country, cq, itu, ctycode, lat, lon, gmtoff, pfx = l
                    self.countries [country] = True
                    end = False
                else :
                    # Docs say 'should' contain comma at the end on continuation
                    if line.endswith (';') :
                        end = True
                    line = line.rstrip (',')
                    pfxs = line.split (',')
                    for pfx in pfxs :
                        # discard any additional info at end of prefix
                        for s in self.suffixes :
                            s = s [0]
                            pfx = pfx.split (s, 1) [0]
                        if pfx.startswith ('=') :
                            pfx = pfx.lstrip ('=')
                            if pfx not in self.exact_callsign :
                                self.exact_callsign [pfx] = country
                        else :
                            l = len (pfx)
                            if l > self.prf_max :
                                self.prf_max = l
                            if pfx not in self.prefix :
                                self.prefix [pfx] = country
                    if end :
                        country = None
                        end     = False
    # end def __init__

    def callsign_lookup (self, callsign) :
        for n in reversed (range (self.prf_max)) :
            pfx = callsign [:n+1]
            if pfx in self.prefix :
                return self.prefix [pfx]
    # end def callsign_lookup

# end class CTY

if __name__ == '__main__' :
    from afu.dxcc import DXCC_File
    dxcc = DXCC_File ()
    dxcc.parse ()
    dxcc = dxcc.by_type ['CURRENT']
    cty = CTY (CTY.data)
    csl = [ 'GM0XXX', 'GM0HZI', 'GM5BDX', 'GG7XXX', 'MM0CPZ', '2I0VIR'
          , '2E0INN', 'RK4PR', 'RK6BCP', 'R4AEK', '9A4ZM'
          ]
    if len (sys.argv) > 1 :
        csl = sys.argv [1:]
    for cs in csl :
        print ('%s:' % cs, cty.callsign_lookup (cs))
#    for c in sorted (cty.countries) :
#        if c not in dxcc.by_name :
#            print ('No dxcc country: %s' % c)
#    for c in sorted (dxcc.by_name) :
#        if c not in cty.countries :
##            print ('DXCC country not found: %s' % c)
