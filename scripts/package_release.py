"""Build a clean installable archive, without local data or caches."""
import json
import os
import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[1]
version = json.loads((root / 'custom_components/family_quests/manifest.json').read_text())['version']
if not re.fullmatch(r'\d+\.\d+\.\d+', version):
    raise SystemExit('Expected a stable semantic version')
ref = os.environ.get('GITHUB_REF', '')
if ref.startswith('refs/tags/') and ref != 'refs/tags/v' + version:
    raise SystemExit('Tag and manifest version differ')
out = root / 'dist'
out.mkdir(exist_ok=True)
with ZipFile(out / f'Rodinne-ulohy-{version}.zip', 'w', ZIP_DEFLATED) as z:
    for folder in ['custom_components', 'examples', 'docs']:
        for f in sorted((root / folder).rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts and f.suffix != '.pyc':
                z.write(f, f.relative_to(root))
    for name in ['README.md', 'LICENSE', 'CHANGELOG.md', 'hacs.json']:
        z.write(root / name, name)
print(out / f'Rodinne-ulohy-{version}.zip')
