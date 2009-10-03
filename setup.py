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
            'pyspidermonkey',
            include_dirs = ['spidermonkey/src', 'build/spidermonkey'],
            library_dirs = ['build/spidermonkey'],
            libraries = [library],
            sources = [
                'pyspidermonkey/pyspidermonkey.c',
                'pyspidermonkey/nodepos.c'
            ]
        )
    args = {}
    args.update(
        name = 'pyjsl',
        version = '1.0',
        author = 'Matthias Miller',
        author_email = 'info@javascriptlint.com',
        url = 'http://www.javascriptlint.com/',
        description = 'JavaScript Lint',
        ext_modules = [pyspidermonkey]
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

