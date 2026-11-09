import argparse
import json
from pathlib import Path
import re
import shutil

p = argparse.ArgumentParser(description='Create a local Hugo starter; no network or GitHub mutations')
p.add_argument('path', type=Path)
p.add_argument('--owner', required=True)
p.add_argument('--repo', default='blog')
p.add_argument('--author', required=True)
a = p.parse_args()
for v in (a.owner, a.repo):
    if not re.fullmatch('[A-Za-z0-9][A-Za-z0-9-]{0,38}', v):
        p.error('Use a GitHub owner and repository name with letters, numbers or hyphens')
shutil.copytree(Path(__file__).resolve().parents[1] / 'assets/starter', a.path)
f = a.path / 'hugo.toml'
s = f.read_text().replace("'__BLOG_AUTHOR__ · 文章'", json.dumps(a.author + ' · 文章', ensure_ascii=False)).replace("'__BLOG_AUTHOR__'", json.dumps(a.author, ensure_ascii=False))
for old, new in {'__BLOG_URL__': f'https://{a.owner.lower()}.github.io/{a.repo}/', '__OWNER_SITE__': f'https://{a.owner.lower()}.github.io/', '__OWNER_GITHUB__': f'https://github.com/{a.owner}'}.items():
    s = s.replace(old, new)
f.write_text(s, encoding='utf-8')
print(a.path.resolve())
