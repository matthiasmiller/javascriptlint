#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import codecs
import glob
import os
import sys
import unittest
from optparse import OptionParser

try:
    import setup
except ImportError:
    pass
else:
    sys.path.append(setup.get_lib_path())

import pyjsl.conf
import pyjsl.jsparse
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
            try:
                test.run(file)
            except test.TestError, error:
                print error

def _dump(paths):
    for path in paths:
        script = pyjsl.util.readfile(path)
        pyjsl.jsparse.dump_tree(script)

def _lint(paths, conf):
    def lint_error(path, line, col, errname):
        _lint_results['warnings'] = _lint_results['warnings'] + 1
        print '%s(%i): %s' % (path, line+1, errname)
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

if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] [files]")
    add = parser.add_option
    add("--conf", dest="conf", metavar="CONF",
        help="set the conf file")
    add("-t", "--test", dest="test", action="store_true", default=False,
        help="run the javascript tests")
    add("--profile", dest="profile", action="store_true", default=False,
        help="turn on hotshot profiling")
    add("--dump", dest="dump", action="store_true", default=False,
        help="dump this script")
    add("--unittest", dest="unittest", action="store_true", default=False,
        help="run the python unittests")
    add("--quiet", dest="verbosity", action="store_const", const=0,
        help="minimal output")
    add("--verbose", dest="verbosity", action="store_const", const=2,
        help="verbose output")
    parser.set_defaults(verbosity=1)
    options, args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    conf = pyjsl.conf.Conf()
    if options.conf:
        conf.loadfile(options.conf)

    profile_func = profile_disabled
    if options.profile:
        profile_func = profile_enabled

    if options.unittest:
        suite = unittest.TestSuite();
        for module in [pyjsl.jsparse, pyjsl.util]:
            suite.addTest(unittest.findTestCases(module))

        runner = unittest.TextTestRunner(verbosity=options.verbosity)
        runner.run(suite)

    if options.test:
        profile_func(run_tests)

    paths = []
    for recurse, path in conf['paths']:
        paths.extend(_resolve_paths(path, recurse))
    for arg in args:
        paths.extend(_resolve_paths(arg, False))
    if options.dump:
        profile_func(_dump, paths)
    else:
        profile_func(_lint, paths, conf)

    if _lint_results['errors']:
        sys.exit(3)
    if _lint_results['warnings']:
        sys.exit(1)

