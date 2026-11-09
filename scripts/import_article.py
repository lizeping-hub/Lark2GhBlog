#!/usr/bin/env python3
"""Convert a Feishu document to a Hugo page bundle.

Input files and API responses stay outside the public repository. Re-run only
after fetching the approved source documents and their media with lark-cli.
"""
import argparse
import copy
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from datetime import date
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

def escape(text):
    return re.sub(r'([\\`*_{}\[\]|#!])', r'\\\1', html.escape(text, quote=False))


def plain(node):
    out = node.text or ''
    for child in node:
        out += ('\n' if child.tag == 'br' else plain(child)) + (child.tail or '')
    return out


def inline(node):
    out = escape(node.text or '')
    for child in node:
        value = inline(child)
        if child.tag == 'b':
            value = '<strong>' + value + '</strong>'
        elif child.tag == 'em':
            value = '<em>' + value + '</em>'
        elif child.tag == 'code':
            value = '<code>' + html.escape(plain(child)) + '</code>'
        elif child.tag == 'a':
            href = child.attrib['href']
            if urlsplit(href).scheme.lower() not in ('https', 'http', 'mailto') or any(ord(c) < 32 for c in href):
                raise ValueError('Unsupported link scheme')
            value = '<a href="' + html.escape(child.attrib['href'], quote=True) + '">' + value + '</a>'
        elif child.tag == 'br':
            value = '<br>'
        elif child.tag not in ('p', 'li'):
            raise ValueError(f'Unsupported inline element: {child.tag}')
        out += value + escape(child.tail or '')
    return out


def block(node, image_names):
    tag = node.tag
    if tag == 'title':
        return ''
    if tag == 'p':
        return inline(node)
    if re.fullmatch(r'h[1-6]', tag):
        return '#' * int(tag[1]) + ' ' + inline(node)
    if tag == 'img':
        return f'![]({image_names[node.attrib["src"]]})'
    if tag == 'pre':
        code = plain(node)
        fence = '`' * max(3, max((len(m) + 1 for m in re.findall(r'`+', code)), default=3))
        return fence + 'text\n' + code + '\n' + fence
    if tag in ('ul', 'ol'):
        rows = []
        for i, li in enumerate(node, 1):
            assert li.tag == 'li'
            prefix = f'{i}. ' if tag == 'ol' else '- '
            content = ET.Element('li')
            content.text = li.text
            nested = []
            for child in li:
                if child.tag in ('ul', 'ol'):
                    nested.append(child)
                else:
                    content.append(copy.deepcopy(child))
            rows.append(prefix + inline(content))
            for child in nested:
                rows.extend(' ' * len(prefix) + line for line in block(child, image_names).splitlines())
        return '\n'.join(rows)
    if tag == 'table':
        rows = []
        for tr in node.iter('tr'):
            cells = []
            for td in tr:
                cells.append('<br>'.join(inline(p) for p in td if p.tag == 'p'))
            rows.append('| ' + ' | '.join(cells) + ' |')
        assert rows
        columns = len(next(node.iter('tr')))
        rows.insert(1, '| ' + ' | '.join(['---'] * columns) + ' |')
        return '\n'.join(rows)
    if tag == 'hr':
        return '---'
    raise ValueError(f'Unsupported block: {tag}')


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout


