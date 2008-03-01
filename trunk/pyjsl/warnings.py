""" This module contains all the warnings. To add a new warning, define a
class. Its name should be in lowercase and words should be separated by
underscores. Its docstring should be the warning message.

The class can have one more more member functions to inspect nodes. The
function should be decorated with a @lookat call specifying the nodes it
wants to examine. The node names may be in the 'kind' or 'kind:opcode'
format. To report a warning, the function should return the node causing
the warning.

For example:

	class warning_name:
		'questionable JavaScript coding style'
		@lookat('nodekind', 'nodekind:opcode')
		def _lint(self, node):
			if questionable:
				return node
"""
import re
import sys
import types

from visitation import visit as lookat
# TODO: document inspect, node:opcode, etc

def _get_branch_in_for(node):
		" Returns None if this is not one of the branches in a 'for' "
		if node.parent and node.parent.kind == 'reserved' and \
			node.parent.parent.kind == 'for':
			return node.node_index
		return None

def _get_exit_points(node):
	if node.kind == 'lc':
		# Only if the last child contains it
		exit_points = set([None])
		for kid in node.kids:
			# "None" is only a valid exit point for the last statement.
			if None in exit_points:
				exit_points.remove(None)
			if kid:
				exit_points |= _get_exit_points(kid)
	elif node.kind == 'if':
		# Only if both branches have an exit point
		cond_, if_, else_ = node.kids
		exit_points = _get_exit_points(if_)
		if else_:
			exit_points |= _get_exit_points(else_)
	elif node.kind == 'switch':
		exit_points = set([None])

		switch_has_default = False
		switch_has_final_fallthru = True

		switch_var, switch_stmts = node.kids
		for node in switch_stmts.kids:
			case_val, case_stmt = node.kids
			case_exit_points = _get_exit_points(case_stmt)
			switch_has_default = switch_has_default or node.kind == 'default'
			switch_has_final_fallthru = None in case_exit_points
			exit_points |= case_exit_points

		# Correct the "None" exit point.
		exit_points.remove(None)

		# Check if the switch contained any break
		if 'break' in exit_points:
			exit_points.remove('break')
			exit_points.add(None)

		# Check if the switch had a default case
		if not switch_has_default:
			exit_points.add(None)

		# Check if the final case statement had a fallthru
		if switch_has_final_fallthru:
			exit_points.add(None)
	elif node.kind == 'break':
		exit_points = set(['break'])
	elif node.kind == 'with':
		exit_points = _get_exit_points(node.kids[-1])
	elif node.kind == 'return':
		exit_points = set(['return'])
	elif node.kind == 'throw':
		exit_points = set(['throw'])
	elif node.kind == 'try':
		try_, catch_, finally_ = node.kids

		exit_points = _get_exit_points(try_) | _get_exit_points(catch_)
		if finally_:
			# Always if the finally has an exit point
			if None in exit_points:
				exit_points.remove(None)
			exit_points |= _get_exit_points(finally_)
	else:
		exit_points = set([None])

	return exit_points

class comparison_type_conv:
	'comparisons against null, 0, true, false, or an empty string allowing implicit type conversion (use === or !==)'
	@lookat('eqop:eq')
	def _lint(self, node):
		lvalue, rvalue = node.kids
		if not self._allow_coercive_compare(lvalue) or \
			not self._allow_coercive_compare(rvalue):
			return node
	def _allow_coercive_compare(self, node):
		if node.kind == 'primary' and node.opcode in ('null', 'true', 'false'):
			return False
		if node.kind == 'number' and not node.dval:
			return False
		if node.kind == 'string' and not node.atom:
			return False
		return True

class default_not_at_end:
	'the default case is not at the end of the switch statement'
	@lookat('default')
	def _lint(self, node):
		siblings = node.parent.kids
		if node.node_index != len(siblings)-1:
			return siblings[node.node_index+1]

class duplicate_case_in_switch:
	'duplicate case in switch statement'
	@lookat('case')
	def _lint(self, node):
		# Only look at previous siblings
		siblings = node.parent.kids
		siblings = siblings[:node.node_index]
		# Compare values (first kid)
		node_value = node.kids[0]
		for sibling in siblings:
			if sibling.kind == 'case':
				sibling_value = sibling.kids[0]
				if node_value.is_equivalent(sibling_value, True):
					return node

class missing_default_case:
	'missing default case in switch statement'
	@lookat('switch')
	def _lint(self, node):
		value, cases = node.kids
		for case in cases.kids:
			if case.kind == 'default':
				return
		return node

class with_statement:
	'with statement hides undeclared variables; use temporary variable instead'
	@lookat('with')
	def _lint(self, node):
		return node

