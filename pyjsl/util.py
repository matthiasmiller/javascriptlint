import codecs
import os.path

def readfile(path):
	file = codecs.open(path, 'r', 'utf-8')
	contents = file.read()
	if contents[0] == unicode(codecs.BOM_UTF8, 'utf8'):
		contents = contents[1:]
	return contents

def normpath(path):
	path = os.path.abspath(path)
	path = os.path.normcase(path)
	path = os.path.normpath(path)
	return path

