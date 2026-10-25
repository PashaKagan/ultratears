# Building UltraTears from the source

The builder package (README.md) is this source plus the tools below, so it needs nothing installed. From a clone you
install the tools yourself; the build itself is the same command.

## What you need on your PC

| Tool | Version used | Notes |
|---|---|---|
| Windows 10/11 x64 | | |
| Python | **3.14** or newer (the build uses `compression.zstd`) | with the packages `lz4 capstone unicorn`: `python -m pip install lz4 capstone unicorn` (a venv is fine) |
| MSYS2, environment CLANG64 | clang/LLVM 23 | packages: `pacman -S mingw-w64-clang-x86_64-{clang,lld,ninja,SDL3,opus,libvpx,zstd,libiconv,vulkan-headers}`. Another folder with the same layout works too: set `ULTRS_CLANG64` to its `bin` |
| The shader translator `ultrs-shaders.exe` | | either `python tools/build_xlate.py` (needs the .NET 10 SDK and network access the first time; everything it fetches stays inside the clone) or copy `deps\shaders\` from the builder package |
| git | | for the clone |

The tools are looked up in this order (`tools/toolchain.py`): `deps\` in the clone (the builder package's layout),
then `ULTRS_CLANG64`, then `C:\msys64\clang64\bin`.

## Build

```
git clone <URL of this repository> UltraTears
cd UltraTears
python tools/setup.py
```

The dump is `game\` in the clone (`game\exefs`, `game\romfs`; README.md, "What you need"), or the folder given with
`--dump <folder>` (remembered, so later runs need only `python tools/setup.py`). `--cpus N` limits the logical processors the build uses (default: all, at low
priority so the PC stays usable). `--only <step>` runs one step.

The steps, what they write and how long they take on an 8-core PC:

| Step | Writes | Time | Runs again when |
|---|---|---|---|
| `check` | nothing: checks the tools, the SHA-256 of `exefs\main`, `subsdk0`, `sdk` (1.4.3) and refuses encrypted packages | seconds | always |
| `romfs` | `data\romfs\romfs.bin` + index: the RomFS folder in one file, read with 16 threads; its content hash is checked against 1.4.3 | ~4 min | the image is missing |
| `lift` | `data\exefs` (a copy of the code modules), `data\generated` (the game's code as C, ~0.9 GB) | ~2 min | the lifter changed |
| `compile` | `UltraTears.exe` (~0.4 GB) and `build\` (objects ~1.8 GB, debug symbols) | ~15 min (seconds when little changed) | sources changed (ninja) |
| `shaders` | `data\shaders` (SPIR-V of the 28,769 shaders) | ~5 min | the finder or the translator changed; new shaders only otherwise |
| `textures` | `data\textures` (BC7 / BC1 of every ASTC texture, ~7.4 GB) | ~7 min | textures not yet in the cache |
| `finish` | `ultratears.cfg` | seconds | always |

`data\`, `build\`, `userdata\`, `ultratears.cfg` and `UltraTears.exe` hold material made from your copy of the game:
they are in `.gitignore` and must never be shared.

## Keeping the game apart from the source (developers)

`python tools/setup.py` makes the clone itself the game folder. To keep the source folder free of anything made from
the game, unpack a builder package into another folder once (it brings the tools) and build there from your working
tree instead:

```
python tools/deploy.py --home D:\Games\UltraTears
```

It copies the source files (uncommitted edits too) into that folder and runs its `setup.py`; only what changed is
rebuilt. Run the game from there; development output (profiles, audits, frame dumps) goes to its `diag\`.

## Where the game looks for its data

`UltraTears.exe` reads `ultratears.cfg` next to it: the ExeFS (`exefs=`) and the `TOTK_*` variables for the RomFS,
shaders, texture cache and saves. Without that file it uses the development layout (`work\` of the developer's
machine). The RomFS may also be a plain folder (`TOTK_ROMFS=<folder>`): it is indexed when the game
starts, but loading reads many small files, which is slower; the packed image is the default.

## Troubleshooting

- `clang not found`: install MSYS2 CLANG64 with the packages above, or set `ULTRS_CLANG64`.
- `exefs\main is not the one of Tears of the Kingdom 1.4.3`: extract the ExeFS again with update 1.4.3 applied.
- `the RomFS is not the one of ... 1.4.3`: extract the RomFS again with the update applied, without mods.
- `encrypted packages are not accepted`: give the extracted folders, not an `.nsp` / `.xci` / `.nca`.
- The game starts with a black window or a Vulkan error: update the graphics driver (Vulkan 1.3 with
  `VK_EXT_shader_object` is needed).

## Making the builder package (maintainers)

```
python tools/build_xlate.py
git tag v<version>
python tools/deploy.py
python tools/make_package.py
python tools/public_tree.py --publish
```

The version has one source, the tag `v<x.y.z>` on the release commit (`tools/version.py`): the package, the public
commit and the exe take it from there. The exe writes it as the first line of its log and shows it in the file's
properties; between releases it reads like `0.1.0-3-gabc1234` (`git describe`).

It needs a complete build in the game folder (`tools/deploy.py`, default `..\release-test`) and a clean working tree,
and writes `dev-local\dist\UltraTears-builder-<version>-windows-x86_64.zip`: the public tree of HEAD, the part of MSYS2 CLANG64 the build
reads (measured from ninja's dependency records and the linker's trace), Python 3.14 with the packages above,
`ultrs-shaders.exe`, `setup.bat`, and the licenses of all of it.
