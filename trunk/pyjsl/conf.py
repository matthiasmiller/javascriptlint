import os

import warnings

class ConfError(Exception):
	def __init__(self, error):
		Exception.__init__(error)
		self.lineno = None
		self.path = None

class Setting():
	wants_parm = False
	wants_dir = False

class BooleanSetting(Setting):
	wants_parm = False
	def __init__(self, default):
		self.value = default
	def load(self, enabled):
		self.value = enabled

class StringSetting(Setting):
	wants_parm = True
	def __init__(self, default):
		self.value = default
	def load(self, enabled, parm):
		if not enabled:
			raise ConfError, 'Expected +.'
		self.value = parm

class DeclareSetting(Setting):
	wants_parm = True
	def __init__(self):
		self.value = []
	def load(self, enabled, parm):
		if not enabled:
			raise ConfError, 'Expected +.'
		self.value.append(parm)

class ProcessSetting(Setting):
	wants_parm = True
	wants_dir = True
	def __init__(self, recurse_setting):
		self.value = []
		self._recurse = recurse_setting
	def load(self, enabled, parm, dir):
		if dir:
			parm = os.path.join(dir, parm)
		self.value.append((self._recurse.value, parm))

class Conf():
	def __init__(self):
		recurse = BooleanSetting(False) 
		self._settings = {
			'recurse': recurse,
			'show_context': BooleanSetting(False),
			'output-format': StringSetting('TODO'),
			'lambda_assign_requires_semicolon': BooleanSetting(False),
			'legacy_control_comments': BooleanSetting(True),
			'jscript_function_extensions': BooleanSetting(False),
			'always_use_option_explicit': BooleanSetting(False),
			'define': DeclareSetting(),
			'context': BooleanSetting(False),
			'process': ProcessSetting(recurse),
			# SpiderMonkey warnings
			'no_return_value': BooleanSetting(True),
			'equal_as_assign': BooleanSetting(True),
			'anon_no_return_value': BooleanSetting(True)
		}
		for klass in warnings.klasses:
			self._settings[klass.__name__] = BooleanSetting(True)
		self.loadline('-block_without_braces')

	def loadfile(self, path):
		path = os.path.abspath(path)
		conf = open(path, 'r').read()
		try:
			self.loadtext(conf, dir=os.path.dirname(path))
		except ConfError, error:
			error.path = path
			raise

	def loadtext(self, conf, dir=None):
		lines = conf.splitlines()
		for lineno in range(0, len(lines)):
			try:
				self.loadline(lines[lineno], dir)
			except ConfError, error:
				error.lineno = lineno
				raise

	def loadline(self, line, dir=None):
		assert not '\r' in line
		assert not '\n' in line

		# Allow comments
		line = line.partition('#')[0]
		line = line.rstrip()
		if not line:
			return

		# Parse the +/-
		if line.startswith('+'):
			enabled = True
		elif line.startswith('-'):
			enabled = False
		else:
			raise ConfError, 'Expected + or -.'
		line = line[1:]

		# Parse the key/parms
		name = line.split()[0].lower()
		parm = line[len(name):].lstrip()

		# Load the setting
		setting = self._settings[name]
		args = {
			'enabled': enabled
		}
		if setting.wants_parm:
			args['parm'] = parm
		elif parm:
			raise ConfError, 'The %s setting does not expect a parameter.' % name
		if setting.wants_dir:
			args['dir'] = dir
		setting.load(**args)

	def __getitem__(self, name):
		if name == 'paths':
			name = 'process'
		elif name == 'declarations':
			name = 'define'
		return self._settings[name].value

