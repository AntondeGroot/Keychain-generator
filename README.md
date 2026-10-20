# Keychain-Generator

Turns a picture (PNG or JPEG) into a double-sided, multi-colour keychain for 3D printing.

The picture's colours are matched to your filaments, cleaned up so every line and area is at
least 0.4 mm wide, and traced into smooth outlines. Around it comes a black rim with a tab
and a keyring hole. The keychain is 3 mm thick:

| Layer | Height | What it is |
|---|---|---|
| back face | 0 – 0.8 mm | the picture, mirrored when seen from behind |
| core | 0.8 – 2.2 mm | the rim colour across the whole keychain, so these layers need no filament change |
| front face | 2.2 – 3.0 mm | the picture |

Pictures with flat colours and dark outlines work best, such as cartoons or logos.

## Setup

Requires Python 3.11 or newer, on Windows, macOS or Linux.

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

On Windows (PowerShell), activate with `.venv\Scripts\Activate.ps1` instead.

## Usage

### In the browser

```sh
keychain web
```

This opens a page on your own computer (http://127.0.0.1:8765, not reachable from elsewhere):

1. Choose a picture. Its main colours appear as a list; change, remove or add filaments, or
   use **Pick from picture** to add the colour you click on, such as a small red tongue.
2. Paint a rough mask where the automatic background is wrong: **Background** (red) leaves
   that part out, **Keep** (green) keeps it even if it looks like background. Paint **Smooth**
   (blue) where the curves should be calmer than the picture, such as a wobbly JPEG edge, and
   **Detailed** (yellow) where they should follow it more closely. The **Paint** button next to a
   colour paints with that colour on the picture, for a detail the colours miss. **Connect**: click
   A, then B, to join an area that fades out in between, such as a strip of hair along a
   hairline; it gets a strip of the colour at A.
3. Set the size, and the **curve tolerance**: how far the curves may stray from the picture.
   Every edge is drawn as splines with as few points as fit within it, with sharp corners
   kept sharp and small round blobs such as eyes drawn as ellipses.
4. **Place ring in preview**, then click where the keyring hole should go; a stem joins it to
   the keychain if needed.
5. **Download** a zip with the 3MF and the STLs.

The preview updates by itself after every change; each one takes a few seconds.

### On the command line

First see which colours the picture has:

```sh
keychain colours picture.png
```

It prints the main colours and a ready-made command. Add details the detection missed, such as
a small red tongue, and leave out what you do not want to print, such as soft pink blushes:
pixels of a left-out colour go to the nearest colour that is left.

```sh
keychain make picture.png --colours black=#090404 white=#fefefe skin=#fabe93 red=#e03838
```

Without `--colours`, `make` uses the detected colours. The darkest colour is the ink: the
lines, and unless `--rim-colour` says otherwise also the rim, the ring and the core.

| Option | Default | Meaning |
|---|---|---|
| `--width` | `50` | widest side of the keychain in mm, rim included, keyring tab not |
| `--thickness` | `3.0` | total thickness in mm |
| `--core` | `1.4` | middle layer in mm, in the rim colour; the faces share the rest |
| `--rim` | `1.5` | border around the picture in mm |
| `--hole` | `4.0` | keyring hole diameter in mm |
| `--rim-colour` | ink | name of the colour for the rim, the ring and the core, such as `white`: a light rim keeps the picture's outer lines visible |
| `--out` | `out` | output folder |
| `--open` | | show the output folder when done |

`make` writes a folder named after the picture:

| File | What it is |
|---|---|
| `picture.3mf` | the whole keychain in one file, every colour of every layer a named part |
| `picture-preview.svg` | the front face, to check the colours |
| `picture-front-*.stl`, `picture-core.stl`, `picture-back-*.stl` | the same parts as separate STLs |

Import the 3MF in the slicer and give each part its filament.

## Pictures of characters

Characters such as Tintin are protected by copyright and trademarks. Printing one for yourself
is one thing; sharing the files or the keychains, for example on MakerWorld, needs permission.
