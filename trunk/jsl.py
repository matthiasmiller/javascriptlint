#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import codecs
import glob
import os
import sys
import unittest
from optparse import OptionParser

import pyjsl.conf
import pyjsl.htmlparse
import pyjsl.jsparse
import pyjsl.lint
import pyjsl.util

_lint_results = {
    'warnings': 0,
    'errors': 0
}

def _dump(paths):
    for path in paths:
        script = pyjsl.util.readfile(path)
        pyjsl.jsparse.dump_tree(script)

def _lint(paths, conf):
    def lint_error(path, line, col, errname, errdesc):
        _lint_results['warnings'] = _lint_results['warnings'] + 1
        print pyjsl.util.format_error(conf['output-format'], path, line, col,
                                      errname, errdesc)
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

def _profile_enabled(func, *args, **kwargs):
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
def _profile_disabled(func, *args, **kwargs):
    func(*args, **kwargs)

def main():
    parser = OptionParser(usage="%prog [options] [files]")
    add = parser.add_option
    add("--conf", dest="conf", metavar="CONF",
        help="set the conf file")
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

    profile_func = _profile_disabled
    if options.profile:
        profile_func = _profile_enabled

    if options.unittest:
        suite = unittest.TestSuite();
        for module in [pyjsl.htmlparse, pyjsl.jsparse, pyjsl.util]:
            suite.addTest(unittest.findTestCases(module))

        runner = unittest.TextTestRunner(verbosity=options.verbosity)
        runner.run(suite)

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
    sys.exit(1)

if __name__ == '__main__':
    main()

