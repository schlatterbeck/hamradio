#!/usr/bin/python

from rsclib.autosuper import autosuper

class ADIF_Syntax_Error (RuntimeError)  : pass
class ADIF_EOF          (StandardError) : pass

class ADIF_Parse (autosuper) :
    def __init__ (self, fd, lineno = 1) :
        self.__super.__init__ ()
        self.fd     = fd
        self.lineno = lineno
        self.dict   = {}
    # end def __init__

    def get_tag (self) :
        count  = 0
        tag    = []
        value  = []
        state  = 'start'

        c = self.fd.read (1)
        while (c) :
            if state == 'start' :
                if c.isspace () :
                    if c == '\n' :
                        self.lineno += 1
                elif c == '<' :
                    state = 'tag'
                else :
                    raise ADIF_Syntax_Error, \
                        '%s: Expected tag start' % self.lineno
            elif state == 'tag' :
                if c == '>' or c == ':' :
                    if len (tag) == 0 :
                        raise ADIF_Syntax_Error, '%s: Empty tag' % self.lineno
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
                    try :
                        count = int (''.join (value))
                    except ValueError :
                        raise ADIF_Syntax_Error, '%s: Invalid count: %s' \
                            % (self.lineno, ''.join (value))
                    value = []
                    state = 'value'
                else :
                    value.append (c)
            elif state == 'value' :
                value.append (c)
                count -= 1
                if count == 0 :
                    value = ''.join (value)
                    yield (tag, value)
                    tag   = []
                    value = []
                    state = 'start'
            else :
                assert (0)
            c = self.fd.read (1)
    # end def get_tag
# end class ADIF_Parse

class ADIF_Record (ADIF_Parse) :
    def __init__ (self, fd, lineno) :
        """ consume one record from fd """
        self.__super.__init__ (fd, lineno)
        self.fd = fd
        for k, v in self.get_tag () :
            print k, v
            if k == 'EOR' :
                if v :
                    raise ADIF_Syntax_Error, "%s: Invalid EOR" % self.lineno
            self.dict [k] = v
        if not self.dict :
            raise ADIF_EOF
    # end def __init__
# end class ADIF_Record

class ADIF (ADIF_Parse) :
    def __init__ (self, fd) :
        self.__super.__init__ (fd)
        self.records = []
        l = fd.readline ()
        f, fn = l.split (': ')
        if f != 'File' :
            raise ADIF_Syntax_Error, "File header not found", self.lineno
        self.filename = fn.rstrip ('\r\n')
        self.lineno += 1
        for k, v in self.get_tag () :
            print k, v
            if k == 'EOH' :
                if v :
                    raise ADIF_Syntax_Error, "%s: Invalid EOR" % self.lineno
            self.dict [k] = v
        while (1) :
            try :
                self.records.append (ADIF_Record (fd, self.lineno))
            except ADIF_EOF :
                break
    # end def __init__

    def as_cabrillo (self) :
        pass
    # end def as_cabrillo
# end class ADIF

if __name__ == '__main__' :
    import sys
    adif = ADIF (sys.stdin)
