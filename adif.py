#!/usr/bin/python

from __future__ import print_function

import io
from datetime         import datetime
from rsclib.autosuper import autosuper
from gzip             import GzipFile


class ADIF_Syntax_Error (RuntimeError)  : pass
class ADIF_EOF          (Exception) : pass

class ADIF_Parse (autosuper) :
    def __init__ (self, fd, lineno = 1) :
        self.__super.__init__ ()
        self.fd     = fd
        self.lineno = lineno
        self.dict   = {}
        self.header = None
    # end def __init__

    def get_header (self, endtag = 'eoh', firstchar = None) :
        endtag = endtag + '>'
        head   = []
        state  = 'text'
        tagctr = 0
        if firstchar is not None :
            c = firstchar
        else :
            c = self.fd.read (1)
        while (c) :
            if state == 'text' :
                if c == '<' :
                    state = 'tag'
                else :
                    head.append (c)
            elif state == 'tag' :
                if c.lower () == endtag [tagctr] :
                    tagctr += 1
                    if tagctr >= len (endtag) :
                        self.header = ''.join (head)
                        return
                else :
                    head.append ('<')
                    head.append (endtag [:tagctr])
                    tagctr = 0
                    state = 'text'
            else :
                assert 0
            c = self.fd.read (1)
    # end def get_header

    def get_tags (self, endtag, firstchar = None) :
        for k, v in self.get_tag (firstchar = firstchar) :
            firstchar = None
            if k.lower () == endtag :
                if v :
                    raise ADIF_Syntax_Error \
                        ("%s: Invalid %s" % (self.lineno, endtag))
                return
            else :
                self.dict [k.lower ()] = v
    # end def get_tags

    def get_tag (self, firstchar = None) :
        count  = 0
        tag    = []
        value  = []
        state  = 'start'

        if firstchar is not None :
            c = firstchar
        else :
            c = self.fd.read (1)
        while (c) :
            if state == 'start' or state == 'skip' :
                # Be tolerant and allow white space where we expect a tag
                if c.isspace () :
                    if c == '\n' :
                        self.lineno += 1
                elif c == '<' :
                    state = 'tag'
                elif state != 'skip' :
                    raise ADIF_Syntax_Error \
                        ('%s: Expected tag start, got %s' % (self.lineno, c))
            elif state == 'tag' :
                if c == '>' or c == ':' :
                    if len (tag) == 0 :
                        raise ADIF_Syntax_Error ('%s: Empty tag' % self.lineno)
                    tag   = ''.join (tag)
                    state = 'length'
                    if c == '>' :
                        yield ''.join (tag), ''
                        tag   = []
                        value = []
                        state = 'start'
                else :
                    tag.append (c)
            elif state == 'length' :
                if c == '>' :
                    v = ''.join (value)
                    try :
                        count = int (v)
                    except ValueError :
                        c1, c2 = v.split (':', 1)
                        # TQ8 has some weirdness for SIGN_LOTW_V1.0 tag
                        try :
                            count = int (c1)
                            c2    = int (c2)
                        except ValueError :
                            raise ADIF_Syntax_Error \
                                ( '%s: Invalid count: %s'
                                % (self.lineno, ''.join (value))
                                )
                    value = []
                    state = 'value'
                else :
                    value.append (c)
            elif state == 'value' :
                if count :
                    value.append (c)
                    count -= 1
                if count == 0 :
                    value = ''.join (value)
                    yield (tag, value)
                    tag   = []
                    value = []
                    state = 'skip'
            else :
                assert (0)
            c = self.fd.read (1)
    # end def get_tag

    def __getitem__ (self, name) :
        n = name.lower ()
        return self.dict [n]
    # end def __getitem__

    def __contains__ (self, name) :
        n = name.lower ()
        return n in self.dict
    # end def __contains__
    has_key = __contains__
# end class ADIF_Parse

