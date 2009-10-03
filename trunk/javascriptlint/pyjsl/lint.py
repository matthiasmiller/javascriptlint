#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import os.path
import re

import conf
import htmlparse
import jsparse
import visitation
import warnings
import util

from spidermonkey import tok, op

_newline_kinds = (
    'eof', 'comma', 'dot', 'semi', 'colon', 'lc', 'rc', 'lp', 'rb', 'assign',
    'relop', 'hook', 'plus', 'minus', 'star', 'divop', 'eqop', 'shop', 'or',
    'and', 'bitor', 'bitxor', 'bitand', 'else', 'try'
) 

_globals = frozenset([
    'Array', 'Boolean', 'Math', 'Number', 'String', 'RegExp', 'Script', 'Date',
    'isNaN', 'isFinite', 'parseFloat', 'parseInt',
    'eval', 'NaN', 'Infinity',
    'escape', 'unescape', 'uneval',
    'decodeURI', 'encodeURI', 'decodeURIComponent', 'encodeURIComponent',
    'Function', 'Object', 
    'Error', 'InternalError', 'EvalError', 'RangeError', 'ReferenceError',
    'SyntaxError', 'TypeError', 'URIError',
    'arguments', 'undefined'
])

def _find_function(node):
    while node and node.kind != tok.FUNCTION:
        node = node.parent
    return node

def _find_functions(node):
    functions = []
    while node:
        if node.kind == tok.FUNCTION:
            functions.append(node)
        node = node.parent
    return functions

def _parse_control_comment(comment):
    """ Returns None or (keyword, parms) """
    if comment.atom.lower().startswith('jsl:'):
        control_comment = comment.atom[4:]
    elif comment.atom.startswith('@') and comment.atom.endswith('@'):
        control_comment = comment.atom[1:-1]
    else:
        return None

    control_comments = {
        'ignoreall': (False),
        'ignore': (False),
        'end': (False),
        'option explicit': (False),
        'import': (True),
        'fallthru': (False),
        'pass': (False),
        'declare': (True)
    }
    if control_comment.lower() in control_comments:
        keyword = control_comment.lower()
    else:
        keyword = control_comment.lower().split()[0]
        if not keyword in control_comments:
            return None

    parms = control_comment[len(keyword):].strip()
    return (comment, keyword, parms)

class Scope:
    """ Outer-level scopes will never be associated with a node.
        Inner-level scopes will always be associated with a node.
    """
    def __init__(self):
        self._parent = None
        self._kids = []
        self._identifiers = {}
        self._references = []
        self._node = None
    def add_scope(self, node):
        assert not node is None
        self._kids.append(Scope())
        self._kids[-1]._parent = self
        self._kids[-1]._node = node
        return self._kids[-1]
    def add_declaration(self, name, node):
        self._identifiers[name] = node
    def add_reference(self, name, node):
        self._references.append((name, node))
    def get_identifier(self, name):
        if name in self._identifiers:
            return self._identifiers[name]
        else:
            return None
    def get_identifiers(self):
        "returns a list of names"
        return self._identifiers.keys()
    def resolve_identifier(self, name):
        if name in self._identifiers:
            return self, self._identifiers[name]
        if self._parent:
            return self._parent.resolve_identifier(name)
        return None
    def get_unreferenced_and_undeclared_identifiers(self):
        """ Returns a tuple of unreferenced and undeclared, where each is a list
            of (scope, name, node) tuples.
        """
        unreferenced = {}
        undeclared = []
        self._find_unreferenced_and_undeclared(unreferenced, undeclared, False)

        # Convert "unreferenced" from a dictionary of:
        #   { (scope, name): node }
        # to a list of:
        #   [ (scope, name, node) ]
        # sorted by node position.
        unreferenced = [(key[0], key[1], node) for key, node
                        in unreferenced.items()]
        unreferenced.sort(key=lambda x: x[2].start_pos())

        return unreferenced, undeclared
    def _find_unreferenced_and_undeclared(self, unreferenced, undeclared,
                                          is_in_with_scope):
        """ unreferenced is a dictionary, such that:
                (scope, name): node
            }
            undeclared is a list, such that: [
                (scope, name, node)
            ]
        """
        if self._node and self._node.kind == tok.WITH:
            is_in_with_scope = True

        # Add all identifiers as unreferenced. Children scopes will remove
        # them if they are referenced.  Variables need to be keyed by name
        # instead of node, because function parameters share the same node.
        for name, node in self._identifiers.items():
            unreferenced[(self, name)] = node

        # Remove all declared variables from the "unreferenced" set; add all
        # undeclared variables to the "undeclared" list.
        for name, node in self._references:
            resolved = self.resolve_identifier(name)
            if resolved:
                # Make sure this isn't an assignment.
                if node.parent.kind in (tok.ASSIGN, tok.INC, tok.DEC) and \
                   node.node_index == 0 and \
                   node.parent.parent.kind == tok.SEMI:
                    continue
                unreferenced.pop((resolved[0], name), None)
            else:
                # with statements cannot have undeclared identifiers.
                if not is_in_with_scope:
                    undeclared.append((self, name, node))

        for child in self._kids:
            child._find_unreferenced_and_undeclared(unreferenced, undeclared,
                                                    is_in_with_scope)
    def find_scope(self, node):
        for kid in self._kids:
            scope = kid.find_scope(node)
            if scope:
                return scope

        # Always add it to the outer scope.
        if not self._parent:
            assert not self._node
            return self

        # Conditionally add it to an inner scope.
        assert self._node
        if (node.start_pos() >= self._node.start_pos() and \
            node.end_pos() <= self._node.end_pos()):
            return self

