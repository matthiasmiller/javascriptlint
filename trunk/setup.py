#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import distutils.command.build
import distutils.command.clean
import os
import subprocess
import sys

class _BuildError(Exception):
    pass

def _getrevnum():
    path = os.path.dirname(os.path.abspath(__file__))
    p = subprocess.Popen(['svnversion', path], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise _BuildError, 'Error running svnversion: %s' % stderr
    version = stdout.strip().rstrip('M')
    return int(version)

if __name__ == '__main__':
    cmdclass = {
        'build': distutils.command.build.build,
        'clean': distutils.command.clean.clean,
    }
    args = {}
    args.update(
        name = 'javascriptlint',
        version = '0.0.0.%i' % _getrevnum(),
        author = 'Matthias Miller',
        author_email = 'info@javascriptlint.com',
        url = 'http://www.javascriptlint.com/',
        cmdclass = cmdclass,
        description = 'JavaScript Lint (pyjsl beta r%i)' % _getrevnum(),
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
                        raise _BuildError, 'Error running upx on %s' % exe
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

