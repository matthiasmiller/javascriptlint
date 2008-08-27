# vim: ts=4 sw=4 expandtab
import HTMLParser
import unittest

import jsparse

class _Parser(HTMLParser.HTMLParser):
    def __init__(self):
        HTMLParser.HTMLParser.__init__(self)
        self._node_positions = jsparse.NodePositions('')
        self._script = None
        self._scripts = []

    def handle_starttag(self, tag, attributes):
        if tag.lower() == 'script' and not self._script:
            offset = self._getoffset() + len(self.get_starttag_text())
            self._script = self._script or {
                'start': offset,
                'attributes': attributes
            }

    def handle_endtag(self, tag):
        if tag.lower() == 'script' and self._script:
            start = self._script['start']
            end = self._getoffset()
            script = self.rawdata[start:end]
            if jsparse.is_compilable_unit(script):
                attr = dict(self._script['attributes'])
                self._scripts.append({
                    'script': script,
                    'startoffset': start,
                    'endoffset': end,
                    'startpos': self._node_positions.from_offset(start),
                    'endpos': self._node_positions.from_offset(end),
                    'src': attr.get('src'),
                    'type': attr.get('type')
                })
                self._script = None

    def feed(self, data):
        self._node_positions = jsparse.NodePositions(self.rawdata + data)
        HTMLParser.HTMLParser.feed(self, data)

    def getscripts(self):
        return self._scripts

    def _getnodepos(self):
        line, col = self.getpos()
        return jsparse.NodePos(line - 1, col)

    def _getoffset(self):
        return self._node_positions.to_offset(self._getnodepos())

def findscripts(s):
    parser = _Parser()
    parser.feed(s)
    parser.close()
    return parser.getscripts()

class TestHTMLParse(unittest.TestCase):
    def testFindScript(self):
        html = """
<html><body>
<script src=test.js></script>
hi&amp;b
a<script><!--
var s = '<script></script>';
--></script>
ok&amp;
..</script>
ok&amp;
</body>
</html>
"""
        scripts = [x['script'] for x in findscripts(html)]
        self.assertEquals(scripts, [
            "",
            "<!--\nvar s = '<script></script>';\n-->"
        ])

