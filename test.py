import re

import pyjsl.conf
import pyjsl.lint

class TestError(Exception):
	pass

def _get_conf(script):
	regexp = re.compile(r"/\*conf:([^*]*)\*/")
	text = '\n'.join(regexp.findall(script))
	conf = pyjsl.conf.Conf()
	conf.loadtext(text)
	return conf

def _get_expected_warnings(script):
	"returns an array of tuples -- line, warning"
	warnings = []

	regexp = re.compile(r"/\*warning:([^*]*)\*/")

	lines = script.splitlines()
	for i in range(0, len(lines)):
		for warning in regexp.findall(lines[i]):
			# TODO: implement these
			unimpl_warnings = ('ambiguous_newline', 'dup_option_explicit', 'invalid_pass',
				'missing_semicolon'
			)
			if not warning in unimpl_warnings:
				warnings.append((i, warning))
	return warnings

def run(path):
	# Parse the script and find the expected warnings.
	script = open(path).read()
	expected_warnings = _get_expected_warnings(script)
	unexpected_warnings = []
	conf = _get_conf(script)

	def lint_error(path, line, col, errname):
		warning = (line, errname)

		# Bad hack to fix line numbers on ambiguous else statements
		# TODO: Fix tests.
		if errname == 'ambiguous_else_stmt' and not warning in expected_warnings:
			warning = (line-1, errname)

		if warning in expected_warnings:
			expected_warnings.remove(warning)
		else:
			unexpected_warnings.append(warning)

	pyjsl.lint.lint_files([path], lint_error, conf=conf)

	errors = []
	if expected_warnings:
		errors.append('Expected warnings:')
		for line, warning in expected_warnings:
			errors.append('\tline %i: %s' % (line+1, warning))
	if unexpected_warnings:
		errors.append('Unexpected warnings:')
		for line, warning in unexpected_warnings:
			errors.append('\tline %i: %s' % (line+1, warning))
	if errors:
		raise TestError, '\n'.join(errors)

