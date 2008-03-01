#!/usr/bin/python
import codecs
import getopt
import glob
import os
import sys
import unittest

try:
	import setup
except ImportError:
	pass
else:
	sys.path.append(setup.get_lib_path())

import pyjsl.conf
import pyjsl.parse
import pyjsl.util
import test

_lint_results = {
	'warnings': 0,
	'errors': 0
}

def get_test_files():
	# Get a list of test files.
	dir_ = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tests')

	all_files = []
	for root, dirs, files in os.walk(dir_):
		all_files += [os.path.join(dir_, root, file) for file in files]
		if '.svn' in dirs:
			dirs.remove('.svn')
		# TODO
		if 'conf' in dirs:
			dirs.remove('conf')
	all_files.sort()
	return all_files

def run_tests():
	for file in get_test_files():
		if file.endswith('.htm') or file.endswith('.html'):
			continue #TODO
		elif file.endswith('.js'):
			print file
			try:
				test.run(file)
			except test.TestError, error:
				print error

def _dump(paths):
	for path in paths:
		script = pyjsl.util.readfile(path)
		pyjsl.parse.dump_tree(script)

def _lint(paths, conf):
	def lint_error(path, line, col, errname):
		_lint_results['warnings'] = _lint_results['warnings'] + 1
		print '%s(%i): %s' % (path, line, errname)
	pyjsl.lint.lint_files(paths, lint_error, conf=conf)

def _resolve_paths(path, recurse):
	if os.path.isfile(path):
		return [path]
	elif os.path.isdir(path):
		dir = path
		pattern = '*'
	else:
		dir, pattern = os.path.split(path)

	# Build a list of directories
	dirs = [dir]
	if recurse:
		for cur_root, cur_dirs, cur_files in os.walk(dir):
			for name in cur_dirs:
				dirs.append(os.path.join(cur_root, name))

	# Glob all files.
	paths = []
	for dir in dirs:
		paths.extend(glob.glob(os.path.join(dir, pattern)))
	return paths

def profile_enabled(func, *args, **kwargs):
	import tempfile
	import hotshot
	import hotshot.stats
	handle, filename = tempfile.mkstemp()
	profile = hotshot.Profile(filename)
	profile.runcall(func, *args, **kwargs)
	profile.close()
	stats = hotshot.stats.load(filename)
	stats = stats.sort_stats("time")
	stats.print_stats()
def profile_disabled(func, *args, **kwargs):
	func(*args, **kwargs)

def usage():
	print """
Usage:
   jsl [files]
   --help (-h)  print this help
   --test (-t)  run tests
   --dump=      dump this script
"""

if __name__ == '__main__':
	try:
		opts, args = getopt.getopt(sys.argv[1:], 'ht:v', ['conf=', 'help', 'test', 'dump', 'unittest', 'profile'])
	except getopt.GetoptError:
		usage()
		sys.exit(2)

	dump = False
	conf = pyjsl.conf.Conf()
	profile_func = profile_disabled
	for opt, val in opts:
		if opt in ('-h', '--help'):
			usage()
			sys.exit()
		if opt in ('--dump',):
			dump = True
		if opt in ('-t', '--test'):
			profile_func(run_tests)
		if opt in ('--unittest',):
			unittest.main(pyjsl.parse, argv=sys.argv[:1])
		if opt in ('--profile',):
			profile_func = profile_enabled
		if opt in ('--conf',):
			conf.loadfile(val)

	paths = []
	for recurse, path in conf['paths']:
		paths.extend(_resolve_paths(path, recurse))
	for arg in args:
		paths.extend(_resolve_paths(arg, False))
	if dump:
		profile_func(_dump, paths)
	else:
		profile_func(_lint, paths, conf)

	if _lint_results['errors']:
		sys.exit(3)
	if _lint_results['warnings']:
		sys.exit(1)

