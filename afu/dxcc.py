#!/usr/bin/python3
# Copyright (C) 2019-21 Dr. Ralf Schlatterbeck Open Source Consulting.
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

import io
import os
import requests
from re                 import compile as rc
from argparse           import ArgumentParser
from rsclib.autosuper   import autosuper
from rsclib.stateparser import Parser

def prefix_sequence (seq) :
    """ Generate a sequence of prefixes from certain input ranges
    >>> prefix_sequence ('7T-7Y')
    ['7T', '7U', '7V', '7W', '7X', '7Y']
    >>> prefix_sequence ('9Q-9T')
    ['9Q', '9R', '9S', '9T']
    >>> prefix_sequence ('H6-7')
    ['H6', 'H7']
    >>> prefix_sequence ('EA6-EH6')
    ['EA6', 'EB6', 'EC6', 'ED6', 'EE6', 'EF6', 'EG6', 'EH6']
    >>> prefix_sequence ('PP0-PU0F')
    ['PP0F', 'PQ0F', 'PR0F', 'PS0F', 'PT0F', 'PU0F']
    >>> prefix_sequence ('UA8-0')
    ['UA8', 'UA9', 'UA0']
    >>> prefix_sequence ('UA-UB8-0')
    ['UA8', 'UA9', 'UA0', 'UB8', 'UB9', 'UB0']
    """
    newp = []
    x = seq.split ('-', 1)
    sfx = ''
    if len (x [0]) < len (x [1]) :
        assert len (x [1]) > len (x [0])
        sfx = x [1][len (x [0]):]
        x [1] = x [1][:-len (sfx)]
    elif len (x [0]) > len (x [1]) :
        x [1] = x [0][:-len (x [1])] + x [1]
    if x [0][-1] == x [1][-1] :
        assert x [0][:-2] == x [1][:-2]
        pfx = x [0][:-2]
        sfx = x [0][-1] + sfx
        frm = x [0][-2]
        to  = x [1][-2]
    else :
        assert x [0][:-1] == x [1][:-1]
        pfx = x [0][:-1]
        frm = x [0][-1]
        to  = x [1][-1]
    seq = range (ord (frm), ord (to) + 1)
    if ord (to) < ord (frm) :
        assert to == '0'
        seq = list (range (ord (frm), ord ('9') + 1))
        seq.append (ord ('0'))
    for i in seq :
        r = pfx + chr (i) + sfx
        if '-' in r :
            r = prefix_sequence (r)
            newp.extend (r)
        else :
            newp.append (r)
    return newp
# end def prefix_sequence


class DXCC_Entry (autosuper) :

    def __init__ (self, code, name, continent, ituz, cqz, *prefix) :
        self.code      = code
        self.name      = name
        self.continent = continent
        self.ituz      = ituz
        self.cqz       = cqz
        self.prefixes  = list (prefix)
        self.note      = ''
        self.org       = None
        self.__super.__init__ ()
    # end def __init__

    def add_note (self, note) :
        if self.note :
            self.note += '\n' + note
        else :
            self.note = note
    # end def add_note

    def __str__ (self) :
        r = []
        r.append (self.code)
        r.append ('%-35s' % self.name)
        r.append (self.continent)
        r.append ("ITU: %s" % self.ituz)
        r.append ("CQ: %s" % self.cqz)
        r.append (','.join (self.prefixes))
        if self.org :
            r.append ('Org: %s' % self.org)
        if self.note :
            r.append ('\n  Notes:')
            for n in self.note.split ('\n') :
                r.append ('\n    %s' % n)
        return ' '.join (r)
    # end def __str__
    __repr__ = __str__

# end class DXCC_Entry

