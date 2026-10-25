"""Build UltraTears from the player's own dump, in one command: every step is checked and can be resumed.

usage: python tools/setup.py [--dump <folder with exefs\\ and romfs\\>] [--cpus N] [--only <step>]
The dump is game\\ in this folder unless --dump names another (remembered for later runs); run it again to resume, or to
rebuild what changed after an update of the port.
The dump: the ExeFS and RomFS of The Legend of Zelda: Tears of the Kingdom with update 1.4.3 applied, as plain files,
extracted by the player from their own console. Encrypted packages (.nsp, .xci, .nca, ...) are refused: the port
decrypts nothing and reads no keys (README.md, Legal). Optional: <dump>\\sysdata\\fonts\\*.bfttf, the console's shared fonts.

Steps (data\\ holds everything made from the dump; it never leaves this PC):
  check     the tools, the dump's version (SHA-256 of the code modules) and its files
  romfs     the RomFS folder packed into one image, data\\romfs (its content hash checked against 1.4.3)
  lift      the game's code translated to C, data\\generated
  compile   the C compiled and linked: UltraTears.exe (objects in build\\)
  shaders   every shader of the game found and translated to SPIR-V, data\\shaders
  textures  the ASTC textures re-encoded for PC graphics cards (BC7 / BC1), data\\textures
  finish    ultratears.cfg
"""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tools'))
import toolchain  # noqa: E402

DATA = ROOT / 'data'
STATE = DATA / 'setup.json'
# The version the port is made for: TOTK 1.4.3 (facts about the player's files, no game data).
EXEFS = {
    'main': 'e84a90d551fed0824b4b74933b9c6d043c458521363a7cea58b2faca1822dc9e',
    'subsdk0': '767c35bcd7d23e78f9063c69b638290b8b83f91e839beb10799e6576960179b1',
    'sdk': '1d187f29784cd0af46e9e123fc2a62c77b3b07c5a39c8633d90d6c80de64e4ad',
}
ROMFS_FILES = 304243
ROMFS_BYTES = 17026725026
ROMFS_CONTENT = 'b2a2e966a06158e098c03e564f77fd72809bc57275f04eb0725bcde14d522056'
ENCRYPTED = ('.nsp', '.nsz', '.xci', '.xcz', '.nca', '.ncz')


class Fail(Exception):
    pass


def say(msg):
    print(msg, flush=True)


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def tree_hash(paths):
    """A stamp of source files: when it changes, the step that uses them runs again."""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(str(p.relative_to(ROOT)).encode() + b'\0' + p.read_bytes())
    return h.hexdigest()[:16]


def run(cmd, what):
    t0 = time.time()
    rc = subprocess.run([str(c) for c in cmd], cwd=ROOT).returncode
    if rc:
        raise Fail(f'{what} failed (exit code {rc}); the lines above say why')
    return time.time() - t0


def load_state():
    try:
        return json.loads(STATE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state):
    DATA.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1))


