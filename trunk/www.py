#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import BaseHTTPServer
import re
import os
import sys

import markdown

DOC_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'www')
TEMPLATE_PATH = os.path.join(DOC_ROOT, '__template__')

NAV = [
    ('/', 'Home'),
    ('/download.htm', 'Download'),
    ('/online_lint.php', 'The Online Lint'),
    ('/docs/', 'Documentation'),
    ('/news.php', 'News'),
    ('/contact_support.htm', 'Contact'),
]

def _resolve_url(url):
    urls = [
        url.rstrip('/') + '/index.htm',
        url
    ]
    for url in urls:
        path = os.path.join(DOC_ROOT, url.lstrip('/'))
        if path.startswith(DOC_ROOT + os.sep) and os.path.isfile(path):
            return path

def _get_nav(path):
    nav = []
    for url, name in NAV:
        navpath = _resolve_url(url)
        if navpath and navpath == path:
            nav.append('* <a class="active">%s</a>' % name)
        else:
            nav.append('* [%s](%s)' % (name, url))
    return markdown.markdown('\n'.join(nav))

def _transform_file(path):
    source = open(path).read()
    if path.endswith('.css'):
        return 'text/css', source
    elif path.endswith('.gif'):
        return 'image/gif', source
    elif path.endswith('.png'):
        return 'image/png', source
    elif path.endswith('.htm') or path.endswith('.php'):
        body = markdown.markdown(source)
        keywords = re.findall(r'^@(\w+)=(.*)$', source, re.MULTILINE)
        # TODO: encode
        keywords = dict(keywords)
        keywords['body'] = body
        keywords['nav'] = _get_nav(path)
        page = open(TEMPLATE_PATH).read() % keywords
        return 'text/html', page
    else:
        raise ValueError, 'Invalid file type: %s' % path

class _Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        path = _resolve_url(self.path)
        if path:
            self._send_response(*_transform_file(path))
        else:
            self.send_error(404, "File not found")

    def _send_response(self, contenttype, content):
        self.send_response(200)
        self.send_header("Content-type", contenttype)
        self.send_header("Content-length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def runserver():
    server_address = ('', 8000)
    httpd = BaseHTTPServer.HTTPServer(server_address, _Handler)
    httpd.serve_forever()

def main(action=''):
    if action == 'server':
        runserver()
        return
    # TODO: Implement 'build'.
    print >>sys.stderr, """\
Usage: www.py [server|build]

server     runs a test server on localhost
build      generates static HTML files from the markup
"""
    sys.exit(1)

if __name__ == '__main__':
    main(*sys.argv[1:])