class useless_comparison:
	'useless comparison; comparing identical expressions'
	@lookat('eqop','relop')
	def _lint(self, node):
		lvalue, rvalue = node.kids
		if lvalue.is_equivalent(rvalue):
			return node

class use_of_label:
	'use of label'
	@lookat('colon:name')
	def _lint(self, node):
		return node

class meaningless_block:
	'meaningless block; curly braces have no impact'
	@lookat('lc')
	def _lint(self, node):
		if node.parent and node.parent.kind == 'lc':
			return node

class misplaced_regex:
	'regular expressions should be preceded by a left parenthesis, assignment, colon, or comma'
	@lookat('object:regexp')
	def _lint(self, node):
		if node.parent.kind == 'name' and node.parent.opcode == 'setname':
			return # Allow in var statements
		if node.parent.kind == 'assign' and node.parent.opcode == 'nop':
			return # Allow in assigns
		if node.parent.kind == 'colon' and node.parent.parent.kind == 'rc':
			return # Allow in object literals
		if node.parent.kind == 'lp' and node.parent.opcode == 'call':
			return # Allow in parameters
		if node.parent.kind == 'dot' and node.parent.opcode == 'getprop':
			return # Allow in /re/.property
		if node.parent.kind == 'return':
			return # Allow for return values
		return node

class assign_to_function_call:
	'assignment to a function call'
	@lookat('assign')
	def _lint(self, node):
		if node.kids[0].kind == 'lp':
			return node

class ambiguous_else_stmt:
	'the else statement could be matched with one of multiple if statements (use curly braces to indicate intent'
	@lookat('if')
	def _lint(self, node):
		# Only examine this node if it has an else statement.
		condition, if_, else_ = node.kids
		if not else_:
			return

		tmp = node
		while tmp:
			# Curly braces always clarify if statements.
			if tmp.kind == 'lc':
				return
			# Else is only ambiguous in the first branch of an if statement.
			if tmp.parent.kind == 'if' and tmp.node_index == 1:
				return else_
			tmp = tmp.parent

class block_without_braces:
	'block statement without curly braces'
	@lookat('if', 'while', 'do', 'for', 'with')
	def _lint(self, node):
		if node.kids[1].kind != 'lc':
			return node.kids[1]

class ambiguous_nested_stmt:
	'block statements containing block statements should use curly braces to resolve ambiguity'
	_block_nodes = ('if', 'while', 'do', 'for', 'with')
	@lookat(*_block_nodes)
	def _lint(self, node):
		# Ignore "else if"
		if node.kind == 'if' and node.node_index == 2 and node.parent.kind == 'if':
			return

		# If the parent is a block, it means a block statement
		# was inside a block statement without clarifying curlies.
		# (Otherwise, the node type would be 'lc'.)
		if node.parent.kind in self._block_nodes:
			return node

class inc_dec_within_stmt:
	'increment (++) and decrement (--) operators used as part of greater statement'
	@lookat('inc', 'dec')
	def _lint(self, node):
		if node.parent.kind == 'semi':
			return None

		# Allow within the third part of the "for"
		tmp = node
		while tmp and tmp.parent and tmp.parent.kind == 'comma':
			tmp = tmp.parent
		if tmp and tmp.node_index == 2 and \
			tmp.parent.kind == 'reserved' and \
			tmp.parent.parent.kind == 'for':
			return None

		return node
	def _is_for_ternary_stmt(self, node, branch=None):
		if node.parent and node.parent.kind == 'comma':
			return _is_for_ternary_stmt(node.parent, branch)
		return node.node_index == branch and \
			node.parent and \
			node.parent.kind == 'reserved' and \
			node.parent.parent.kind == 'for'

class comma_separated_stmts:
	'multiple statements separated by commas (use semicolons?)'
	@lookat('comma')
	def _lint(self, node):
		# Allow within the first and third part of "for(;;)"
		if _get_branch_in_for(node) in (0, 2):
			return
		# This is an array
		if node.parent.kind == 'rb':
			return
		return node

class empty_statement:
	'empty statement or extra semicolon'
	@lookat('semi')
	def _semi(self, node):
		if not node.kids[0]:
			return node
	@lookat('lc')
	def _lc(self, node):
		if node.kids:
			return
		# Ignore the outermost block.
		if not node.parent:
			return
		# Some empty blocks are meaningful.
		if node.parent.kind in ('catch', 'case', 'default', 'switch', 'function'):
			return
		return node

