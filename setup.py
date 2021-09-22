#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import distutils.command.build
import distutils.command.clean
import os
import subprocess
import sys

try:
    import py2exe
except ImportError:
    py2exe = None

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
    if py2exe is not None:
        class _MyPy2Exe(py2exe.distutils_buildexe.py2exe):
            def run(self):
                super().run()
                assert self.distribution.scripts
                for script in self.distribution.scripts:
                    exe = os.path.join(self.dist_dir, "%s.exe" % script)
                    print('Compressing %s' % exe)
                    subprocess.check_output(['win32util/upx.exe', '-9', exe])

        args['cmdclass']['py2exe'] = _MyPy2Exe

        args.update(
            console = ['jsl'],
            options = {
                'py2exe': {
                    'excludes': [
                        'resource',
                        'bz2',
                        '_ssl',
                        '_hashlib',
                        'socket',
                        'select',
                        'hotshot',
                    ],
                    'bundle_files': 1,
                    'optimize': 1, # requires 1 to preserve docstrings
                    'dll_excludes': [
                        'mswsock.dll',
                        'powrprof.dll',
                        'CRYPT32.dll'
                    ]

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
