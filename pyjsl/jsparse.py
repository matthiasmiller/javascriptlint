#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
""" Parses a script into nodes. """
import bisect
import re
import unittest

import pyspidermonkey
from pyspidermonkey import tok, op

_tok_names = dict(zip(
    [getattr(tok, prop) for prop in dir(tok)],
    ['tok.%s' % prop for prop in dir(tok)]
))

NodePos = pyspidermonkey.NodePos

class NodePositions:
    " Given a string, allows [x] lookups for NodePos line and column numbers."
    def __init__(self, text):
        # Find the length of each line and incrementally sum all of the lengths
        # to determine the ending position of each line.
        self._lines = text.splitlines(True)
        lines = [0] + [len(x) for x in self._lines]
        for x in range(1, len(lines)):
            lines[x] += lines[x-1]
        self._line_offsets = lines
    def from_offset(self, offset):
        line = bisect.bisect(self._line_offsets, offset)-1
        col = offset - self._line_offsets[line]
        return NodePos(line, col)
    def to_offset(self, pos):
        offset = self._line_offsets[pos.line] + pos.col
        assert offset <= self._line_offsets[pos.line+1] # out-of-bounds col num
        return offset
    def text(self, start, end):
        assert start <= end
        # Trim the ending first in case it's a single line.
        lines = self._lines[start.line:end.line+1]
        lines[-1] = lines[-1][:end.col+1]
        lines[0] = lines[0][start.col:]
        return ''.join(lines)

class NodeRanges:
    def __init__(self):
        self._offsets = []
    def add(self, start, end):
        i = bisect.bisect_left(self._offsets, start)
        if i % 2 == 1:
            i -= 1
            start = self._offsets[i]

        end = end + 1
        j = bisect.bisect_left(self._offsets, end)
        if j % 2 == 1:
            end = self._offsets[j]
            j += 1

        self._offsets[i:j] = [start,end]
    def has(self, pos):
        return bisect.bisect_right(self._offsets, pos) % 2 == 1

class _Node:
    def add_child(self, node):
        if node:
            node.node_index = len(self.kids)
            node.parent = self
        self.kids.append(node)
    
    def start_pos(self):
        try:
            return self._start_pos
        except AttributeError:
            self._start_pos = NodePos(self._start_line, self._start_col)
            return self._start_pos

    def end_pos(self):
        try:
            return self._end_pos
        except AttributeError:
            self._end_pos = NodePos(self._end_line, self._end_col)
            return self._end_pos

    def __str__(self):
        kind = self.kind
        if not kind:
            kind = '(none)'
        return '%s>%s' % (_tok_names[kind], str(self.kids))

    def is_equivalent(self, other, are_functions_equiv=False):
        if not other:
            return False

        # Bail out for functions
        if not are_functions_equiv:
            if self.kind == tok.FUNCTION:
                return False
            if self.kind == tok.LP and self.opcode == op.CALL:
                return False

        if self.kind != other.kind:
            return False
        if self.opcode != other.opcode:
            return False

        # Check atoms on names, properties, and string constants
        if self.kind in (tok.NAME, tok.DOT, tok.STRING) and self.atom != other.atom:
            return False

        # Check values on numbers
        if self.kind == tok.NUMBER and self.dval != other.dval:
            return False

        # Compare child nodes
        if len(self.kids) != len(other.kids):
            return False
        for i in range(0, len(self.kids)):
            # Watch for dead nodes
            if not self.kids[i]:
                if not other.kids[i]: return True
                else: return False
            if not self.kids[i].is_equivalent(other.kids[i]):
                return False

        return True

def _parse_comments(script, root, node_positions, ignore_ranges):
    pos = 0
    single_line_re = r"//[^\r\n]*"
    multi_line_re = r"/\*(.*?)\*/"
    full_re = "(%s)|(%s)" % (single_line_re, multi_line_re)
    comment_re = re.compile(full_re, re.DOTALL)

    comments = []
    while True:
        match = comment_re.search(script, pos)
        if not match:
            return comments

        # Get the comment text
        comment_text = script[match.start():match.end()]
        if comment_text.startswith('/*'):
            comment_text = comment_text[2:-2]
            opcode = 'JSOP_C_COMMENT'
        else:
            comment_text = comment_text[2:]
            opcode = 'JSOP_CPP_COMMENT'
        opcode = opcode[5:].lower()

        start_offset = match.start()+1
        end_offset = match.end()

        # Make sure it doesn't start in a string or regexp
        if not ignore_ranges.has(start_offset):
            start_pos = node_positions.from_offset(start_offset)
            end_pos = node_positions.from_offset(end_offset)
            kwargs = {
                'type': 'COMMENT',
                'atom': comment_text,
                'opcode': opcode,
                '_start_line': start_pos.line,
                '_start_col': start_pos.col,
                '_end_line': end_pos.line,
                '_end_col': end_pos.col,
                'parent': None,
                'kids': [],
                'node_index': None
            }
            comment_node = _Node()
            comment_node.__dict__.update(kwargs)
            comments.append(comment_node)
            pos = match.end()
        else:
            pos = match.start()+1

def parse(script, error_callback):
    def _wrapped_callback(line, col, msg):
        assert msg.startswith('JSMSG_')
        msg = msg[6:].lower()
        error_callback(line, col, msg)

    return pyspidermonkey.parse(script, _Node, _wrapped_callback)

