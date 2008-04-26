# vim: ts=4 sw=4 expandtab
""" This module contains all the warnings. To add a new warning, define a
class. Its name should be in lowercase and words should be separated by
underscores. Its docstring should be the warning message.

The class can have one more more member functions to inspect nodes. The
function should be decorated with a @onpush call specifying the nodes it
wants to examine. The node names may be in the tok.KIND or (tok.KIND, op.OPCODE)
format. To report a warning, the function should return the node causing
the warning.

For example:

    class warning_name:
        'questionable JavaScript coding style'
        @onpush(tok.NODEKIND, (tok.NODEKIND, op.OPCODE))
        def _lint(self, node):
            if questionable:
                return node
"""
import re
import sys
import types

import visitation
from pyspidermonkey import tok, op

# TODO: document inspect, node:opcode, etc

def onpush(*args):
    return visitation.visit('push', *args)

class LintWarning(Exception):
    def __init__(self, node):
        self.node = node

def _get_branch_in_for(node):
        " Returns None if this is not one of the branches in a 'for' "
        if node.parent and node.parent.kind == tok.RESERVED and \
            node.parent.parent.kind == tok.FOR:
            return node.node_index
        return None

def _get_exit_points(node):
    if node.kind == tok.LC:
        # Only if the last child contains it
        exit_points = set([None])
        for kid in node.kids:
            # "None" is only a valid exit point for the last statement.
            if None in exit_points:
                exit_points.remove(None)
            if kid:
                exit_points |= _get_exit_points(kid)
    elif node.kind == tok.IF:
        # Only if both branches have an exit point
        cond_, if_, else_ = node.kids
        exit_points = _get_exit_points(if_)
        if else_:
            exit_points |= _get_exit_points(else_)
    elif node.kind == tok.SWITCH:
        exit_points = set([None])

        switch_has_default = False
        switch_has_final_fallthru = True

        switch_var, switch_stmts = node.kids
        for node in switch_stmts.kids:
            case_val, case_stmt = node.kids
            case_exit_points = _get_exit_points(case_stmt)
            switch_has_default = switch_has_default or node.kind == tok.DEFAULT
            switch_has_final_fallthru = None in case_exit_points
            exit_points |= case_exit_points

        # Correct the "None" exit point.
        exit_points.remove(None)

        # Check if the switch contained any break
        if tok.BREAK in exit_points:
            exit_points.remove(tok.BREAK)
            exit_points.add(None)

        # Check if the switch had a default case
        if not switch_has_default:
            exit_points.add(None)

        # Check if the final case statement had a fallthru
        if switch_has_final_fallthru:
            exit_points.add(None)
    elif node.kind == tok.BREAK:
        exit_points = set([tok.BREAK])
    elif node.kind == tok.WITH:
        exit_points = _get_exit_points(node.kids[-1])
    elif node.kind == tok.RETURN:
        exit_points = set([tok.RETURN])
    elif node.kind == tok.THROW:
        exit_points = set([tok.THROW])
    elif node.kind == tok.TRY:
        try_, catch_, finally_ = node.kids

        assert catch_.kind == tok.RESERVED
        catch_, = catch_.kids
        assert catch_.kind == tok.LEXICALSCOPE
        catch_, = catch_.kids
        assert catch_.kind == tok.CATCH
        ignored, ignored, catch_ = catch_.kids
        assert catch_.kind == tok.LC

        exit_points = _get_exit_points(try_) | _get_exit_points(catch_)
        if finally_:
            finally_exit_points = _get_exit_points(finally_)
            if None in finally_exit_points:
                # The finally statement does not add a missing exit point.
                finally_exit_points.remove(None)
            else:
                # If the finally statement always returns, the other
                # exit points are irrelevant.
                if None in exit_points:
                    exit_points.remove(None)

            exit_points |= finally_exit_points

    else:
        exit_points = set([None])

    return exit_points