class _Script:
    def __init__(self):
        self._imports = set()
        self.scope = Scope()
    def importscript(self, script):
        self._imports.add(script)
    def hasglobal(self, name):
        return not self._findglobal(name, set()) is None
    def _findglobal(self, name, searched):
        """ searched is a set of all searched scripts """
        # Avoid recursion.
        if self in searched:
            return

        # Check this scope.
        if self.scope.get_identifier(name):
            return self
        searched.add(self)

        # Search imported scopes.
        for script in self._imports:
            global_ = script._findglobal(name, searched)
            if global_:
                return global_

def lint_files(paths, lint_error, conf=conf.Conf()):
    def lint_file(path, kind):
        def import_script(import_path):
            # The user can specify paths using backslashes (such as when
            # linting Windows scripts on a posix environment.
            import_path = import_path.replace('\\', os.sep)
            import_path = os.path.join(os.path.dirname(path), import_path)
            return lint_file(import_path, 'js')
        def _lint_error(*args):
            return lint_error(normpath, *args)

        normpath = util.normpath(path)
        if normpath in lint_cache:
            return lint_cache[normpath]
        print normpath
        contents = util.readfile(path)
        lint_cache[normpath] = _Script()

        script_parts = []
        if kind == 'js':
            script_parts.append((None, contents))
        elif kind == 'html':
            for script in htmlparse.findscripts(contents):
                if script['src']:
                    other = import_script(script['src'])
                    lint_cache[normpath].importscript(other)
                if script['script'].strip():
                    script_parts.append((script['startpos'], script['script']))
        else:
            assert False, 'Unsupported file kind: %s' % kind

        _lint_script_parts(script_parts, lint_cache[normpath], _lint_error, conf, import_script)
        return lint_cache[normpath]

    lint_cache = {}
    for path in paths:
        ext = os.path.splitext(path)[1]
        if ext.lower() in ['.htm', '.html']:
            lint_file(path, 'html')
        else:
            lint_file(path, 'js')

