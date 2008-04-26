#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import os.path
import re

import conf
import jsparse
import visitation
import warnings
import util

from pyspidermonkey import tok, op

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

_identifier = re.compile('^[A-Za-z_$][A-Za-z0-9_$]*$')

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
    def __init__(self, node):
        self._is_with_scope = node.kind == tok.WITH
        self._parent = None
        self._kids = []
        self._identifiers = {}
        self._references = []
        self._node = node
    def add_scope(self, node):
        self._kids.append(Scope(node))
        self._kids[-1]._parent = self
        if self._is_with_scope:
            self._kids[-1]._is_with_scope = True
        return self._kids[-1]
    def add_declaration(self, name, node):
        if not self._is_with_scope:
            self._identifiers[name] = node
    def add_reference(self, name, node):
        if not self._is_with_scope:
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
    def get_undeclared_identifiers(self):
        identifiers = []
        for child in self._kids:
            identifiers += child.get_undeclared_identifiers()
        for name, node in self._references:
            if not self.resolve_identifier(name):
                identifiers.append(node)
        return identifiers
    def find_scope(self, node):
        for kid in self._kids:
            scope = kid.find_scope(node)
            if scope:
                return scope

        # Always add it to the outer scope.
        if not self._parent or \
            (node.start_pos() >= self._node.start_pos() and \
            node.end_pos() <= self._node.end_pos()):
            return self

        return None

def lint_files(paths, lint_error, conf=conf.Conf()):
    def lint_file(path):
        def import_script(import_path):
            import_path = os.path.join(os.path.dirname(path), import_path)
            return lint_file(import_path)
        def _lint_error(*args):
            return lint_error(normpath, *args)

        normpath = util.normpath(path)
        if not normpath in lint_cache:
            lint_cache[normpath] = {}
            script = util.readfile(path)
            print normpath
            _lint_script(script, lint_cache[normpath], _lint_error, conf, import_script)
        return lint_cache[normpath]

    lint_cache = {}
    for path in paths:
        lint_file(path)

def _lint_script(script, script_cache, lint_error, conf, import_callback):
    def parse_error(row, col, msg):
        if not msg in ('redeclared_var', 'var_hides_arg'):
                parse_errors.append((jsparse.NodePos(row, col), msg))

    def report(node, errname):
        _report(node.start_pos(), errname, True)

    def _report(pos, errname, require_key):
        try:
            if not conf[errname]:
                return
        except KeyError, err:
            if require_key:
                raise

        for start, end in ignores:
            if pos >= start and pos <= end:
                return

        return lint_error(pos.line, pos.col, errname)

    parse_errors = []
    root, comments = jsparse.parse(script, parse_error)
    ignores = []
    start_ignore = None
    declares = []
    import_paths = []
    for comment in comments:
        cc = _parse_control_comment(comment)
        if cc:
            node, keyword, parms = cc
            if keyword == 'declare':
                if not _identifier.match(parms):
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
        else:
            if comment.opcode == 'c_comment':
                if '/*' in comment.atom or comment.atom.endswith('/'):
                    report(comment, 'nested_comment')
            if comment.atom.lower().startswith('jsl:'):
                report(comment, 'jsl_cc_not_understood')
            elif comment.atom.startswith('@'):
                report(comment, 'legacy_cc_not_understood')
    if start_ignore:
        report(start_ignore, 'mismatch_ctrl_comments')

    # Wait to report parse errors until loading jsl:ignore directives.
    for pos, msg in parse_errors:
        _report(pos, msg, False)

    # Find all visitors and convert them into "onpush" callbacks that call "report"
    visitors = {
        'push': warnings.make_visitors()
    }
    for event in visitors:
        for kind, callbacks in visitors[event].items():
            visitors[event][kind] = [_getreporter(callback, report) for callback in callbacks]

    assert not script_cache
    imports = script_cache['imports'] = set()
    scope = script_cache['scope'] = Scope(root)

    # Push the scope/variable checks.
    visitation.make_visitors(visitors, [_get_scope_checks(scope, report)])

    # kickoff!
    _lint_node(root, visitors)

    # Process imports by copying global declarations into the universal scope.
    imports |= set(conf['declarations'])
    imports |= _globals
    for path in import_paths:
        cache = import_callback(path)
        imports |= cache['imports']
        imports |= set(cache['scope'].get_identifiers())

    for name, node in declares:
        declare_scope = scope.find_scope(node)
        if declare_scope.get_identifier(name):
            report(node, 'redeclared_var')
        else:
            declare_scope.add_declaration(name, node)

    for node in scope.get_undeclared_identifiers():
        if not node.atom in imports:
            report(node, 'undeclared_identifier')

def _getreporter(visitor, report):
    def onpush(node):
        try:
            ret = visitor(node)
            assert ret is None, 'visitor should raise an exception, not return a value'
        except warnings.LintWarning, warning:
            report(warning.node, visitor.warning)
    return onpush

def _warn_or_declare(scope, name, node, report):
    other = scope.get_identifier(name)
    if other and other.kind == tok.FUNCTION and name in other.fn_args:
        report(node, 'var_hides_arg')
    elif other:
        report(node, 'redeclared_var')
    else:
        scope.add_declaration(name, node)

def _get_scope_checks(scope, report):
    scopes = [scope]

    class scope_checks:
        ' '
        @visitation.visit('push', tok.NAME)
        def _name(self, node):
            if node.node_index == 0 and node.parent.kind == tok.COLON and node.parent.parent.kind == tok.RC:
                pass # left side of object literal
            elif node.parent.kind == tok.CATCH:
                scopes[-1].add_declaration(node.atom, node)
            else:
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

        @visitation.visit('push', tok.VAR)
        def _push_var(self, node):
            for kid in node.kids:
                _warn_or_declare(scope, kid.atom, node, report)

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


