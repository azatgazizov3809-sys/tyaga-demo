"""Prepare static Python copy and a small, self-contained local-server archive."""
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
DIST = ROOT / 'dist'


def build():
    for name in ('engine.py','catalog_schema.py'):
        shutil.copyfile(ROOT/name, DIST/name)
    output = DIST/'tyaga-python-demo.zip'
    source = [ROOT/n for n in ('README.md','app.py','engine.py','catalog_schema.py','requirements.txt','build.py')]
    source += sorted((ROOT/'tests').glob('*.py'))
    source += sorted(p for p in DIST.rglob('*') if p.is_file() and p!=output and 'runtime' not in p.relative_to(DIST).parts)
    for name in ('index.html','styles.css','app.js','api.js','server-mode.js','python-worker.js','engine.py'):
        if not (DIST/name).is_file():raise RuntimeError('Missing '+name)
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in source:
            item=zipfile.ZipInfo('tyaga-python-demo/'+path.relative_to(ROOT).as_posix(),date_time=(2026,9,8,0,0,0))
            item.compress_type=zipfile.ZIP_DEFLATED
            item.external_attr=0o644 << 16
            archive.writestr(item,path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
    print(f'Prepared {len(source)} files; {output.stat().st_size:,} bytes')


if __name__=='__main__':build()
