# vim: ts=4 sw=4 expandtab
import codecs
import os.path
import re
import unittest

_identifier = re.compile('^[A-Za-z_$][A-Za-z0-9_$]*$')

def isidentifier(text):
    return _identifier.match(text)

def _encode_error_keyword(s):
    s = s.replace('\\', '\\\\')
    s = s.replace('"', '\\"')
    s = s.replace("'", "\\'")
    s = s.replace("\t", "\\t")
    s = s.replace("\r", "\\r")
    s = s.replace("\n", "\\n")
    return s

def format_error(output_format, path, line, col, errname, errdesc):
    errprefix = 'warning' #TODO
    replacements = {
        '__FILE__': path,
        '__FILENAME__': os.path.basename(path),
        '__LINE__': str(line+1),
        '__COL__': str(col),
        '__ERROR__': '%s: %s' % (errprefix, errdesc),
        '__ERROR_NAME__': errname,
        '__ERROR_PREFIX__': errprefix,
        '__ERROR_MSG__': errdesc,
        '__ERROR_MSGENC__': errdesc,
    }

    formatted_error = output_format

    # If the output format starts with encode:, all of the keywords should be
    # encoded.
    if formatted_error.startswith('encode:'):
        formatted_error = formatted_error[len('encode:'):]
        encoded_keywords = replacements.keys()
    else:
        encoded_keywords = ['__ERROR_MSGENC__']

    for keyword in encoded_keywords:
        replacements[keyword] = _encode_error_keyword(replacements[keyword])

    regexp = '|'.join(replacements.keys())
    return re.sub(regexp, lambda match: replacements[match.group(0)],
                  formatted_error)

def readfile(path):
    file = codecs.open(path, 'r', 'utf-8')
    contents = file.read()
    if contents and contents[0] == unicode(codecs.BOM_UTF8, 'utf8'):
        contents = contents[1:]
    return contents

def normpath(path):
    path = os.path.abspath(path)
    path = os.path.normcase(path)
    path = os.path.normpath(path)
    return path

class TestUtil(unittest.TestCase):
    def testIdentifier(self):
        assert not isidentifier('')
        assert not isidentifier('0a')
        assert not isidentifier('a b')
        assert isidentifier('a')
        assert isidentifier('$0')

    def testEncodeKeyword(self):
        self.assertEquals(_encode_error_keyword(r'normal text'), 'normal text')
        self.assertEquals(_encode_error_keyword(r'a\b'), r'a\\b')
        self.assertEquals(_encode_error_keyword(r"identifier's"), r"identifier\'s")
        self.assertEquals(_encode_error_keyword(r'"i"'), r'\"i\"')
        self.assertEquals(_encode_error_keyword('a\tb'), r'a\tb')
        self.assertEquals(_encode_error_keyword('a\rb'), r'a\rb')
        self.assertEquals(_encode_error_keyword('a\nb'), r'a\nb')

    def testFormattedError(self):
        self.assertEquals(format_error('__FILE__', '__LINE__', 1, 2, 'name', 'desc'),
                          '__LINE__')
        self.assertEquals(format_error('__FILE__', r'c:\my\file', 1, 2, 'name', 'desc'),
                          r'c:\my\file')
        self.assertEquals(format_error('encode:__FILE__', r'c:\my\file', 1, 2, 'name', 'desc'),
                          r'c:\\my\\file')
        self.assertEquals(format_error('__ERROR_MSGENC__', r'c:\my\file', 1, 2, 'name', r'a\b'),
                          r'a\\b')
        self.assertEquals(format_error('encode:__ERROR_MSGENC__', r'c:\my\file', 1, 2, 'name', r'a\b'),
                          r'a\\b')

        
if __name__ == '__main__':
    unittest.main()