class ADIF_Record (ADIF_Parse) :
    """ Represents a QSO record in ADIF format
        Common fields: BAND, CALL, FREQ, MODE, QSO_DATE, RST_RCVD,
        RST_SENT, TIME_OFF, TIME_ON, GRIDSQUARE
        all converted to lowercase.
    """

    cabrillo_fields  = \
        [ 'frqint:5'
        , 'mode:2'
        , 'isodate:10'
        , 'time_off:4'
        , 'own_call:13'
        , 'rst_sent:3'
        , 'call:13'
        , 'rst_rcvd:3'
        , 'gridsquare:4'
        ]

    def __init__ (self, adif, fd, lineno, end_tag = 'eor', firstchar = None) :
        """ consume one record from fd """
        self.__super.__init__ (fd, lineno)
        self.end_tag  = end_tag
        self.adif     = adif
        self.fd       = fd
        self.get_tags (self.end_tag, firstchar = firstchar)
        if not self.dict :
            raise ADIF_EOF
    # end def __init__

    def as_cabrillo (self, fields = None) :
        x = fields or self.cabrillo_fields
        fields = []
        for f in x :
            a, b = f.split (':')
            fields.append ((a, int (b)))
        r = ['QSO:']
        for f, l in fields :
            fmt = '%-' + str (l) + '.' + str (l) + 's'
            r.append (fmt % self [f])
        return ' '.join (r)
    # end def as_cabrillo

    def __getitem__ (self, name) :
        n = name.lower ()
        if n == 'frqint' :
            return str (int (float (self.dict ['freq']) * 1000 + 0.5))
        elif n == 'mode' and self.adif.modemap :
            return self.adif.modemap.get \
                ( self.dict ['mode']
                , self.adif.modemap.get ('default', self.dict ['mode'])
                )
        elif n == 'isodate' :
            dt = datetime.strptime (self.dict ['qso_date'], '%Y%m%d')
            return dt.strftime ('%Y-%m-%d')
        try :
            if n == 'time_off' and n not in self :
                return self.__super.__getitem__ ('time_on')
            return self.__super.__getitem__ (n)
        except KeyError :
            return self.adif [n]
    # end def __getitem__

    def __contains__ (self, name) :
        n = name.lower ()
        if n in ('frqint', 'isodate') :
            return True
        if n == 'mode' and self.adif.modemap :
            return True
        return self.__super.has_key (n) or self.adif.has_key (n)
    # end def __contains__
    has_key = __contains__
# end class ADIF_Record

class ADIF (ADIF_Parse) :

    modemap = {}

    def __init__ (self, fd, lineno = 1, callsign = None, ** kw) :
        self.__super.__init__ (fd, lineno)
        self.callsign = callsign
        self.dict.update (kw)
        if callsign :
            self.dict ['own_call'] = callsign
        self.records  = []
        c1 = fd.read (1)
        if c1 != '<' :
            self.get_header (firstchar = c1)
            c1 = None
        while (1) :
            try :
                self.records.append \
                    (ADIF_Record (self, fd, self.lineno, firstchar = c1))
                c1 = None
            except ADIF_EOF :
                break
    # end def __init__

    def as_cabrillo (self, fields = None, cabrillo = (), **kw) :
        s = []
        for k in cabrillo :
            s.append ('%s: %s' % (k.upper (), cabrillo [k]))
        for k in kw :
            s.append ('%s: %s' % (k.upper (), kw [k]))
        for r in self.records :
            s.append (r.as_cabrillo (fields))
        s.append ('END_OF_LOG:')
        return '\n'.join (s)
    # end def as_cabrillo

    def set_modemap (self, modemap) :
        """ Set a map for mapping modes in self ['mode'] to something
            else. May specify 'default' as a key for a default mapping
            if nothing is found.
        """
        self.modemap = modemap
    # end def set_modemap

# end class ADIF

class TQ8 (ADIF_Parse) :
    def __init__ (self, fd, lineno = 1, ** kw) :
        fd = GzipFile (mode = 'r', fileobj = fd)
        self.__super.__init__ (fd, lineno)
        self.get_tags ('eor')
        assert (self.dict ['Rec_Type'] == 'tCERT')
        self.get_tags ('eor')
        assert (self.dict ['Rec_Type'] == 'tSTATION')
        self.callsign = self.dict ['call']
        self.records  = []
        while (1) :
            try :
                self.records.append \
                    (ADIF_Record (self, fd, self.lineno, end_tag = 'eor'))
            except ADIF_EOF :
                break
    # end def __init__
# end class TQ8

if __name__ == '__main__' :
    import sys
    f = sys.stdin
    if len (sys.argv) > 1 :
        f = io.open (sys.argv [1], 'r', encoding = 'utf-8')
    adif = ADIF (f, callsign = 'OE3RSU')
    d = {'START-OF-LOG' : '2.0'}
    print (adif.header)
    print (adif.as_cabrillo (cabrillo = d))
