#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import distutils.command.build
import distutils.command.clean
import os
import subprocess
import sys

def _runmakefiles(distutils_dir, build_opt=1, args=[]):
    # First build SpiderMonkey.
    subprocess.check_call(['make', '-f', 'Makefile.ref', '-C',
                           'spidermonkey/src', 'BUILD_OPT=%i' % build_opt] + \
                            args)

    # Then copy the files to the build directory.
    env = dict(os.environ)
    if distutils_dir:
        env['DISTUTILS_DIR'] = distutils_dir
    subprocess.check_call(['make', '-f', 'Makefile.SpiderMonkey',
                          'BUILD_OPT=%i' % build_opt] + args, env=env)

class _MyBuild(distutils.command.build.build):
    def run(self):
        _runmakefiles(self.build_platlib)
        distutils.command.build.build.run(self)

class _MyClean(distutils.command.clean.clean):
    def run(self):
        _runmakefiles(None, args=['clean'])
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
        packages = ['javascriptlint', 'javascriptlint.pyjsl'],
        scripts = ['jsl']
    )
    try:
        import py2exe
    except ImportError:
        pass
    else:
        args.update(
            console = ['jsl.py'],
            options = {
                'py2exe': {
                    'excludes': ['pyjsl.spidermonkey_'],
                    'bundle_files': 1
                }
            },
            zipfile = None
        )
    setup(**args)

