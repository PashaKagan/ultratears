# UltraTears

**UltraTears** is an unofficial native PC port of *The Legend of Zelda: Tears of the Kingdom* (Nintendo Switch,
version 1.4.3) for Windows, and Steam Deck through Proton. It is not an emulator: the game's program code is translated
ahead of time (static recompilation, ARM64 → C → x86-64), and the Switch system and its NVN graphics API are replaced
by the port's own implementations on Windows and Vulkan. Shaders and textures are converted for PC graphics cards when
the game is built, not while you play.

> **This repository contains no game code, no game assets, no Nintendo SDK code, no firmware and no keys, and it does
> not tell you where to get any of them.** It does nothing without a copy of the game you dumped yourself from your own
> console. Everything made from the game (the translated code, the compiled game, shaders, textures) is made on your
> PC from your files and must stay there: do not share it, and do not open issues asking for it.
>
> UltraTears is not affiliated with or endorsed by Nintendo. *The Legend of Zelda* and *Tears of the Kingdom* are
> trademarks of Nintendo; the name is used only to say which game this works with.

Русская версия: [README.ru.md](README.ru.md).

## Status

Early. Measured on the developer's PC (Windows 10, Ryzen, 16 threads, GeForce RTX 3060):

| What | Result |
|---|---|
| Title screen, new game, prologue, Great Sky Island | plays |
| Frame rate | the game's own 30 fps, with drops while new shaders compile (being fixed: shaders compiled ahead) |
| Steam Deck | through Proton, being tested |
| Other PCs and graphics cards | not tested yet |

Known issues: hitches the first time an effect or place is seen (shader compilation); the controller layout follows the
Switch (A is the right face button); no settings menu yet (window size, resolution, upscaling come later).

## The game is never downloaded

There is no prebuilt game to download, and there never will be: the game is translated and compiled **on your PC, from
your files**. What you download is this source code, alone or as the **builder package**: the same source plus the
free tools the build needs, so you install nothing.

## What you need

- **Your own extracted copy of Tears of the Kingdom with update 1.4.3 applied**: the ExeFS and the RomFS as plain
  files, which go into the `game` folder of UltraTears:
  ```
  UltraTears\game\
    exefs\    main, subsdk0, sdk, main.npdm, ...
    romfs\    Actor\, Pack\, Shader\, ... (about 304,000 files, 16 GB)
  ```
  You make them yourself, from your own console and your own copy of the game, with the update installed; this
  project does not provide or point to tools for that. The build checks that it is exactly version 1.4.3. Encrypted packages (`.nsp`,
  `.xci`, `.nca`, ...) are refused: this project decrypts nothing and reads no keys.
- Windows 10/11 x64; a processor with AVX2 (Intel Haswell / AMD Ryzen or newer).
- A graphics card with a current Vulkan 1.3 driver that has `VK_EXT_shader_object` (recent NVIDIA, AMD and Intel
  drivers; Steam Deck's Mesa).
- About **32 GB** free where you unzip the builder (the build makes about 30 GB: the packed RomFS 16 GB, textures
  7.4 GB, shaders 2.4 GB, the compiled game and its intermediate files 4 GB), besides the 16 GB of your game in `game\`,
  whose `romfs` you may delete after the build. 16 GB of RAM.

## Getting started (builder package)

1. **Download** `UltraTears-builder-<version>-windows-x86_64.zip` from the **Releases** page and unzip it into a folder
   of its own, for example `D:\Games\UltraTears`.
2. **Put your game in**: copy your extracted `exefs` and `romfs` folders into `game\` there (a dump kept elsewhere
   also works: drag its folder onto `setup.bat`).
3. **Build**: run **`setup.bat`**. It checks the dump, then builds, showing each step:

   | Step | What it does | Time (8-core PC) |
   |---|---|---|
   | check | the version of your dump | seconds |
   | romfs | the RomFS packed into one file (`data\romfs`; reading 304,000 small files while playing would stall) | ~4 min |
   | lift | the game's code translated to C | ~2 min |
   | compile | the C compiled into `UltraTears.exe` | ~15 min |
   | shaders | every shader of the game translated for Vulkan | ~5 min |
   | textures | the textures re-encoded for PC graphics cards (BC7 / BC1) | ~7 min |

   If it stops (a power cut, you closed it), run `setup.bat` again: it goes on where it stopped.
4. **Play**: start **`UltraTears.exe`** in that folder. The first start takes longer; saves are in `userdata\`.

After the build `game\romfs` is no longer needed (the game reads its packed copy in `data\romfs`): delete it to free
16 GB, or keep it. Do not move or delete `data\`.

Keyboard (until a settings menu exists): WASD move, arrow keys camera, J = A, K / Space = B, I = X, U = Y,
Q / E = L / R, left Alt / Shift = ZL / ZR, Enter = +, Tab / Esc = − (map), T F G H = d-pad, Z / C = stick buttons,
F11 or Alt+Enter = full screen. Controllers (Xbox, DualSense, Switch Pro, ...) work through SDL3.

**Updating the port:** unzip the new builder package over the old one (or into a new folder and copy `data\` and
`userdata\` there) and run `setup.bat`: it rebuilds only what changed.

**Steam Deck (Proton):** build on a PC, copy the whole UltraTears folder to the Deck, add `UltraTears.exe` to Steam as a
non-Steam game and force Proton in its properties.

## Building from the source

See [BUILDING.md](BUILDING.md): the same `tools/setup.py`, with the tools installed yourself.

## Legal

- Nothing of the game is in this repository or in a release: no code (also none translated from the game), no assets,
  shaders, textures, fonts, keys or firmware. Everything derived from the game is made on the player's PC from the
  player's own dump and stays there.
- UltraTears decrypts nothing and reads no keys: it takes the ExeFS and RomFS the player has already extracted.
- No Nintendo SDK code or headers are used; the system and graphics layers are the port's own implementations.
- Only the facts needed to run are in the source: addresses, hashes, short instruction replacements.
- The icon (`assets/icon.ico`) is the author's own drawing, not Nintendo artwork.
- UltraTears is not affiliated with or endorsed by Nintendo; you need your own purchased copy of the game.

## License

UltraTears is free software under the **GNU General Public License v3.0 or later** ([LICENSE](LICENSE)). Third-party
code keeps its own license: [third_party/README.md](third_party/README.md); the builder package adds
`THIRD-PARTY-NOTICES.md` and `licenses\` for the tools it carries.
