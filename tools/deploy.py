"""Development: bring the game folder (default ..\\release-test, the player's layout from the builder package) up to this
working tree, then build there with its own setup.py, as a player updating the port would.

usage: python tools/deploy.py [--home ..\\release-test] [--cpus 8] [--no-setup]
  - the source: every file of the public tree (tools/public_tree.py: what git tracks, without the internal notes), as
    it is in this working tree (uncommitted edits too), is copied where it differs; files a previous deploy put there
    and the tree no longer has are removed (the list is kept in <home>\\deploy-files.txt);
  - the shader translator: dev-local\\build\\shaders\\ultrs-shaders.exe, if built (tools/build_xlate.py), replaces
    <home>\\deps\\shaders\\ultrs-shaders.exe when it differs;
  - then <home>\\deps\\python\\python.exe tools\\setup.py --cpus N in <home> (incremental: seconds to minutes).
Never touches the game folder's game\\, data\\, build\\, userdata\\, diag\\ or the rest of deps\\. The source folder holds
no game data at all: everything made from the game lives in the game folder.
"""
import argparse
import filecmp
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import public_tree  # noqa: E402
import version  # noqa: E402

KEEP = {'game', 'data', 'build', 'userdata', 'diag', 'deps'}   # the game folder's own: never written by a deploy
# made by tools/make_package.py or setup.py, not source files: a deploy leaves them
PACKAGE_OWN = {'setup.bat', 'VERSION.txt', 'THIRD-PARTY-NOTICES.md', 'licenses', 'ultratears.cfg', 'UltraTears.exe',
               'UltraTears.pdb', 'deploy-files.txt'}


def public_files():
    """Paths of the public tree that exist in the working tree (tracked files, PRIVATE left out)."""
    out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], check=True, capture_output=True).stdout
    files = [f for f in out.decode('utf-8').split('\0') if f]
    return [f for f in files if f.split('/')[0] not in public_tree.PRIVATE and (ROOT / f).is_file()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--home', type=pathlib.Path, default=ROOT.parent / 'release-test')
    ap.add_argument('--cpus', type=int, default=8)
    ap.add_argument('--no-setup', action='store_true')
    a = ap.parse_args()
    home = a.home.resolve()
    if not (home / 'deps/python/python.exe').is_file():
        sys.exit(f'{home} is not a game folder: unpack a builder package there first (deps\\python is missing)')
    files = public_files()
    if any(f.split('/')[0] in KEEP for f in files):
        sys.exit('a tracked path would overwrite the game folder\'s own data: refusing')
    changed = 0
    for f in files:
        src, dst = ROOT / f, home / f
        if dst.is_file() and filecmp.cmp(src, dst, shallow=False):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        changed += 1
    listing = home / 'deploy-files.txt'
    if listing.is_file():
        old = set(listing.read_text(encoding='utf-8').splitlines())
    else:   # the first deploy over an unpacked package: its source files are the old ones
        old = {p.relative_to(home).as_posix() for p in home.rglob('*') if p.is_file() and
               p.relative_to(home).parts[0] not in KEEP | PACKAGE_OWN}
    removed = 0
    for f in sorted(old - set(files)):
        p = home / f
        if f.split('/')[0] not in KEEP | PACKAGE_OWN and p.is_file():   # only source files
            p.unlink()
            removed += 1
            for d in p.parents:   # folders left empty go too
                if d == home or any(d.iterdir()):
                    break
                d.rmdir()
    listing.write_text('\n'.join(files) + '\n', encoding='utf-8')
    v_txt = version.version_txt(*version.current())   # the game folder has no .git: the version goes with the files
    if not (home / 'VERSION.txt').is_file() or (home / 'VERSION.txt').read_text(encoding='utf-8') != v_txt:
        (home / 'VERSION.txt').write_text(v_txt, encoding='utf-8')
    xlate = ROOT / 'dev-local/build/shaders/ultrs-shaders.exe'
    dst = home / 'deps/shaders/ultrs-shaders.exe'
    if xlate.is_file() and not (dst.is_file() and filecmp.cmp(xlate, dst, shallow=False)):
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(xlate, dst)
        changed += 1
    print(f'deploy -> {home}: {changed} files updated, {removed} removed', flush=True)
    if a.no_setup:
        return
    rc = subprocess.run([str(home / 'deps/python/python.exe'), str(home / 'tools/setup.py'), '--cpus', str(a.cpus)],
                        cwd=home, stdin=subprocess.DEVNULL, env=dict(os.environ, PYTHONNOUSERSITE='1')).returncode
    sys.exit(rc)


if __name__ == '__main__':
    main()
