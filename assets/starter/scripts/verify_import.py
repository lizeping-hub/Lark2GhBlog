#!/usr/bin/env python3
"""Verify rendered article text, image placement, asset hashes, and block counts."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import ast
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET


def normalize(value):
    return re.sub(r'\s+', '', value)


def collapse(events):
    result = []
    for kind, value in events:
        if kind == 'text':
            value = normalize(value)
            if not value:
                continue
            if result and result[-1][0] == 'text':
                result[-1] = ('text', result[-1][1] + value)
                continue
        result.append((kind, value))
    return result


class ArticleParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.events = []
        self.images = []
        self.counts = {'table': 0, 'pre': 0}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            if self.depth:
                self.depth += 1
            elif 'post-content' in attrs.get('class', '').split():
                self.depth = 1
        if self.depth:
            if tag in self.counts:
                self.counts[tag] += 1
            if tag == 'img':
                src = attrs['src']
                self.images.append(src)
                self.events.append(('image', Path(unquote(urlparse(src).path)).name))

    def handle_endtag(self, tag):
        if tag == 'div' and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.events.append(('text', data))


def expected_events(node, image_names):
    if node.tag in ('title', 'colgroup'):
        return []
    if node.tag == 'img':
        return [('image', image_names[node.attrib['src']])]
    events = [('text', node.text or '')]
    for child in node:
        events.extend(expected_events(child, image_names))
        events.append(('text', child.tail or ''))
    return events


def main():
    args = argparse.ArgumentParser()
    args.add_argument('audit_dir', type=Path, nargs='?')
    args.add_argument('--slug')
    options = args.parse_args()
    audit = options.audit_dir
    assert not audit or options.slug, 'Provide --slug when using an audit snapshot'
    site = Path(__file__).resolve().parents[1]
    manifest = json.loads((site / 'content-manifest.json').read_text())
    selected = [p for p in manifest if not options.slug or p['slug'] == options.slug]
    if options.slug and not selected:
        raise ValueError('Article not found in manifest')
    config = (site / 'hugo.toml').read_text()
    base = urlparse(ast.literal_eval(next(line.split('=', 1)[1].strip() for line in config.splitlines() if re.match(r'^baseURL\s*=', line))))
    for post in selected:
        rendered = site / 'public' / 'posts' / post['slug'] / 'index.html'
        parser = ArticleParser()
        parser.feed(rendered.read_text())
        if audit:
            document = json.loads((audit / 'document.json').read_text())['data']['document']
            root = ET.fromstring('<root>' + document['content'] + '</root>')
            assert len(list(root.iter('img'))) == len(post['images'])
            image_names = {node.attrib['src']: image['file'] for node, image in zip(root.iter('img'), post['images'])}
            expected = collapse(expected_events(root, image_names))
            actual = collapse(parser.events)
            if expected != actual:
                raise AssertionError(f'Article content or image placement differs: {post["slug"]}')
        assert parser.counts == {'table': post['tables'], 'pre': post['code_blocks']}
        assert len(parser.images) == len(post['images'])
        for url, image in zip(parser.images, post['images']):
            parsed = urlparse(url)
            assert not parsed.netloc or parsed.netloc == base.netloc, url
            path = site / 'public' / (unquote(parsed.path).removeprefix(base.path) if parsed.path.startswith(base.path) else f'posts/{post["slug"]}/' + Path(parsed.path).name)
            assert parsed.path.startswith(base.path) or not parsed.path.startswith('/'), url
            assert hashlib.sha256(path.read_bytes()).hexdigest() == image['sha256']
        detail = 'full text and image placement match; ' if audit else ''
        print(f'PASS {post["slug"]}: {detail}{len(parser.images)} images; {post["tables"]} table; {post["code_blocks"]} code blocks')


if __name__ == '__main__':
    main()
