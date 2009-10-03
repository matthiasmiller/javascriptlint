#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
from distutils.core import setup, Extension
import os
import sys

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
    args = {}
    args.update(
        name = 'javascriptlint',
        version = '1.0',
        author = 'Matthias Miller',
        author_email = 'info@javascriptlint.com',
        url = 'http://www.javascriptlint.com/',
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