class comparison_type_conv:
    'comparisons against null, 0, true, false, or an empty string allowing implicit type conversion (use === or !==)'
    @onpush((tok.EQOP, op.EQ))
    def comparison_type_conv(self, node):
        for kid in node.kids:
            if kid.kind == tok.PRIMARY and kid.opcode in (op.NULL, op.TRUE, op.FALSE):
                continue
            if kid.kind == tok.NUMBER and not kid.dval:
                continue
            if kid.kind == tok.STRING and not kid.atom:
                continue
            raise LintWarning, kid

class default_not_at_end:
    'the default case is not at the end of the switch statement'
    @onpush(tok.DEFAULT)
    def default_not_at_end(self, node):
        siblings = node.parent.kids
        if node.node_index != len(siblings)-1:
            raise LintWarning, siblings[node.node_index+1]

class duplicate_case_in_switch:
    'duplicate case in switch statement'
    @onpush(tok.CASE)
    def duplicate_case_in_switch(self, node):
        # Only look at previous siblings
        siblings = node.parent.kids
        siblings = siblings[:node.node_index]
        # Compare values (first kid)
        node_value = node.kids[0]
        for sibling in siblings:
            if sibling.kind == tok.CASE:
                sibling_value = sibling.kids[0]
                if node_value.is_equivalent(sibling_value, True):
                    raise LintWarning, node

class missing_default_case:
    'missing default case in switch statement'
    @onpush(tok.SWITCH)
    def missing_default_case(self, node):
        value, cases = node.kids
        for case in cases.kids:
            if case.kind == tok.DEFAULT:
                return
        raise LintWarning, node

class with_statement:
    'with statement hides undeclared variables; use temporary variable instead'
    @onpush(tok.WITH)
    def with_statement(self, node):
        raise LintWarning, node

class useless_comparison:
    'useless comparison; comparing identical expressions'
    @onpush(tok.EQOP,tok.RELOP)
    def useless_comparison(self, node):
        lvalue, rvalue = node.kids
        if lvalue.is_equivalent(rvalue):
            raise LintWarning, node

class use_of_label:
    'use of label'
    @onpush((tok.COLON, op.NAME))
    def use_of_label(self, node):
        raise LintWarning, node

class meaningless_block:
    'meaningless block; curly braces have no impact'
    @onpush(tok.LC)
    def meaningless_block(self, node):
        if node.parent and node.parent.kind == tok.LC:
            raise LintWarning, node

class misplaced_regex:
    'regular expressions should be preceded by a left parenthesis, assignment, colon, or comma'
    @onpush((tok.OBJECT, op.REGEXP))
    def misplaced_regex(self, node):
        if node.parent.kind == tok.NAME and node.parent.opcode == op.SETNAME:
            return # Allow in var statements
        if node.parent.kind == tok.ASSIGN and node.parent.opcode == op.NOP:
            return # Allow in assigns
        if node.parent.kind == tok.COLON and node.parent.parent.kind == tok.RC:
            return # Allow in object literals
        if node.parent.kind == tok.LP and node.parent.opcode == op.CALL:
            return # Allow in parameters
        if node.parent.kind == tok.DOT and node.parent.opcode == op.GETPROP:
            return # Allow in /re/.property
        if node.parent.kind == tok.RETURN:
            return # Allow for return values
        raise LintWarning, node

class assign_to_function_call:
    'assignment to a function call'
    @onpush(tok.ASSIGN)
    def assign_to_function_call(self, node):
        if node.kids[0].kind == tok.LP:
            raise LintWarning, node

class ambiguous_else_stmt:
    'the else statement could be matched with one of multiple if statements (use curly braces to indicate intent'
    @onpush(tok.IF)
    def ambiguous_else_stmt(self, node):
        # Only examine this node if it has an else statement.
        condition, if_, else_ = node.kids
        if not else_:
            return

        tmp = node
        while tmp:
            # Curly braces always clarify if statements.
            if tmp.kind == tok.LC:
                return
            # Else is only ambiguous in the first branch of an if statement.
            if tmp.parent.kind == tok.IF and tmp.node_index == 1:
                raise LintWarning, else_
            tmp = tmp.parent

