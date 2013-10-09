# vim: sw=4 ts=4 et
from jsengine import JSSyntaxError
import tok

_WHITESPACE = u'\u0020\t\u000B\u000C\u00A0\uFFFF'
_LINETERMINATOR = u'\u000A\u000D\u2028\u2029'
_DIGITS = u'0123456789'
_DOT_DIGITS = [u'.%s' % digit for digit in _DIGITS]
_HEX_DIGITS = _DIGITS + u'abcdefABCDEF'
_IDENT = u'abcdefghijklmnopqrstuvwxyz' + \
         u'ABCDEFGHIJKLMNOPQRSTUVWXYZ' + \
         u'$_'

_KEYWORDS = tok.getkeywords()
_PUNCTUATOR_TREE = tok.get_punctuator_tree()

class Token:
    def __init__(self, tok, atom=None):
        self.tok = tok
        self.atom = atom
        self.start_offset = None
        self.end_offset = None
    def set_offset(self, start_offset, end_offset):
        self.start_offset = start_offset
        self.end_offset = end_offset
    def __repr__(self):
        return 'Token(%r, %r)' % \
            (self.tok, self.atom)

class TokenStream:
    def __init__(self, content, start_offset=0):
        assert isinstance(start_offset, int)
        self._content = content
        self._start_offset = start_offset
        self._offset = 0
        self._watched_offset = None

    def get_offset(self):
        return self._start_offset + self._offset

    def watch_reads(self):
        self._watched_offset = self._offset

    def get_watched_reads(self):
        assert not self._watched_offset == None
        s = self._content[self._watched_offset:self._offset]
        self._watched_offset = None
        return s

    def eof(self):
        return self._offset >= len(self._content)

    def readchr(self):
        if self._offset < len(self._content):
            self._offset += 1
            return self._content[self._offset - 1]
        raise JSSyntaxError(self.get_offset()-1, 'unexpected_eof')

    def readchrif(self, seq):
        s = self.peekchrif(seq)
        if s:
            assert len(s) == 1
            self._offset += 1
        return s

    def peekchrif(self, seq):
        if self._offset < len(self._content) and \
                self._content[self._offset] in seq:
            return self._content[self._offset]

    def readtextif(self, text):
        """ Returns the string if found. Otherwise returns None.
        """
        len_ = len(text)
        if self._offset + len_ <= len(self._content):
            peeked = self._content[self._offset:self._offset+len_]
            if peeked == text:
                self._offset += len_
                return text

