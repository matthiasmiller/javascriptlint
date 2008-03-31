""" This module contains all the warnings. To add a new warning, define a
class. Its name should be in lowercase and words should be separated by
underscores. Its docstring should be the warning message.

The class can have one more more member functions to inspect nodes. The
function should be decorated with a @lookat call specifying the nodes it
wants to examine. The node names may be in the tok.KIND or (tok.KIND, op.OPCODE)
format. To report a warning, the function should return the node causing
the warning.

For example:

    class warning_name:
        'questionable JavaScript coding style'
        @lookat(tok.NODEKIND, (tok.NODEKIND, op.OPCODE))
        def _lint(self, node):
            if questionable:
                return node
"""
import re
import sys
import types

from visitation import visit as lookat
from pyspidermonkey import tok, op

# TODO: document inspect, node:opcode, etc

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
    @lookat((tok.EQOP, op.EQ))
    def _lint(self, node):
        lvalue, rvalue = node.kids
        if not self._allow_coercive_compare(lvalue) or \
            not self._allow_coercive_compare(rvalue):
            return node
    def _allow_coercive_compare(self, node):
        if node.kind == tok.PRIMARY and node.opcode in (op.NULL, op.TRUE, op.FALSE):
            return False
        if node.kind == tok.NUMBER and not node.dval:
            return False
        if node.kind == tok.STRING and not node.atom:
            return False
        return True

class default_not_at_end:
    'the default case is not at the end of the switch statement'
    @lookat(tok.DEFAULT)
    def _lint(self, node):
        siblings = node.parent.kids
        if node.node_index != len(siblings)-1:
            return siblings[node.node_index+1]

class duplicate_case_in_switch:
    'duplicate case in switch statement'
    @lookat(tok.CASE)
    def _lint(self, node):
        # Only look at previous siblings
        siblings = node.parent.kids
        siblings = siblings[:node.node_index]
        # Compare values (first kid)
        node_value = node.kids[0]
        for sibling in siblings:
            if sibling.kind == tok.CASE:
                sibling_value = sibling.kids[0]
                if node_value.is_equivalent(sibling_value, True):
                    return node

class missing_default_case:
    'missing default case in switch statement'
    @lookat(tok.SWITCH)
    def _lint(self, node):
        value, cases = node.kids
        for case in cases.kids:
            if case.kind == tok.DEFAULT:
                return
        return node

class with_statement:
    'with statement hides undeclared variables; use temporary variable instead'
    @lookat(tok.WITH)
    def _lint(self, node):
        return node

class useless_comparison:
    'useless comparison; comparing identical expressions'
    @lookat(tok.EQOP,tok.RELOP)
    def _lint(self, node):
        lvalue, rvalue = node.kids
        if lvalue.is_equivalent(rvalue):
            return node

class use_of_label:
    'use of label'
    @lookat((tok.COLON, op.NAME))
    def _lint(self, node):
        return node

class meaningless_block:
    'meaningless block; curly braces have no impact'
    @lookat(tok.LC)
    def _lint(self, node):
        if node.parent and node.parent.kind == tok.LC:
            return node

class misplaced_regex:
    'regular expressions should be preceded by a left parenthesis, assignment, colon, or comma'
    @lookat((tok.OBJECT, op.REGEXP))
    def _lint(self, node):
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
        return node

class assign_to_function_call:
    'assignment to a function call'
    @lookat(tok.ASSIGN)
    def _lint(self, node):
        if node.kids[0].kind == tok.LP:
            return node

class ambiguous_else_stmt:
    'the else statement could be matched with one of multiple if statements (use curly braces to indicate intent'
    @lookat(tok.IF)
    def _lint(self, node):
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
                return else_
            tmp = tmp.parent

class block_without_braces:
    'block statement without curly braces'
    @lookat(tok.IF, tok.WHILE, tok.DO, tok.FOR, tok.WITH)
    def _lint(self, node):
        if node.kids[1].kind != tok.LC:
            return node.kids[1]

class ambiguous_nested_stmt:
    'block statements containing block statements should use curly braces to resolve ambiguity'
    _block_nodes = (tok.IF, tok.WHILE, tok.DO, tok.FOR, tok.WITH)
    @lookat(*_block_nodes)
    def _lint(self, node):
        # Ignore "else if"
        if node.kind == tok.IF and node.node_index == 2 and node.parent.kind == tok.IF:
            return

        # If the parent is a block, it means a block statement
        # was inside a block statement without clarifying curlies.
        # (Otherwise, the node type would be tok.LC.)
        if node.parent.kind in self._block_nodes:
            return node

