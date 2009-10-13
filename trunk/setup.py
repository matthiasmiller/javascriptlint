#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import distutils.command.build
import distutils.command.clean
import os
import subprocess
import sys

class _MakefileError(Exception):
    pass

def _runmakefiles(distutils_dir, build_opt=1, target=None):
    args = ['BUILD_OPT=%i' % build_opt]
    if distutils_dir:
        args.append('DISTUTILS_DIR=%s' % distutils_dir)
    if target:
        args.append(target)

    # First build SpiderMonkey. Force it to link statically against the CRT to
    # make deployment easier.
    ret = subprocess.call(['make', '-f', 'Makefile.ref', '-C',
                           'spidermonkey/src', 'XCFLAGS=-MT'] + args)
    if ret != 0:
        raise _MakefileError, 'Error running make.'

    # Then copy the files to the build directory.
    ret = subprocess.call(['make', '-f', 'Makefile.SpiderMonkey'] + args)
    if ret != 0:
        raise _MakefileError, 'Error running make.'

class _MyBuild(distutils.command.build.build):
    def run(self):
        # py2exe is calling reinitialize_command without finalizing.
        self.ensure_finalized()

        _runmakefiles(self.build_platlib)
        distutils.command.build.build.run(self)

class _MyClean(distutils.command.clean.clean):
    def run(self):
        _runmakefiles(None, target='clean')
        distutils.command.clean.clean.run(self)

if __name__ == '__main__':
    if os.name == 'nt':
        library = 'js32'
    else:
        library = 'js'
    pyspidermonkey = Extension(
            'javascriptlint.pyspidermonkey',
            include_dirs = ['spidermonkey/src', 'build/spidermonkey'],
            library_dirs = ['build/spidermonkey'],
            libraries = [library],
            sources = [
                'javascriptlint/pyspidermonkey/pyspidermonkey.c',
                'javascriptlint/pyspidermonkey/nodepos.c'
            ]
        )
    cmdclass = {
        'build': _MyBuild,
        'clean': _MyClean,
    }
    args = {}
    args.update(
        name = 'javascriptlint',
        version = '1.0',
        author = 'Matthias Miller',
        author_email = 'info@javascriptlint.com',
        url = 'http://www.javascriptlint.com/',
        cmdclass = cmdclass,
        description = 'JavaScript Lint',
        ext_modules = [pyspidermonkey],
        packages = ['javascriptlint'],
        scripts = ['jsl']
    )
    try:
        import py2exe
    except ImportError:
        pass
    else:
        args.update(
            console = ['jsl'],
            options = {
                'py2exe': {
                    'excludes': ['javascriptlint.spidermonkey_'],
                    'bundle_files': 1
                }
            },
            zipfile = None
        )
    setup(**args)