class missing_break:
	'missing break statement'
	@lookat('case', 'default')
	def _lint(self, node):
		# The last item is handled separately
		if node.node_index == len(node.parent.kids)-1:
			return
		case_contents = node.kids[1]
		assert case_contents.kind == 'lc'
		# Ignore empty case statements
		if not case_contents.kids:
			return
		if None in _get_exit_points(case_contents):
			return node

class missing_break_for_last_case:
	'missing break statement for last case in switch'
	@lookat('case', 'default')
	def _lint(self, node):
		if node.node_index < len(node.parent.kids)-1:
			return
		case_contents = node.kids[1]
		assert case_contents.kind == 'lc'
		if None in _get_exit_points(case_contents):
			return node

class multiple_plus_minus:
	'unknown order of operations for successive plus (e.g. x+++y) or minus (e.g. x---y) signs'
	@lookat('inc')
	def _inc(self, node):
		if node.node_index == 0 and node.parent.kind == 'plus':
			return node
	@lookat('dec')
	def _dec(self, node):
		if node.node_index == 0 and node.parent.kind == 'minus':
			return node

class useless_assign:
	'useless assignment'
	@lookat('name:setname')
	def _lint(self, node):
		if node.parent.kind == 'assign':
			assert node.node_index == 0
			value = node.parent.kids[1]
		elif node.parent.kind == 'var':
			value = node.kids[0]
		if value and value.kind == 'name' and node.atom == value.atom:
			return node

class unreachable_code:
	'unreachable code'
	@lookat('break', 'continue', 'return', 'throw')
	def _lint(self, node):
		if node.parent.kind == 'lc' and \
			node.node_index != len(node.parent.kids)-1:
			return node.parent.kids[node.node_index+1]

class meaningless_block:
	'meaningless block; curly braces have no impact'
	#TODO: @lookat('if')
	def _lint(self, node):
		condition, if_, else_ = node.kids
		if condition.kind == 'primary' and condition.opcode in ('true', 'false', 'null'):
			return condition
	#TODO: @lookat('while')
	def _lint(self, node):
		condition = node.kids[0]
		if condition.kind == 'primary' and condition.opcode in ('false', 'null'):
			return condition
	@lookat('lc')
	def _lint(self, node):
		if node.parent and node.parent.kind == 'lc':
			return node

class useless_void:
	'use of the void type may be unnecessary (void is always undefined)'
	@lookat('unaryop:void')
	def _lint(self, node):
		return node

class parseint_missing_radix:
	'parseInt missing radix parameter'
	@lookat('lp:call')
	def _lint(self, node):
		if node.kids[0].kind == 'name' and node.kids[0].atom == 'parseInt' and len(node.kids) <= 2:
			return node

class leading_decimal_point:
	'leading decimal point may indicate a number or an object member'
	@lookat('number')
	def _lint(self, node):
		if node.atom.startswith('.'):
			return node

class trailing_decimal_point:
	'trailing decimal point may indicate a number or an object member'
	@lookat('number')
	def _lint(self, node):
		if node.parent.kind == 'dot':
			return node
		if node.atom.endswith('.'):
			return node

class octal_number:
	'leading zeros make an octal number'
	_regexp = re.compile('^0[0-9]')
	@lookat('number')
	def _line(self, node):
		if self._regexp.match(node.atom):
			return node

class trailing_comma_in_array:
	'extra comma is not recommended in array initializers'
	@lookat('rb')
	def _line(self, node):
		if node.end_comma:
			return node

class mismatch_ctrl_comments:
	'mismatched control comment; "ignore" and "end" control comments must have a one-to-one correspondence'
	pass

class redeclared_var:
	'redeclaration of {0} {1}'
	pass

class undeclared_identifier:
	'undeclared identifier: {0}'
	pass

class jsl_cc_not_understood:
	'couldn\'t understand control comment using /*jsl:keyword*/ syntax'
	pass

class nested_comment:
	'nested comment'
	pass

class legacy_cc_not_understood:
	'couldn\'t understand control comment using /*@keyword@*/ syntax'
	pass

class var_hides_arg:
	'variable {0} hides argument'
	pass

class duplicate_formal:
	'TODO'
	pass

class missing_semicolon:
	'missing semicolon'
	pass

class ambiguous_newline:
	'unexpected end of line; it is ambiguous whether these lines are part of the same statement'
	pass

class missing_option_explicit:
	'the "option explicit" control comment is missing'
	pass

class partial_option_explicit:
	'the "option explicit" control comment, if used, must be in the first script tag'
	pass

class dup_option_explicit:
	'duplicate "option explicit" control comment'
	pass

klasses = tuple([
	obj for
	obj in
	sys.modules[__name__].__dict__.values() if
	type(obj) == types.ClassType
])

