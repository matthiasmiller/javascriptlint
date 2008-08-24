# vim: ts=4 sw=4 expandtab
import codecs
import os.path
import re
import unittest

_identifier = re.compile('^[A-Za-z_$][A-Za-z0-9_$]*$')

def isidentifier(text):
    return _identifier.match(text)

def readfile(path):
    file = codecs.open(path, 'r', 'utf-8')
    contents = file.read()
    if contents[0] == unicode(codecs.BOM_UTF8, 'utf8'):
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

if __name__ == '__main__':
    unittest.main()