class block_without_braces:
    'block statement without curly braces'
    @onpush(tok.IF, tok.WHILE, tok.DO, tok.FOR, tok.WITH)
    def block_without_braces(self, node):
        if node.kids[1].kind != tok.LC:
            raise LintWarning, node.kids[1]

class ambiguous_nested_stmt:
    'block statements containing block statements should use curly braces to resolve ambiguity'
    _block_nodes = (tok.IF, tok.WHILE, tok.DO, tok.FOR, tok.WITH)
    @onpush(*_block_nodes)
    def ambiguous_nested_stmt(self, node):
        # Ignore "else if"
        if node.kind == tok.IF and node.node_index == 2 and node.parent.kind == tok.IF:
            return

        # If the parent is a block, it means a block statement
        # was inside a block statement without clarifying curlies.
        # (Otherwise, the node type would be tok.LC.)
        if node.parent.kind in self._block_nodes:
            raise LintWarning, node

class inc_dec_within_stmt:
    'increment (++) and decrement (--) operators used as part of greater statement'
    @onpush(tok.INC, tok.DEC)
    def inc_dec_within_stmt(self, node):
        if node.parent.kind == tok.SEMI:
            return

        # Allow within the third part of the "for"
        tmp = node
        while tmp and tmp.parent and tmp.parent.kind == tok.COMMA:
            tmp = tmp.parent
        if tmp and tmp.node_index == 2 and \
            tmp.parent.kind == tok.RESERVED and \
            tmp.parent.parent.kind == tok.FOR:
            return

        raise LintWarning, node
    def _is_for_ternary_stmt(self, node, branch=None):
        if node.parent and node.parent.kind == tok.COMMA:
            return _is_for_ternary_stmt(node.parent, branch)
        return node.node_index == branch and \
            node.parent and \
            node.parent.kind == tok.RESERVED and \
            node.parent.parent.kind == tok.FOR

class comma_separated_stmts:
    'multiple statements separated by commas (use semicolons?)'
    @onpush(tok.COMMA)
    def comma_separated_stmts(self, node):
        # Allow within the first and third part of "for(;;)"
        if _get_branch_in_for(node) in (0, 2):
            return
        # This is an array
        if node.parent.kind == tok.RB:
            return
        raise LintWarning, node

class empty_statement:
    'empty statement or extra semicolon'
    @onpush(tok.SEMI)
    def empty_statement(self, node):
        if not node.kids[0]:
            raise LintWarning, node
    @onpush(tok.LC)
    def empty_statement_(self, node):
        if node.kids:
            return
        # Ignore the outermost block.
        if not node.parent:
            return
        # Some empty blocks are meaningful.
        if node.parent.kind in (tok.CATCH, tok.CASE, tok.DEFAULT, tok.SWITCH, tok.FUNCTION):
            return
        raise LintWarning, node

class missing_break:
    'missing break statement'
    @onpush(tok.CASE, tok.DEFAULT)
    def missing_break(self, node):
        # The last item is handled separately
        if node.node_index == len(node.parent.kids)-1:
            return
        case_contents = node.kids[1]
        assert case_contents.kind == tok.LC
        # Ignore empty case statements
        if not case_contents.kids:
            return
        if None in _get_exit_points(case_contents):
            # Show the warning on the *next* node.
            raise LintWarning, node.parent.kids[node.node_index+1]

class missing_break_for_last_case:
    'missing break statement for last case in switch'
    @onpush(tok.CASE, tok.DEFAULT)
    def missing_break_for_last_case(self, node):
        if node.node_index < len(node.parent.kids)-1:
            return
        case_contents = node.kids[1]
        assert case_contents.kind == tok.LC
        if None in _get_exit_points(case_contents):
            raise LintWarning, node