def parsecomments(script, root_node):
    positions = NodePositions(script)
    comment_ignore_ranges = NodeRanges()

    def process(node):
        if node.kind == tok.NUMBER:
            node.atom = positions.text(node.start_pos(), node.end_pos())
        elif node.kind == tok.STRING or \
                (node.kind == tok.OBJECT and node.opcode == op.REGEXP):
            start_offset = positions.to_offset(node.start_pos())
            end_offset = positions.to_offset(node.end_pos())
            comment_ignore_ranges.add(start_offset, end_offset)
        for kid in node.kids:
            if kid:
                process(kid)
    process(root_node)

    return _parse_comments(script, root_node, positions, comment_ignore_ranges)

def is_compilable_unit(script):
    return pyspidermonkey.is_compilable_unit(script)

def _dump_node(node, depth=0):
    print '.    '*depth,
    if node is None:
        print '(none)'
    else:
        print '%s\t%s, %s' % (_tok_names[node.kind], node.start_pos(), node.end_pos())
        for node in node.kids:
            _dump_node(node, depth+1)

def dump_tree(script):
    def error_callback(line, col, msg):
        print '(%i, %i): %s', (line, col, msg)
    node = parse(script, error_callback)
    _dump_node(node)

class TestComments(unittest.TestCase):
    def _test(self, script, expected_comments):
        root = parse(script, lambda line, col, msg: None)
        comments = parsecomments(script, root)
        encountered_comments = [node.atom for node in comments]
        self.assertEquals(encountered_comments, list(expected_comments))
    def testSimpleComments(self):
        self._test('re = /\//g', ())
        self._test('re = /\///g', ())
        self._test('re = /\////g', ('g',))
    def testCComments(self):
        self._test('/*a*//*b*/', ('a', 'b'))
        self._test('/*a\r\na*//*b\r\nb*/', ('a\r\na', 'b\r\nb'))
        self._test('a//*b*/c', ('*b*/c',))
        self._test('a///*b*/c', ('/*b*/c',))
        self._test('a/*//*/;', ('//',))
        self._test('a/*b*/+/*c*/d', ('b', 'c'))

class TestNodePositions(unittest.TestCase):
    def _test(self, text, expected_lines, expected_cols):
        # Get a NodePos list
        positions = NodePositions(text)
        positions = [positions.from_offset(i) for i in range(0, len(text))]
        encountered_lines = ''.join([str(x.line) for x in positions])
        encountered_cols = ''.join([str(x.col) for x in positions])
        self.assertEquals(encountered_lines, expected_lines.replace(' ', ''))
        self.assertEquals(encountered_cols, expected_cols.replace(' ', ''))
    def testSimple(self):
        self._test(
            'abc\r\ndef\nghi\n\nj',
            '0000 0 1111 2222 3 4',
            '0123 4 0123 0123 0 0'
        )
        self._test(
            '\rabc',
            '0 111',
            '0 012'
        )
    def testText(self):
        pos = NodePositions('abc\r\ndef\n\nghi')
        self.assertEquals(pos.text(NodePos(0, 0), NodePos(0, 0)), 'a')
        self.assertEquals(pos.text(NodePos(0, 0), NodePos(0, 2)), 'abc')
        self.assertEquals(pos.text(NodePos(0, 2), NodePos(1, 2)), 'c\r\ndef')
    def testOffset(self):
        pos = NodePositions('abc\r\ndef\n\nghi')
        self.assertEquals(pos.to_offset(NodePos(0, 2)), 2)
        self.assertEquals(pos.to_offset(NodePos(1, 0)), 5)
        self.assertEquals(pos.to_offset(NodePos(3, 1)), 11)

class TestNodeRanges(unittest.TestCase):
    def testAdd(self):
        r = NodeRanges()
        r.add(5, 10)
        self.assertEquals(r._offsets, [5,11])
        r.add(15, 20)
        self.assertEquals(r._offsets, [5,11,15,21])
        r.add(21,22)
        self.assertEquals(r._offsets, [5,11,15,23])
        r.add(4,5)
        self.assertEquals(r._offsets, [4,11,15,23])
        r.add(9,11)
        self.assertEquals(r._offsets, [4,12,15,23])
        r.add(10,20)
        self.assertEquals(r._offsets, [4,23])
        r.add(4,22)
        self.assertEquals(r._offsets, [4,23])
        r.add(30,30)
        self.assertEquals(r._offsets, [4,23,30,31])
    def testHas(self):
        r = NodeRanges()
        r.add(5, 10)
        r.add(15, 15)
        assert not r.has(4)
        assert r.has(5)
        assert r.has(6)
        assert r.has(9)
        assert r.has(10)
        assert not r.has(14)
        assert r.has(15)
        assert not r.has(16)

class TestCompilableUnit(unittest.TestCase):
    def test(self):
        tests = (
            ('var s = "', False),
            ('bogon()', True),
            ('int syntax_error;', True),
            ('a /* b', False),
            ('re = /.*', False),
            ('{ // missing curly', False)
        )
        for text, result in tests:
            self.assertEquals(is_compilable_unit(text), result)

if __name__ == '__main__':
    unittest.main()