class DXCC_Parser (Parser) :
    encoding   = None
    re_entity  = rc (r'^(CURRENT|DELETED) ENTITIES')
    re_date    = rc (r'^([A-Z][a-z]+)\s+([0-9]{4})\s+Edition')
    re_total   = rc (r'^([A-Za-z]+)\s+Entities Total:\s+([0-9]+)\s+')
    re_list    = rc \
        (r'^\s+(\S+)\s+(.+)\s+([AEONS][ACEFONSU,]+)\s+'
         r'([-()0-9,A-Z]+)\s+([-()0-9,A-Z]+)\s+([0-9]{3})'
        )
    re_list_h1 = rc (r'^ZONE\s+Entity')
    re_list_h2 = rc (r'^Prefix\s+Entity\s+Continent\s+ITU\s+CQ\s+Code')
    re_list_h3 = rc (r'^(\s*_){5}')
    re_s_node  = rc (r'\s+NOTES:')
    re_note    = rc (r'^\s+([0-9]+)\s+(.*)$')
    re_spec    = rc (r'^\s+([\^])\s+(.*)$')
    re_end     = rc (r'\s+Zone Notes can be found')

    # State     Pattern           new State Action
    matrix = \
    [ ["init",  'ARRL DXCC LIST', 'dxcc', None]
    , ["dxcc",  re_entity,        'dxcc', "set_entity_type"]
    , ["dxcc",  re_date,          'dxcc', "set_entity_date"]
    , ["dxcc",  re_total,         'dxcc', "set_entity_total"]
    , ["dxcc",  None,             'head', None]
    , ["head",  re_list_h1,       'head', None]
    , ["head",  re_list_h2,       'head', None]
    , ["head",  re_list_h3,       'list', None]
    , ["head",  None,             'head', "set_head_text"]
    , ["list",  re_list,          'list', "add_list_entry"]
    , ["list",  "",               'list', None]
    , ["list",  re_s_node,        'note', None]
    , ["note",  re_note,          'note', "add_note"]
    , ["note",  "",               'note', None]
    , ["note",  re_spec,          'note', "add_note"]
    , ["note",  re_end,           'note', "fix_notes"]
    , ["note",  None,             'note', "append_note"]
    ]

    def __init__ (self, *args, **kw) :
        self.head_text = []
        self.crossref  = {}
        self.entries   = []
        self.by_name   = {}
        self.by_code   = {}
        self.prefix    = {}
        self.notes     = {}
        self.lastnote  = None
        self.prf_max   = 0
        self.__super.__init__ (*args, **kw)
    # end def __init__

    def callsign_lookup (self, callsign) :
        for n in reversed (range (self.prf_max)) :
            pfx = callsign [:n+1]
            if pfx in self.prefix :
                return self.prefix [pfx]
    # end def callsign_lookup

    # Parsing methods below this line

    def add_list_entry (self, state, new_state, match) :
        g = match.groups ()
        c = None
        o = None
        p = g [0]
        p = p.rstrip ('#').rstrip ('*').rstrip ('#').rstrip ('*')
        cross = []
        if '(' in p :
            p, cross = p.split ('(', 1)
            assert cross.endswith (')')
            cross = cross [:-1]
            if ',' in cross :
                cross = cross.split ('),(')
            else :
                cross = [cross]
            p = p.rstrip ('#').rstrip ('*').rstrip ('#').rstrip ('*')
        if '_' in p :
            p, o = p.split ('_', 1)
        e = DXCC_Entry (g [5], g [1].rstrip (), g [2], g [3], g [4])
        # Same crossref can be used for several entities
        for c in cross :
            if c not in self.crossref :
                self.crossref [c] = []
            self.crossref [c].append (e)
        # special note for Antarctica
        if p.endswith ('^') :
            assert '^' not in self.crossref
            self.crossref ['^'] = [e]
            p = p[:-1]
        if o :
            e.org = o
        if ',' not in p :
            p = [p]
        elif ',' in p :
            p = p.split (',')
            # e.g., "3B6,7"
            if len (p) == 2 and len (p [1]) == 1 and p [1].isdigit () :
                if p [0][-1].isdigit () :
                    p [1] = p [0][:-1] + p [1]
        newp = []
        for x in p :
            if '-' in x :
                newp.extend (prefix_sequence (x))
            else :
                newp.append (x)
        p = newp
        e.prefixes = p
        self.entries.append (e)
        self.by_name [e.name] = e
        self.by_code [e.code] = e
        for prf in e.prefixes :
            if prf not in self.prefix :
                self.prefix [prf] = []
            self.prefix [prf].append (e)
            if len (prf) > self.prf_max :
                self.prf_max = len (prf)
    # end def add_list_entry

    def add_note (self, state, new_state, match) :
        g = match.groups ()
        self.notes [g [0]] = g [1].rstrip ()
        self.lastnote = g [0]
    # end def add_note

    def append_note (self, state, new_state, match) :
        self.notes [self.lastnote] += '\n' + self.line.strip ()
    # end def append_note

    def fix_notes (self, state, new_state, match) :
        for n in self.notes :
            for e in self.crossref [n] :
                e.add_note (self.notes [n])
    # end def fix_notes

    def set_entity_date (self, state, new_state, match) :
        g = match.groups ()
        self.entity_month = g [0]
        self.entity_year  = g [1]
    # end def set_entity_date

    def set_entity_total (self, state, new_state, match) :
        g = match.groups ()
        self.entity_total = int (g [1])
        assert self.entity_type.lower () == g [0].lower ()
    # end def set_entity_total

    def set_entity_type (self, state, new_state, match) :
        self.entity_type = match.groups () [0]
    # end def set_entity_type

    def set_head_text (self, state, new_state, match) :
        self.head_text.append (self.line)
    # end def set_head_text