class Tokenizer:
    def __init__(self, stream):
        self._stream = stream
        self._peeked = []
        self._error = False

    def peek(self):
        self._readahead()
        return self._peeked[-1]

    def peek_sameline(self):
        self._readahead()
        for peek in self._peeked:
            if peek.tok == tok.EOL:
                return peek
        else:
            return peek

    def advance(self):
        assert not self._error

        self._readahead()
        peek = self._peeked[-1]
        self._peeked = []
        if peek.tok == tok.ERROR:
            self._error = True
            raise JSSyntaxError(peek.start_offset, peek.atom or 'syntax_error')
        return peek

    def next_withregexp(self):
        assert not self._error
        self._readahead()
        if self._peeked[-1].tok == tok.DIV:
            token = self._parse_rest_of_regexp()
            token.set_offset(self._peeked[-1].start_offset, self._stream.get_offset()-1)
            self._peeked = []
            if token.tok == tok.ERROR:
                self._error = True
                raise JSSyntaxError(peek.start_offset, peek.atom or 'syntax_error')
            return token
        else:
            return self.advance()

    def expect(self, tok):
        encountered = self.advance()
        if encountered.tok != tok:
            raise JSSyntaxError(encountered.start_offset, 'expected_tok',
                                { 'token': tok })
        return encountered

    def expect_identifiername(self):
        encountered = self.advance()
        if encountered.tok in list(_KEYWORDS.values()):
            encountered.tok = tok.NAME
        if encountered.tok != tok.NAME:
            raise JSSyntaxError(encountered.start_offset, 'syntax_error')
        return encountered

    def _readahead(self):
        """ Always ensure that a valid token is at the end of the queue.
        """
        if self._peeked:
            assert self._peeked[-1].tok not in (tok.EOL, tok.SPACE,
                                                tok.C_COMMENT, tok.CPP_COMMENT,
                                                tok.HTML_COMMENT)
            return
        while True:
            start_offset = self._stream.get_offset()
            peek = self._next()
            end_offset = self._stream.get_offset()-1
            if peek.tok == tok.ERROR:
                peek.set_offset(end_offset, end_offset)
            else:
                peek.set_offset(start_offset, end_offset)

            self._peeked.append(peek)
            assert isinstance(peek.tok, tok.TokenType), repr(peek.tok)
            if peek.tok not in (tok.EOL, tok.SPACE,
                                tok.C_COMMENT, tok.CPP_COMMENT,
                                tok.HTML_COMMENT):
                return

    def _parse_rest_of_regexp(self):
        stream = self._stream
        while True:
            c = stream.readchr()
            if c == '\\':
                c = stream.readchr()
                if c == '\n':
                    return Token(tok.ERROR)
            elif c == '[':
                while True:
                    c = stream.readchr()
                    if c == '\n':
                        return Token(tok.ERROR)
                    elif c == ']':
                        break
            elif c == '\n':
                return Token(tok.ERROR)
            elif c == '/':
                break

        # TODO: Validate and save
        while True:
            c = stream.readchrif(_IDENT)
            if not c:
                break

        return Token(tok.REGEXP)

    def _next(self, parse_regexp=False):
        stream = self._stream

        if stream.eof():
            return Token(tok.EOF)

        c = stream.readchr()

        # WHITESPACE
        if c in _WHITESPACE or c in _LINETERMINATOR:
            linebreak = c in _LINETERMINATOR
            while True:
                if stream.readchrif(_LINETERMINATOR):
                    linebreak = True
                elif stream.readchrif(_WHITESPACE):
                    pass
                else:
                    break
            if linebreak:
                return Token(tok.EOL)
            else:
                return Token(tok.SPACE)

        # COMMENTS
        if c == '/':
            if stream.peekchrif("/"):
                while not stream.eof() and not stream.peekchrif(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.CPP_COMMENT)
            if stream.peekchrif("*"):
                linebreak = False
                while True:
                    if stream.eof():
                        return Token(tok.ERROR, atom='unterminated_comment')
                    c = stream.readchr()
                    if c in _LINETERMINATOR:
                        linebreak = True
                    elif c == '*' and stream.readchrif('/'):
                        return Token(tok.C_COMMENT)
                return Token(tok.EOF)
        elif c == '<':
            if stream.readtextif('!--'):
                while not stream.eof() and not stream.peekchrif(_LINETERMINATOR):
                    stream.readchr()
                return Token(tok.HTML_COMMENT)

        # STRING LITERALS
        if c == '"' or c == "'":
            # TODO: Decode
            s = ''
            quote = c
            while True:
                c = stream.readchr()
                if c == '\\':
                    c = stream.readchr()
                elif c == quote:
                    return Token(tok.STRING, atom=s)
                s += c

        # NUMBERS
        if c in _DIGITS or (c == '.' and stream.peekchrif(_DIGITS)):
            s = c # TODO
            stream.watch_reads()
            if c == '0' and stream.readchrif('xX'):
                # Hex
                while stream.readchrif(_HEX_DIGITS):
                    pass
            elif c == '0' and stream.readchrif(_DIGITS):
                # Octal
                while stream.readchrif(_DIGITS):
                    pass
            else:
                # Decimal
                if c != '.':
                    while stream.readchrif(_DIGITS):
                        pass
                    stream.readchrif('.')

                while stream.readchrif(_DIGITS):
                    pass

                if stream.readchrif('eE'):
                    stream.readchrif('+-')
                    if not stream.readchrif(_DIGITS):
                        raise JSSyntaxError(stream.get_offset(), 'syntax_error')
                    while stream.readchrif(_DIGITS):
                        pass

                if stream.peekchrif(_IDENT):
                    return Token(tok.ERROR)

            atom = s + stream.get_watched_reads()
            return Token(tok.NUMBER, atom=atom)

        if c in _PUNCTUATOR_TREE:
            d = _PUNCTUATOR_TREE[c]
            while True:
                c = stream.readchrif(list(d.keys()))
                if c:
                    d = d[c]
                else:
                    break
            try:
                return Token(d[None])
            except KeyError:
                print('oops')
                raise JSSyntaxError(stream.get_offset(), 'syntax_error')

        if c in _IDENT:
            s = ''
            while c:
                s += c
                c = stream.readchrif(_IDENT + _DIGITS)
            if s in _KEYWORDS:
                return Token(_KEYWORDS[s], atom=s)
            elif s:
                return Token(tok.NAME, atom=s)

        raise JSSyntaxError(stream.get_offset(), 'unexpected_char',
                            { 'char': c })