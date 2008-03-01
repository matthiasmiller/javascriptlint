#!/usr/bin/python
""" Parses a script into nodes. """
import bisect
import re
import unittest

import pyspidermonkey

class NodePos():
	def __init__(self, line, col):
		self.line = line
		self.col = col
	def __cmp__(self, other):
		if self.line < other.line:
			return -1
		if self.line > other.line:
			return 1
		if self.col < other.col:
			return -1
		if self.col > other.col:
			return 1
		return 0
	def __repr__(self):
		return '(line %i, col %i)' % (self.line+1, self.col+1)

class NodePositions():
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

class NodeRanges():
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

class _Node():
	def __init__(self, kwargs):
		def _to_node(kid):
			if kid:
				return _Node(kid)
		kwargs['type'] = kwargs['type'].lower()
		self.kind = kwargs['type']
		assert kwargs['opcode'].startswith('JSOP_')
		kwargs['opcode'] = kwargs['opcode'][5:].lower()
		self.opcode = kwargs['opcode']
		self.kids = tuple([_to_node(kid) for kid in kwargs['kids']])
		for kid in self.kids:
			if kid:
				kid.parent = self
		if 'atom' in kwargs:
			self.atom = kwargs['atom']
		if 'dval' in kwargs:
			self.dval = kwargs['dval']
		if 'fn_name' in kwargs:
			self.fn_name = kwargs['fn_name']
		if 'fn_args' in kwargs:
			self.fn_args = kwargs['fn_args']
		if 'end_comma' in kwargs:
			self.end_comma = kwargs['end_comma']
		self.args = kwargs
		self.node_index = kwargs['node_index']
		self.parent = None
		self.start_line = kwargs['start_row']
		self._start_pos = None
		self._end_pos = None

	def add_child(self, node):
		if node:
			node.node_index = len(self.kids)
			node.parent = self
		self.kids.append(node)
	
	def start_pos(self):
		self._start_pos = self._start_pos or \
						NodePos(self.args['start_row'], self.args['start_col'])
		return self._start_pos

	def end_pos(self):
		self._end_pos = self._end_pos or \
						NodePos(self.args['end_row'], self.args['end_col'])
		return self._end_pos

	def __repr__(self):
		kind = self.kind
		if not kind:
			kind = '(none)'
		return '%s>%s' % (kind, str(self.kids))

	def is_equivalent(self, other, are_functions_equiv=False):
		if not other:
			return False

		# Bail out for functions
		if not are_functions_equiv:
			if self.kind == 'function':
				return False
			if self.kind == 'lp' and self.opcode == 'call':
				return False

		if self.kind != other.kind:
			return False
		if self.opcode != other.opcode:
			return False

		# Check atoms on names, properties, and string constants
		if self.kind in ('name', 'dot', 'string') and self.atom != other.atom:
			return False

		# Check values on numbers
		if self.kind == 'number' and self.dval != other.dval:
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
				'start_row': start_pos.line,
				'start_col': start_pos.col,
				'end_row': end_pos.line,
				'end_col': end_pos.col,
				'kids': [],
				'node_index': None
			}
			comment_node = _Node(kwargs)
			comments.append(comment_node)
			pos = match.end()
		else:
			pos = match.start()+1

def parse(script, error_callback):
	def _wrapped_callback(line, col, msg):
		assert msg.startswith('JSMSG_')
		msg = msg[6:].lower()
		error_callback(line, col, msg)

	positions = NodePositions(script)

	roots = []
	nodes = []
	comment_ignore_ranges = NodeRanges()
	def process(node):
		if node.kind == 'number':
			node.atom = positions.text(node.start_pos(), node.end_pos())
		elif node.kind == 'string' or \
				(node.kind == 'object' and node.opcode == 'regexp'):
			start_offset = positions.to_offset(node.start_pos())
			end_offset = positions.to_offset(node.end_pos())
			comment_ignore_ranges.add(start_offset, end_offset)
		for kid in node.kids:
			if kid:
				process(kid)
	def pop():
		nodes.pop()

	roots = pyspidermonkey.traverse(script, _wrapped_callback)
	assert len(roots) == 1
	root_node = _Node(roots[0])
	process(root_node)

	comments = _parse_comments(script, root_node, positions, comment_ignore_ranges)
	return root_node, comments

def _dump_node(node, depth=0):
	print '.	'*depth,
	if node is None:
		print '(none)'
	else:
		print node.kind, '\t', node.args
		for node in node.kids:
			_dump_node(node, depth+1)

def dump_tree(script):
	def error_callback(line, col, msg):
		print '(%i, %i): %s', (line, col, msg)
	node, comments = parse(script, error_callback)
	_dump_node(node)

class TestComments(unittest.TestCase):
	def _test(self, script, expected_comments):
		root, comments = parse(script, lambda line, col, msg: None)
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
if __name__ == '__main__':
	unittest.main()