# ---------------------------------------------------------------- steps
def step_check(dump, state):
    if sys.version_info < (3, 14):
        raise Fail(f'Python 3.14 or newer is needed (this is {sys.version.split()[0]})')
    for mod in ('lz4', 'capstone', 'unicorn'):
        try:
            __import__(mod)
        except ImportError:
            raise Fail(f'the Python package {mod} is missing: python -m pip install lz4 capstone unicorn')
    toolchain.env()
    if toolchain.XLATE is None:
        raise Fail('the shader translator ultrs-shaders.exe is missing: build it with python tools/build_xlate.py '
                   '(needs the .NET 10 SDK) or take deps\\shaders from the builder package')
    if packed(state) and all(ok_module(DATA / 'exefs' / n, h) for n, h in EXEFS.items()):
        return 'Tears of the Kingdom 1.4.3, already taken in (data\\exefs, data\\romfs): the dump is no longer needed'
    if not dump.is_dir():
        raise Fail(f'{dump} does not exist: put your extracted game there (game\\exefs and game\\romfs), '
                   'or give its folder with --dump')
    for p in list(dump.iterdir()) + list((dump / 'exefs').glob('*') if (dump / 'exefs').is_dir() else []):
        if p.suffix.lower() in ENCRYPTED:
            raise Fail(f'{p.name}: encrypted packages are not accepted. Give the extracted exefs and romfs folders '
                       '(this project decrypts nothing and reads no keys)')
    exefs, romfs = dump / 'exefs', dump / 'romfs'
    if not exefs.is_dir() or not romfs.is_dir():
        raise Fail(f'{dump} must hold the folders exefs and romfs (extracted, as plain files)')
    for name, want in EXEFS.items():
        f = exefs / name
        if not f.is_file():
            raise Fail(f'exefs\\{name} is missing')
        if sha256(f) != want:
            raise Fail(f'exefs\\{name} is not the one of Tears of the Kingdom 1.4.3. Extract the ExeFS again with '
                       'update 1.4.3 applied (the base game 1.0.0 and other updates are not supported)')
    if not (romfs / 'Pack/ZsDic.pack.zs').is_file():
        raise Fail(f'{romfs} does not look like the RomFS of Tears of the Kingdom (Pack\\ZsDic.pack.zs is missing)')
    return 'Tears of the Kingdom 1.4.3 (the code modules match)'


def packed(state):
    out = DATA / 'romfs'
    return state.get('romfs') == ROMFS_CONTENT and (out / 'romfs.bin').is_file() and (out / 'runtime-index.bin').is_file()


def ok_module(path, want):
    return path.is_file() and sha256(path) == want


def step_romfs(dump, state, cpus):
    out = DATA / 'romfs'
    if packed(state):
        return 'already packed'
    from pack_romfs import pack
    n, size, content = pack(dump / 'romfs', out, threads=16, progress=say)
    if n != ROMFS_FILES or size < ROMFS_BYTES or content != ROMFS_CONTENT:
        raise Fail(f'the RomFS is not the one of Tears of the Kingdom 1.4.3 ({n} files, expected {ROMFS_FILES}; '
                   'content differs). Extract the RomFS again with update 1.4.3 applied; mods do not go here')
    state['romfs'] = content
    return f'{n} files, {size / 2**30:.1f} GiB, content verified'


def step_lift(dump, state, cpus):
    exefs = DATA / 'exefs'
    exefs.mkdir(parents=True, exist_ok=True)
    for name in list(EXEFS) + ['main.npdm']:   # the code modules are taken in, so the dump can go after the build
        src = dump / 'exefs' / name
        if src.is_file() and (not (exefs / name).is_file() or (exefs / name).stat().st_size != src.stat().st_size):
            shutil.copyfile(src, exefs / name)
    stamp = tree_hash(list((ROOT / 'tools/lifter').glob('*.py')) + [ROOT / 'tools/gen_game.py'])
    if state.get('lift') == stamp and (DATA / 'generated/main').is_dir():
        return 'up to date'
    run([sys.executable, 'tools/gen_game.py', exefs, DATA / 'generated'], 'translating the code')
    state['lift'] = stamp
    return 'done'


def step_compile(dump, state, cpus):
    run([sys.executable, 'tools/build_game.py', '--generated', DATA / 'generated', '--target', 'ultratears', '--cpus', cpus],
        'compiling')
    return 'UltraTears.exe'


