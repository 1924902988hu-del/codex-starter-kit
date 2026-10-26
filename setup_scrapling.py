"""Opt-in, isolated Scrapling runtime. Never touches system Python or browsers."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import venv

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--home', type=Path, default=Path.home())
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    target = a.home.absolute() / '.local/share/codex-starter-kit/scrapling'
    for node in [target, *target.parents]:
        if node.is_symlink():
            p.error('Refusing symlink path: ' + str(node))
    if target.exists():
        p.error('Runtime already exists; retain it. Inspect/version-check before changing it.')
    print('Create isolated runtime:', target)
    print('Download scrapling[fetchers]==0.5 and its dependencies from PyPI. No browser installation.')
    if not a.apply:
        return
    if sys.version_info < (3, 10):
        p.error('Python 3.10+ required')
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        venv.EnvBuilder(with_pip=True).create(target)
        python = target / ('Scripts/python.exe' if sys.platform == 'win32' else 'bin/python')
        subprocess.run([str(python), '-m', 'pip', 'install', 'scrapling[fetchers]==0.5'], check=True)
        subprocess.run([str(python), '-c', 'from scrapling.fetchers import Fetcher; import importlib.metadata; assert importlib.metadata.version("scrapling")=="0.5"; print("Runtime import OK")'], check=True)
        (target / 'starter-runtime.json').write_text(json.dumps({'package':'scrapling','version':'0.5'}))
    except BaseException:
        if target.exists():
            shutil.rmtree(target)
        raise
if __name__ == '__main__':
    main()
