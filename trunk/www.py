#!/usr/bin/python
# vim: ts=4 sw=4 expandtab
import BaseHTTPServer
import md5
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
    ('/news/', 'News'),
    ('/contact_support.htm', 'Contact'),
]

def _markdown2doc(source):
    class _PostProcessor(markdown.Postprocessor):
        def run(self, doc):
            self.doc = doc
            return doc
    postprocessor = _PostProcessor()
    md = markdown.Markdown()
    md.postprocessors.append(postprocessor)
    md.convert(source)
    return postprocessor.doc

def _resolve_url(url, parentpath):
    root = DOC_ROOT
    if not url.startswith('/'):
        if parentpath:
            root = os.path.dirname(parentpath)
            assert (root + os.sep).startswith(DOC_ROOT + os.sep)
        else:
            raise ValueError, 'Tried resolving relative URL: %s' % url

    urls = [
        url.rstrip('/') + '/index.htm',
        url
    ]
    for url in urls:
        path = os.path.join(root, url.lstrip('/'))
        if path.startswith(root + os.sep) and os.path.isfile(path):
            return path

def _get_nav(path):
    nav = []
    for url, name in NAV:
        navpath = _resolve_url(url, None)
        if navpath and navpath == path:
            nav.append('* <a class="active">%s</a>' % name)
        else:
            nav.append('* [%s](%s)' % (name, url))
    return markdown.markdown('\n'.join(nav))

def _remove_comments(source):
    return re.sub('<!--[^>]*-->', '', source)

def _gen_rss(source, title, link, desc):
    def removeblanktextnodes(node):
        for i in range(len(node.childNodes)-1, -1, -1):
            child = node.childNodes[i]
            if child.type == 'text':
                if not child.value:
                    node.removeChild(child)
            else:
                removeblanktextnodes(child)
    text = _remove_comments(source)
    doc = _markdown2doc(text)

    oldDocElement = doc.documentElement
    removeblanktextnodes(oldDocElement)

    rss = doc.createElement("rss")
    rss.setAttribute('version', '2.0')
    doc.appendChild(rss)

    channel = doc.createElement("channel")
    rss.appendChild(channel)
    if not title:
        raise ValueError, 'Missing @title= setting.'
    if not link:
        raise ValueError, 'Missing @link= setting.'
    if not desc:
        raise ValueError, 'Missing @desc= setting.'
    channel.appendChild(doc.createElement('title', textNode=title))
    channel.appendChild(doc.createElement('link', textNode=link))
    channel.appendChild(doc.createElement('desc', textNode=desc))

    guids = []

    item = None
    item_desc = None

    for child in oldDocElement.childNodes:
        if child.type != "element":
            if child.value.strip():
                raise ValueError, 'Expected outer-level element, not text.'
            continue

        if child.nodeName == 'h1':
            pass
        elif child.nodeName == "h2":
            link = len(child.childNodes) == 1 and child.childNodes[0]
            if not link or link.type != 'element' or link.nodeName != 'a':
                raise ValueError, 'Each heading must be a link.'

            titlenode = len(link.childNodes) == 1 and link.childNodes[0]
            if not titlenode or titlenode.type != 'text':
                raise ValueError, 'Each heading link must contain a ' + \
                                  'single text node.'
            heading = titlenode.value.strip()

            assert 'href' in link.attributes
            href = link.attribute_values['href']

            if href in guids:
                raise ValueError, "Duplicate link: %s" % href
            guids.append(href)

            item = doc.createElement("item")
            channel.appendChild(item)
            item.appendChild(doc.createElement("link", href))
            item.appendChild(doc.createElement("title", heading))
            item.appendChild(doc.createElement("guid", guid))
            item_desc = None

        elif child.nodeName in ["p", "ul", "blockquote"] :
            if not item_desc:
                # The first paragraph is <p><em>pubDate</em></p>
                em = len(child.childNodes) == 1 and child.childNodes[0]
                if not em or em.type != 'element'  or em.nodeName != 'em':
                    raise ValueError, 'The first paragraph must contain ' + \
                                      'only an <em>.'

                emchild = len(em.childNodes) == 1 and em.childNodes[0]
                if not emchild or emchild.type != 'text':
                    raise ValueError, "The first paragraph's em must " + \
                                      "contain only text."

                # TODO: Validate canonical date format.

                item.appendChild(doc.createElement('pubDate', emchild.value))
                item_desc = doc.createElement("description")
                item.appendChild(item_desc)
            else:
                cdata = doc.createCDATA(child.toxml())
                item_desc.appendChild(cdata)

        else:
            raise ValueError, 'Unsupported node type: %s' % child.nodeName
    return doc.toxml()

def _preprocess(path):
    def _include(match):
        # When including a file, update global settings and replace
        # with contents.
        includepath = _resolve_url(match.group(1).strip(), path)
        if not includepath:
            raise ValueError, 'Unmatched URL: %s' % match.group(1)
        settings, contents = _preprocess(includepath)
        childsettings.update(settings)
        return contents

    source = open(path).read()

    # Process includes.
    childsettings = {}
    source = re.sub('<!--@include ([^>]*)-->', _include, source)

    # The settings defined in the outer file will rule.
    settings = dict(re.findall(r'^@(\w+)=(.*)$', source, re.MULTILINE))
    source = _remove_comments(source)
    return settings, source

def _transform_file(path):
    source = open(path).read()
    if path.endswith('.css'):
        return 'text/css', source
    elif path.endswith('.gif'):
        return 'image/gif', source
    elif path.endswith('.png'):
        return 'image/png', source
    elif path.endswith('.rss'):
        settings, source = _preprocess(path)
        return 'text/xml', _gen_rss(source, settings.get('title'),
                                    settings.get('link'),
                                    settings.get('desc'))
    elif path.endswith('.htm') or path.endswith('.php') or \
         not '.' in os.path.basename(path):
        settings, source = _preprocess(path)
        page = markdown.markdown(source)
        if 'template' in settings:
            # TODO: encode keywords
            keywords = dict(settings)
            del keywords['template']
            keywords['body'] = page
            keywords['nav'] = _get_nav(path)
            template_path = os.path.join(DOC_ROOT, settings['template'])
            page = open(template_path).read() % keywords
        return 'text/html', page
    else:
        raise ValueError, 'Invalid file type: %s' % path

class _Handler(BaseHTTPServer.BaseHTTPRequestHandler):
    def do_GET(self):
        path = _resolve_url(self.path, None)
        if path:
            try:
                self._send_response(*_transform_file(path))
            except Exception:
                self.send_error(500, "TRACEBACK")
                raise
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