# end class DXCC_Parser

class DXCC_File (autosuper) :
    base = '2019_Current_Deleted(3).txt'
    url  = 'http://www.arrl.org/files/file/DXCC/' + base
    file = os.path.join (os.path.dirname (__file__), 'data', base)

    def __init__ (self, url = None, file = file) :
        self.url       = url
        self.file      = file
        self.dxcc_list = []
        self.by_type   = {}
        if self.url is not None :
            self.session = requests.session ()
    # end def __init__

    def parse (self) :
        h = 'ARRL DXCC LIST'
        if self.url is not None :
            r = self.session.get (self.url)
            if not (200 <= r.status_code <= 299) :
                raise RuntimeError \
                    ( 'Invalid get result: %s: %s\n    %s'
                    % (r.status_code, r.reason, r.text)
                    )
            t = r.text
        else :
            with io.open (self.file, 'r') as f :
                t = f.read ()
        t = t.split (h)
        assert len (t) > 1
        self.dxcc_list = []
        self.by_type   = {}
        for k in t :
            if not k.strip () :
                continue
            with io.StringIO (h + k) as f :
                self.dxcc_list.append (DXCC_Parser ())
                self.dxcc_list [-1].parse (f)
        for l in self.dxcc_list :
            t = l.entity_type
            assert t not in self.by_type
            self.by_type [t] = l
    # end def parse

# end class DXCC_File

def main () :
    cmd = ArgumentParser ()
    cmd.add_argument \
        ( "callsign"
        , help    = "Callsign to look up"
        , nargs   = '*'
        )
    cmd.add_argument \
        ( "-f", "--file"
        , help    = "File of DXCC List, default=%(default)s"
        , default = DXCC_File.file
        )
    cmd.add_argument \
        ( "-u", "--url"
        , help    = "URL of DXCC List, default=%(default)s"
        , default = None
        )
    args = cmd.parse_args ()
    df   = DXCC_File (url = args.url, file = file)
    df.parse ()
    #for l in df.dxcc_list :
    #    #print l.entity_type
    #    if l.entity_type == 'CURRENT' :
    #        for e in l.entries :
    #            print (e)
    current = df.by_type ['CURRENT']
    for cs in args.callsign :
        entities = current.callsign_lookup (cs)
        if not entities :
            print ("%s: NOT FOUND" % cs)
        else :
            for e in entities :
                print ("%s: %s" % (cs, e.name))
# end def main

if __name__ == '__main__' :
    main ()