def step_shaders(dump, state, cpus):
    out = DATA / 'shaders'
    stamp = tree_hash([ROOT / 'tools/shaders/inventory.py', ROOT / 'tools/export_shaders.py'])
    if state.get('shaders-export') != stamp or not (out / 'jobs.jsonl').is_file():
        run([sys.executable, 'tools/export_shaders.py', DATA / 'romfs', out, DATA / 'exefs'], 'finding the shaders')
        state['shaders-export'] = stamp
        save_state(state)
    xlate = sha256(toolchain.XLATE)[:16]
    new_only = ['--new-only'] if state.get('shaders-xlate') == xlate else []
    run([sys.executable, 'tools/run_ryujinx_xlate.py', out, '--workers', min(cpus, 32), '--quiet'] + new_only,
        'translating the shaders')
    state['shaders-xlate'] = xlate
    return 'done'


def step_textures(dump, state, cpus):
    run([sys.executable, 'tools/bc7_build.py', '--romfs', DATA / 'romfs', '--cache', DATA / 'textures', '--threads',
         min(cpus, 64)], 're-encoding the textures')
    return 'done'


def step_finish(dump, state, cpus):
    fonts = dump / 'sysdata/fonts'
    lines = ['# Written by tools/setup.py: where UltraTears finds its data (relative to this folder).',
             'exefs=data/exefs', 'romfs=data/romfs', 'shaders=data/shaders/ryujinx', 'textures=data/textures',
             'saves=userdata']
    if fonts.is_dir() and list(fonts.glob('*.bfttf')):
        shutil.copytree(fonts, DATA / 'fonts', dirs_exist_ok=True)
    lines.append('fonts=data/fonts')
    (ROOT / 'ultratears.cfg').write_text('\n'.join(lines) + '\n')
    (ROOT / 'build/UltraTears.exe').unlink(missing_ok=True)   # where builds before 0.1.0 linked it
    if (dump / 'romfs').is_dir():
        say(f'  The game reads data\\romfs and data\\exefs now: {dump} (16 GB) is no longer needed.')
        if sys.stdin.isatty() and dump.resolve() == (ROOT / 'game').resolve():
            answer = input('  Delete game\\exefs and game\\romfs to free 16 GB? [y/N] ').strip().lower()
            if answer in ('y', 'yes', 'д', 'да'):
                for sub in ('exefs', 'romfs'):
                    shutil.rmtree(dump / sub, ignore_errors=True)
                say('  deleted')
    return 'ultratears.cfg ready'


STEPS = [('check', step_check), ('romfs', step_romfs), ('lift', step_lift), ('compile', step_compile),
         ('shaders', step_shaders), ('textures', step_textures), ('finish', step_finish)]


def main():
    ap = argparse.ArgumentParser(description='Build UltraTears from your own dump of the game.')
    ap.add_argument('--dump', type=pathlib.Path,
                    help='the folder with exefs\\ and romfs\\ (default: game\\ here; remembered for later runs)')
    ap.add_argument('--cpus', type=int, default=os.cpu_count() or 4,
                    help='logical CPUs the build may use (default: all; it runs at low priority)')
    ap.add_argument('--only', choices=[s for s, _ in STEPS], help='run one step only')
    a = ap.parse_args()
    state = load_state()
    if a.dump:
        state['dump'] = str(a.dump.resolve())
    if not state.get('dump'):
        state['dump'] = str(ROOT / 'game')
    dump = pathlib.Path(state['dump'])
    say(f'UltraTears setup: dump {dump}, {a.cpus} CPUs')
    t_all = time.time()
    for i, (name, fn) in enumerate(STEPS, 1):
        if a.only and name != a.only and name != 'check':
            continue
        say(f'[{i}/{len(STEPS)}] {name}')
        t0 = time.time()
        try:
            result = fn(dump, state) if name == 'check' else fn(dump, state, a.cpus)
        except Fail as e:
            say(f'\nERROR in step "{name}": {e}')
            save_state(state)
            sys.exit(1)
        save_state(state)
        say(f'  {result or "ok"} ({time.time() - t0:.0f} s)')
    say(f'\nDone in {(time.time() - t_all) / 60:.0f} min. Start the game: UltraTears.exe in {ROOT}')


if __name__ == '__main__':
    main()