class multiple_plus_minus:
    'unknown order of operations for successive plus (e.g. x+++y) or minus (e.g. x---y) signs'
    @onpush(tok.INC)
    def multiple_plus_minus(self, node):
        if node.node_index == 0 and node.parent.kind == tok.PLUS:
            raise LintWarning, node
    @onpush(tok.DEC)
    def multiple_plus_minus_(self, node):
        if node.node_index == 0 and node.parent.kind == tok.MINUS:
            raise LintWarning, node

class useless_assign:
    'useless assignment'
    @onpush((tok.NAME, op.SETNAME))
    def useless_assign(self, node):
        if node.parent.kind == tok.ASSIGN:
            assert node.node_index == 0
            value = node.parent.kids[1]
        elif node.parent.kind == tok.VAR:
            value = node.kids[0]
        if value and value.kind == tok.NAME and node.atom == value.atom:
            raise LintWarning, node

class unreachable_code:
    'unreachable code'
    @onpush(tok.BREAK, tok.CONTINUE, tok.RETURN, tok.THROW)
    def unreachable_code(self, node):
        if node.parent.kind == tok.LC and \
            node.node_index != len(node.parent.kids)-1:
            raise LintWarning, node.parent.kids[node.node_index+1]

class meaningless_block:
    'meaningless block; curly braces have no impact'
    #TODO: @onpush(tok.IF)
    def meaningless_block(self, node):
        condition, if_, else_ = node.kids
        if condition.kind == tok.PRIMARY and condition.opcode in (op.TRUE, op.FALSE, op.NULL):
            raise LintWarning, condition
    #TODO: @onpush(tok.WHILE)
    def meaningless_blocK_(self, node):
        condition = node.kids[0]
        if condition.kind == tok.PRIMARY and condition.opcode in (op.FALSE, op.NULL):
            raise LintWarning, condition
    @onpush(tok.LC)
    def meaningless_block__(self, node):
        if node.parent and node.parent.kind == tok.LC:
            raise LintWarning, node

class useless_void:
    'use of the void type may be unnecessary (void is always undefined)'
    @onpush((tok.UNARYOP, op.VOID))
    def useless_void(self, node):
        raise LintWarning, node

class parseint_missing_radix:
    'parseInt missing radix parameter'
    @onpush((tok.LP, op.CALL))
    def parseint_missing_radix(self, node):
        if node.kids[0].kind == tok.NAME and node.kids[0].atom == 'parseInt' and len(node.kids) <= 2:
            raise LintWarning, node

class leading_decimal_point:
    'leading decimal point may indicate a number or an object member'
    @onpush(tok.NUMBER)
    def leading_decimal_point(self, node):
        if node.atom.startswith('.'):
            raise LintWarning, node

class trailing_decimal_point:
    'trailing decimal point may indicate a number or an object member'
    @onpush(tok.NUMBER)
    def trailing_decimal_point(self, node):
        if node.parent.kind == tok.DOT:
            raise LintWarning, node
        if node.atom.endswith('.'):
            raise LintWarning, node

class octal_number:
    'leading zeros make an octal number'
    _regexp = re.compile('^0[0-9]')
    @onpush(tok.NUMBER)
    def octal_number(self, node):
        if self._regexp.match(node.atom):
            raise LintWarning, node

class trailing_comma_in_array:
    'extra comma is not recommended in array initializers'
    @onpush(tok.RB)
    def trailing_comma_in_array(self, node):
        if node.end_comma:
            raise LintWarning, node

class useless_quotes:
    'the quotation marks are unnecessary'
    @onpush(tok.STRING)
    def useless_quotes(self, node):
        if node.node_index == 0 and node.parent.kind == tok.COLON:
            raise LintWarning, node

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

