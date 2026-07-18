# rawtherapee-presets — film-look pipeline for Nikon raws

Each look is a folder holding its color grade and effect doses. The shared
pipeline turns NEFs into finished JPEGs through a lossless intermediate:

`RawTherapee grade → lossless TIFF → halation → grain → JPEG`

Grain is deterministic for each source/look/variant, so rerunning an unchanged
photo preserves the same grain pattern. Pass `--random-grain` when variation is
wanted.

## Process a folder of photos

```
./bin/process.sh <folder-of-NEFs>                          # boardwalk, all 4 variants
./bin/process.sh <folder> 01                               # boardwalk Classic only
./bin/process.sh <folder> all --web                        # + 2048px web copies
./bin/process.sh <folder> <look> all --web                 # a different look
./bin/process.sh <folder> <look> 02 --random-grain         # deliberately fresh grain
```

Output lands next to the photos, in a per-look subfolder:
- `<folder>/renders/<look>/DSC_xxxx_NN.jpg` — full-res finished images
- `<folder>/renders/<look>/contact/` — labeled comparison sheets for multi-variant runs
- `<folder>/renders/<look>/web/` — 2048px sharpened copies (with `--web`)

Originals are never modified. Finished files are replaced atomically only after
the new render succeeds. Contact sheets are built only from the current run, so
old variants cannot leak into a new comparison. Running without `--web` removes
an affected stale web copy if one exists.

Boardwalk variants: `00` Color Only (grade without exposure/tone changes,
for already-well-exposed shots) · `01` Classic (balanced) · `02` Punchy (more contrast,
deeper teal) · `03` Faded (soft pastel, heavy grain).

CLUT-based looks (HaldCLUT film emulations from the RawTherapee Film
Simulation Collection plus separately downloaded Fuji X-Trans samples):
- `fuji` — `01` Classic Chrome · `02` Velvia · `03` Astia · `04` Acros (B&W)
- `portra` — `01` 160 · `02` 400 · `03` 800 (warm, soft negative film)
- `kodachrome` — `01` 25 · `02` 64 · `03` 200 (vintage slide film)
- `polaroid` — `01` 669 · `02` PX-680 · `03` Lomo X-Pro (instant / lo-fi)
- `bw` — `01` Tri-X 400 · `02` HP5 Plus · `03` Delta 3200 (classic B&W)

Curve-based (like boardwalk):
- `cinema` — `01` Soft · `02` Classic · `03` Deep (dark cinematic teal/sage
  with warm amber accents, matte blacks, film grain — moody museum /
  available-light aesthetic)
- `postcard` — `01` Cream · `02` Sunfade · `03` Candy (bright vintage pastel:
  cream highlights, flat gentle contrast, milky sage skies, salmon/mustard
  accents — faded-60s-postcard, inspired by a certain symmetrical filmmaker)

## Layout

```
bin/            shared pipeline, validation, setup checks, and GUI export
cluts/              vendored HaldCLUT PNGs used by the looks
boardwalk/, cinema/, postcard/, fuji/, portra/, kodachrome/, polaroid/, bw/   one folder per look:
  rawtherapee/  portable source .pp3 color grades
  fx.conf       per-variant grain strength/size + halation dose
```

## Adding a new look

Copy `boardwalk/` to a new folder, edit the `.pp3` files and `fx.conf`, then:

```
python3 bin/validate.py
./bin/process.sh <photos> <new-folder-name>
```

Profile filenames must contain ` NN - Label.pp3`; `fx.conf` must have one
matching `NN grain_strength grain_size halation` line per profile. Missing,
duplicate, malformed, and orphan variants are rejected before rendering.

## Tuning

- Grain / halation: numbers in `<look>/fx.conf`
- Vignette: `[PCVignette] Strength` in each .pp3 (scale −6…6; currently mild)
- Color/tone: everything else in the .pp3 files (plain text)

## Setting up on a new machine

The supplied launcher and setup notes target macOS. Install Python dependencies
and check the checkout before processing photos:

```
python3 -m pip install -r requirements.txt
python3 bin/doctor.py
```

Five machine/local assets are deliberately not in the repo:

1. `bin/rtcli` — machine-specific binary; recreate it (see Notes below).
2. The four `cluts/Fuji XTrans III - *.png` CLUTs used by the `fuji` look —
   author allows free use but grants no redistribution license, so download
   them yourself from https://blog.sowerby.me/fuji-film-simulation-profiles/
   and drop them into `cluts/` with those exact names. All other looks work
   without them.

The committed CLUT profiles use portable `cluts/<filename>` references. The
pipeline materializes temporary profiles with absolute paths at runtime, so the
repository can be moved without changing tracked files.

To load profiles in RawTherapee’s GUI, export machine-ready copies and load them
through Processing Profiles → load from file:

```
python3 bin/export_gui_profiles.py ~/Desktop/rawtherapee-gui-profiles
```

Curve-only profiles are also directly loadable from their source folders.

## Notes

- `bin/rtcli` is a re-signed copy of RawTherapee's CLI (the one inside
  /Applications crashes when launched from a terminal because of its App
  Sandbox entitlement). After a RawTherapee update, recreate it:
  copy `rawtherapee-cli` out of the app bundle, then
  `codesign --remove-signature <copy>` and `codesign --force --sign - <copy>`.
- Set `RAWTHERAPEE_CLI=/path/to/rawtherapee-cli` to use a different executable.
- RawTherapee diagnostics are preserved when a render fails.
- Validate the repository at any time with `python3 bin/validate.py`; use
  `--strict-assets` to require the locally downloaded Fuji CLUTs.
- Run the automated checks with `python3 -m unittest discover -s tests -v`.
- Requires: RawTherapee 5.12, Python 3.8+, numpy, and Pillow.
- See `cluts/CREDITS.md` before redistributing the CLUT files.
