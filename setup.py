#!/usr/bin/python
from distutils.core import setup, Extension
import os

try:
	import py2exe
except ImportError:
	pass

# Add the bin directory to the module search path
def get_lib_path():
	import distutils.dist
	import distutils.command.build
	dist = distutils.dist.Distribution()
	build = distutils.command.build.build(dist)
	build.finalize_options()
	return os.path.join(os.path.dirname(__file__), build.build_platlib)

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
			sources = ['pyspidermonkey/pyspidermonkey.c']
		)
	setup(
		name = 'pyjsl',
		version = '1.0',
		author = 'Matthias Miller',
		author_email = 'info@javascriptlint.com',
		url = 'http://www.javascriptlint.com/',
		console = ['jsl.py'],
		description = 'JavaScript Lint',
		ext_modules = [pyspidermonkey],
		options = {
			'py2exe': {
				'excludes': 'setup',
				'bundle_files': 1
			}
		},
		zipfile = None
	)

