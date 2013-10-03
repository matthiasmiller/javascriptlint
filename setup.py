#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import distutils.command.build
import distutils.command.clean
import os
import subprocess
import sys

from javascriptlint import version

class _BuildError(Exception):
    pass

def _setup():
    cmdclass = {
        'build': distutils.command.build.build,
        'clean': distutils.command.clean.clean,
    }
    args = {}
    args.update(
        name = 'javascriptlint',
        version = version.version,
        author = 'Matthias Miller',
        author_email = 'info@javascriptlint.com',
        url = 'http://www.javascriptlint.com/',
        cmdclass = cmdclass,
        description = 'JavaScript Lint %s' % version.version,
        packages = ['javascriptlint'],
        scripts = ['jsl']
    )
    try:
        import py2exe
    except ImportError:
        pass
    else:
        class _MyPy2Exe(py2exe.build_exe.py2exe):
            def run(self):
                py2exe.build_exe.py2exe.run(self)
                for exe in self.console_exe_files:
                    ret = subprocess.call(['upx', '-9', exe])
                    if ret != 0:
                        raise _BuildError('Error running upx on %s' % exe)
        args['cmdclass']['py2exe'] = _MyPy2Exe

        args.update(
            console = ['jsl'],
            options = {
                'py2exe': {
                    'excludes': ['resource'],
                    'bundle_files': 1,
                    'optimize': 1, # requires 1 to preserve docstrings
                }
            },
            zipfile = None
        )
    setup(**args)

def _main():
    # Create a temporary __svnversion__.py to bundle the version
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'javascriptlint', '__svnversion__.py')
    with open(path, 'w') as f:
        f.write('version = %r' % version.version)
    try:
        _setup()
    finally:
        os.unlink(path)
        if os.path.exists(path + 'c'):
            os.unlink(path + 'c')

if __name__ == '__main__':
    _main()