def _lint_script_part(scriptpos, script, script_cache, conf, ignores,
                      report_native, report_lint, import_callback):
    def parse_error(row, col, msg):
        if not msg in ('anon_no_return_value', 'no_return_value',
                       'redeclared_var', 'var_hides_arg'):
            parse_errors.append((jsparse.NodePos(row, col), msg))

    def report(node, errname, pos=None, **errargs):
        if errname == 'empty_statement' and node.kind == tok.LC:
            for pass_ in passes:
                if pass_.start_pos() > node.start_pos() and \
                   pass_.end_pos() < node.end_pos():
                    passes.remove(pass_)
                    return

        if errname == 'missing_break':
            # Find the end of the previous case/default and the beginning of
            # the next case/default.
            assert node.kind in (tok.CASE, tok.DEFAULT)
            prevnode = node.parent.kids[node.node_index-1]
            expectedfallthru = prevnode.end_pos(), node.start_pos()
        elif errname == 'missing_break_for_last_case':
            # Find the end of the current case/default and the end of the
            # switch.
            assert node.parent.kind == tok.LC
            expectedfallthru = node.end_pos(), node.parent.end_pos()
        else:
            expectedfallthru = None

        if expectedfallthru:
            start, end = expectedfallthru
            for fallthru in fallthrus:
                # Look for a fallthru between the end of the current case or
                # default statement and the beginning of the next token.
                if fallthru.start_pos() > start and fallthru.end_pos() < end:
                    fallthrus.remove(fallthru)
                    return

        report_lint(node, errname, pos, **errargs)

    parse_errors = []
    declares = []
    import_paths = []
    fallthrus = []
    passes = []

    node_positions = jsparse.NodePositions(script, scriptpos)
    possible_comments = jsparse.findpossiblecomments(script, node_positions)

    root = jsparse.parse(script, parse_error, scriptpos)
    if not root:
        # Report errors and quit.
        for pos, msg in parse_errors:
            report_native(pos, msg)
        return

    comments = jsparse.filtercomments(possible_comments, node_positions, root)
    start_ignore = None
    for comment in comments:
        cc = _parse_control_comment(comment)
        if cc:
            node, keyword, parms = cc
            if keyword == 'declare':
                if not util.isidentifier(parms):
                    report(node, 'jsl_cc_not_understood')
                else:
                    declares.append((parms, node))
            elif keyword == 'ignore':
                if start_ignore:
                    report(node, 'mismatch_ctrl_comments')
                else:
                    start_ignore = node
            elif keyword == 'end':
                if start_ignore:
                    ignores.append((start_ignore.start_pos(), node.end_pos()))
                    start_ignore = None
                else:
                    report(node, 'mismatch_ctrl_comments')
            elif keyword == 'import':
                if not parms:
                    report(node, 'jsl_cc_not_understood')
                else:
                    import_paths.append(parms)
            elif keyword == 'fallthru':
                fallthrus.append(node)
            elif keyword == 'pass':
                passes.append(node)
        else:
            if comment.opcode == 'c_comment':
                # Look for nested C-style comments.
                nested_comment = comment.atom.find('/*')
                if nested_comment < 0 and comment.atom.endswith('/'):
                    nested_comment = len(comment.atom) - 1
                # Report at the actual error of the location. Add two
                # characters for the opening two characters.
                if nested_comment >= 0:
                    pos = node_positions.from_offset(node_positions.to_offset(comment.start_pos()) + 2 + nested_comment)
                    report(comment, 'nested_comment', pos=pos)
            if comment.atom.lower().startswith('jsl:'):
                report(comment, 'jsl_cc_not_understood')
            elif comment.atom.startswith('@'):
                report(comment, 'legacy_cc_not_understood')
    if start_ignore:
        report(start_ignore, 'mismatch_ctrl_comments')

    # Wait to report parse errors until loading jsl:ignore directives.
    for pos, msg in parse_errors:
        report_native(pos, msg)

    # Find all visitors and convert them into "onpush" callbacks that call "report"
    visitors = {
        'push': warnings.make_visitors()
    }
    for event in visitors:
        for kind, callbacks in visitors[event].items():
            visitors[event][kind] = [_getreporter(callback, report) for callback in callbacks]

    # Push the scope/variable checks.
    visitation.make_visitors(visitors, [_get_scope_checks(script_cache.scope, report)])

    # kickoff!
    _lint_node(root, visitors)

    for fallthru in fallthrus:
        report(fallthru, 'invalid_fallthru')
    for fallthru in passes:
        report(fallthru, 'invalid_pass')

    # Process imports by copying global declarations into the universal scope.
    for path in import_paths:
        script_cache.importscript(import_callback(path))

    for name, node in declares:
        declare_scope = script_cache.scope.find_scope(node)
        if declare_scope.get_identifier(name):
            report(node, 'redeclared_var', name=name)
        else:
            declare_scope.add_declaration(name, node)