def main():
    p = argparse.ArgumentParser(description='Import one Feishu or Lark document; never pushes.')
    p.add_argument('url')
    p.add_argument('--site', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True, help='New local directory outside checkout')
    a = p.parse_args()
    url = urlsplit(a.url)
    host = url.hostname or ''
    if url.scheme != 'https' or url.netloc != host or not any(host.endswith('.' + h) or host == h for h in ('feishu.cn', 'larksuite.com')) or not re.fullmatch(r'/(wiki|docx)/[A-Za-z0-9]+/?', url.path):
        p.error('Expected a Feishu/Lark HTTPS wiki or docx URL')
    canonical = f'https://{host}{url.path.rstrip("/")}'
    site, audit = a.site.resolve(), a.audit.resolve()
    if audit == site or site in audit.parents:
        p.error('Audit must stay outside the repository')
    manifest_path = site / 'content-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    audit.mkdir(parents=True, exist_ok=False)
    snapshot = run('lark-cli', 'docs', '+fetch', '--as', 'user', '--doc', canonical, '--detail', 'full')
    (audit / 'document.json').write_text(snapshot, encoding='utf-8')
    response = json.loads(snapshot)
    if response.get('ok') is not True:
        raise ValueError('Document read did not succeed; inspect the private snapshot')
    document = response['data']['document']
    if document.get('tips'):
        raise ValueError('Document reports fallback or unsupported content; inspect private snapshot')
    root = ET.fromstring('<root>' + document['content'] + '</root>')
    doc_id = document['document_id']
    identity = hashlib.sha256(doc_id.encode()).hexdigest()
    old = next((m for m in manifest if m.get('document_key') == identity or m['source_url'] == canonical), None)
    slug = old['slug'] if old else 'article-' + identity[:16]
    if not re.fullmatch('[a-z0-9-]+', slug):
        raise ValueError('Invalid manifest slug')
    folder = site / 'content' / 'posts' / slug
    if folder.exists() and not old:
        raise ValueError('Article path occupied')
    title_node = root.find('title')
    if title_node is None or not plain(title_node).strip():
        raise ValueError('Document title missing')
    title = plain(title_node)
    with tempfile.TemporaryDirectory(dir=audit) as temp:
        stage = Path(temp)
        names, images = {}, []
        for node in root.iter('img'):
            token = node.attrib['src']
            if token in names:
                images.append(dict(next(i for i in images if i['file'] == names[token])))
                continue
            if not re.fullmatch('[A-Za-z0-9_-]+', token):
                raise ValueError('Unsupported media reference')
            stem = f'image-{len(names)+1:02d}'
            run('lark-cli', 'docs', '+media-download', '--as', 'user', '--token', token, '--output', stem, cwd=stage)
            matches = list(stage.glob(stem + '.*'))
            if len(matches) != 1 or matches[0].suffix.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.webp', '.avif') or not matches[0].stat().st_size:
                raise ValueError('No supported raster image downloaded')
            file = matches[0]
            names[token] = file.name
            images.append({'file': file.name, 'sha256': hashlib.sha256(file.read_bytes()).hexdigest()})
        body = '\n\n'.join(block(n, names) for n in root if n.tag != 'title')
        if '{{' + '<' in body or '{{' + '%' in body:
            raise ValueError('Article contains Hugo shortcode syntax; escape and verify before publishing')
        today = date.today().isoformat()
        metadata = {'title': title, 'summary': next((escape(plain(n)) for n in root if n.tag == 'p' and plain(n).strip()), ''), 'sourceURL': canonical, 'importedAt': old.get('imported_at', today) if old else today, 'weight': old.get('weight', manifest.index(old) + 1) if old else len(manifest) + 1}
        if images:
            metadata['cover'] = {'image': images[0]['file'], 'hiddenInSingle': True}
        entry = {'slug': slug, 'document_key': identity, 'title': title, 'source_url': canonical, 'revision': document['revision_id'], 'imported_at': metadata['importedAt'], 'weight': metadata['weight'], 'images': images, 'tables': len(list(root.iter('table'))), 'code_blocks': len(list(root.iter('pre')))}
        (stage / 'index.md').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n\n' + body.rstrip() + '\n', encoding='utf-8')
        folder.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stage / 'index.md', folder)
        for name in set(names.values()):
            shutil.copy2(stage / name, folder)
        if old:
            for name in {i['file'] for i in old['images']} - set(names.values()):
                if re.fullmatch(r'image-\d+\.(png|jpg|jpeg|gif|webp|avif)', name, re.I):
                    (folder / name).unlink(missing_ok=True)
            manifest[manifest.index(old)] = entry
        else:
            manifest.append(entry)
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(entry, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f'{exc.cmd[0]} failed ({exc.returncode}); inspect credentials, access, and CLI help without exposing tokens') from None