class inc_dec_within_stmt:
    'increment (++) and decrement (--) operators used as part of greater statement'
    @lookat(tok.INC, tok.DEC)
    def _lint(self, node):
        if node.parent.kind == tok.SEMI:
            return None

        # Allow within the third part of the "for"
        tmp = node
        while tmp and tmp.parent and tmp.parent.kind == tok.COMMA:
            tmp = tmp.parent
        if tmp and tmp.node_index == 2 and \
            tmp.parent.kind == tok.RESERVED and \
            tmp.parent.parent.kind == tok.FOR:
            return None

        return node
    def _is_for_ternary_stmt(self, node, branch=None):
        if node.parent and node.parent.kind == tok.COMMA:
            return _is_for_ternary_stmt(node.parent, branch)
        return node.node_index == branch and \
            node.parent and \
            node.parent.kind == tok.RESERVED and \
            node.parent.parent.kind == tok.FOR

class comma_separated_stmts:
    'multiple statements separated by commas (use semicolons?)'
    @lookat(tok.COMMA)
    def _lint(self, node):
        # Allow within the first and third part of "for(;;)"
        if _get_branch_in_for(node) in (0, 2):
            return
        # This is an array
        if node.parent.kind == tok.RB:
            return
        return node

class empty_statement:
    'empty statement or extra semicolon'
    @lookat(tok.SEMI)
    def _semi(self, node):
        if not node.kids[0]:
            return node
    @lookat(tok.LC)
    def _lc(self, node):
        if node.kids:
            return
        # Ignore the outermost block.
        if not node.parent:
            return
        # Some empty blocks are meaningful.
        if node.parent.kind in (tok.CATCH, tok.CASE, tok.DEFAULT, tok.SWITCH, tok.FUNCTION):
            return
        return node

class missing_break:
    'missing break statement'
    @lookat(tok.CASE, tok.DEFAULT)
    def _lint(self, node):
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
            return node.parent.kids[node.node_index+1]

class missing_break_for_last_case:
    'missing break statement for last case in switch'
    @lookat(tok.CASE, tok.DEFAULT)
    def _lint(self, node):
        if node.node_index < len(node.parent.kids)-1:
            return
        case_contents = node.kids[1]
        assert case_contents.kind == tok.LC
        if None in _get_exit_points(case_contents):
            return node

class multiple_plus_minus:
    'unknown order of operations for successive plus (e.g. x+++y) or minus (e.g. x---y) signs'
    @lookat(tok.INC)
    def _inc(self, node):
        if node.node_index == 0 and node.parent.kind == tok.PLUS:
            return node
    @lookat(tok.DEC)
    def _dec(self, node):
        if node.node_index == 0 and node.parent.kind == tok.MINUS:
            return node

class useless_assign:
    'useless assignment'
    @lookat((tok.NAME, op.SETNAME))
    def _lint(self, node):
        if node.parent.kind == tok.ASSIGN:
            assert node.node_index == 0
            value = node.parent.kids[1]
        elif node.parent.kind == tok.VAR:
            value = node.kids[0]
        if value and value.kind == tok.NAME and node.atom == value.atom:
            return node

class unreachable_code:
    'unreachable code'
    @lookat(tok.BREAK, tok.CONTINUE, tok.RETURN, tok.THROW)
    def _lint(self, node):
        if node.parent.kind == tok.LC and \
            node.node_index != len(node.parent.kids)-1:
            return node.parent.kids[node.node_index+1]

class meaningless_block:
    'meaningless block; curly braces have no impact'
    #TODO: @lookat(tok.IF)
    def _lint(self, node):
        condition, if_, else_ = node.kids
        if condition.kind == tok.PRIMARY and condition.opcode in (op.TRUE, op.FALSE, op.NULL):
            return condition
    #TODO: @lookat(tok.WHILE)
    def _lint(self, node):
        condition = node.kids[0]
        if condition.kind == tok.PRIMARY and condition.opcode in (op.FALSE, op.NULL):
            return condition
    @lookat(tok.LC)
    def _lint(self, node):
        if node.parent and node.parent.kind == tok.LC:
            return node

class useless_void:
    'use of the void type may be unnecessary (void is always undefined)'
    @lookat((tok.UNARYOP, op.VOID))
    def _lint(self, node):
        return node

class parseint_missing_radix:
    'parseInt missing radix parameter'
    @lookat((tok.LP, op.CALL))
    def _lint(self, node):
        if node.kids[0].kind == tok.NAME and node.kids[0].atom == 'parseInt' and len(node.kids) <= 2:
            return node

class leading_decimal_point:
    'leading decimal point may indicate a number or an object member'
    @lookat(tok.NUMBER)
    def _lint(self, node):
        if node.atom.startswith('.'):
            return node

class trailing_decimal_point:
    'trailing decimal point may indicate a number or an object member'
    @lookat(tok.NUMBER)
    def _lint(self, node):
        if node.parent.kind == tok.DOT:
            return node
        if node.atom.endswith('.'):
            return node

class octal_number:
    'leading zeros make an octal number'
    _regexp = re.compile('^0[0-9]')
    @lookat(tok.NUMBER)
    def _line(self, node):
        if self._regexp.match(node.atom):
            return node

class trailing_comma_in_array:
    'extra comma is not recommended in array initializers'
    @lookat(tok.RB)
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