def _lint_script_parts(script_parts, script_cache, lint_error, conf, import_callback):
    def report_lint(node, errname, pos=None, **errargs):
        errdesc = warnings.format_error(errname, **errargs)
        _report(pos or node.start_pos(), errname, errdesc, True)

    def report_native(pos, errname):
        # TODO: Format the error.
        _report(pos, errname, errname, False)

    def _report(pos, errname, errdesc, require_key):
        try:
            if not conf[errname]:
                return
        except KeyError, err:
            if require_key:
                raise

        for start, end in ignores:
            if pos >= start and pos <= end:
                return

        return lint_error(pos.line, pos.col, errname, errdesc)

    for scriptpos, script in script_parts:
        ignores = []
        _lint_script_part(scriptpos, script, script_cache, conf, ignores,
                          report_native, report_lint, import_callback)

    scope = script_cache.scope
    unreferenced, undeclared = scope.get_unreferenced_and_undeclared_identifiers()
    for decl_scope, name, node in undeclared:
        if name in conf['declarations']:
            continue
        if name in _globals:
            continue
        if not script_cache.hasglobal(name):
            report_lint(node, 'undeclared_identifier', name=name)
    for ref_scope, name, node in unreferenced:
        # Ignore the outer scope.
        if ref_scope != scope:
            report_lint(node, 'unreferenced_identifier', name=name)

def _getreporter(visitor, report):
    def onpush(node):
        try:
            ret = visitor(node)
            assert ret is None, 'visitor should raise an exception, not return a value'
        except warnings.LintWarning, warning:
            # TODO: This is ugly hardcoding to improve the error positioning of
            # "missing_semicolon" errors.
            if visitor.warning in ('missing_semicolon', 'missing_semicolon_for_lambda'):
                pos = warning.node.end_pos()
            else:
                pos = None
            report(warning.node, visitor.warning, pos=pos, **warning.errargs)
    return onpush

def _warn_or_declare(scope, name, node, report):
    parent_scope, other = scope.resolve_identifier(name) or (None, None)
    if other and other.kind == tok.FUNCTION and name in other.fn_args:
        report(node, 'var_hides_arg', name=name)
    elif other and parent_scope == scope:
        report(node, 'redeclared_var', name=name)
    else:
        # TODO: Warn when hiding a variable in a parent scope.
        scope.add_declaration(name, node)

def _get_scope_checks(scope, report):
    scopes = [scope]

    class scope_checks:
        ' '
        @visitation.visit('push', tok.NAME)
        def _name(self, node):
            if node.node_index == 0 and node.parent.kind == tok.COLON and node.parent.parent.kind == tok.RC:
                return # left side of object literal
            if node.parent.kind == tok.VAR:
                _warn_or_declare(scopes[-1], node.atom, node, report)
                return
            if node.parent.kind == tok.CATCH:
                scopes[-1].add_declaration(node.atom, node)
            scopes[-1].add_reference(node.atom, node)

        @visitation.visit('push', tok.FUNCTION)
        def _push_func(self, node):
            if node.fn_name:
                _warn_or_declare(scopes[-1], node.fn_name, node, report)
            self._push_scope(node)
            for var_name in node.fn_args:
                scopes[-1].add_declaration(var_name, node)

        @visitation.visit('push', tok.LEXICALSCOPE, tok.WITH)
        def _push_scope(self, node):
            scopes.append(scopes[-1].add_scope(node))

        @visitation.visit('pop', tok.FUNCTION, tok.LEXICALSCOPE, tok.WITH)
        def _pop_scope(self, node):
            scopes.pop()

    return scope_checks


def _lint_node(node, visitors):

    for kind in (node.kind, (node.kind, node.opcode)):
        if kind in visitors['push']:
            for visitor in visitors['push'][kind]:
                visitor(node)

    for child in node.kids:
        if child:
            _lint_node(child, visitors)

    for kind in (node.kind, (node.kind, node.opcode)):
        if kind in visitors['pop']:
            for visitor in visitors['pop'][kind]:
                visitor(node)


