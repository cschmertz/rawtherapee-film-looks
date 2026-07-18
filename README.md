# rawtherapee-presets — film-look pipeline for Nikon raws

Each look is a folder holding its color grade and effect doses; `bin/` is the
shared pipeline that turns NEFs into finished JPEGs
(grade → halation → grain → optional web export + contact sheets).

## Process a folder of photos

```
~/Desktop/rawtherapee-presets/bin/process.sh <folder-of-NEFs>              # boardwalk, all 3 variants
~/Desktop/rawtherapee-presets/bin/process.sh <folder> 01                   # one variant only
~/Desktop/rawtherapee-presets/bin/process.sh <folder> all --web            # + 2048px web copies
~/Desktop/rawtherapee-presets/bin/process.sh <folder> <look> all --web     # a different look
```

Output lands next to the photos, in a per-look subfolder:
- `<folder>/renders/<look>/DSC_xxxx_NN.jpg` — full-res finished images
- `<folder>/renders/<look>/contact/` — labeled comparison sheets (start here)
- `<folder>/renders/<look>/web/` — 2048px sharpened copies (with `--web`)

Originals are never modified.

Boardwalk variants: `00` Color Only (grade without exposure/tone changes,
for already-well-exposed shots) · `01` Classic (balanced) · `02` Punchy (more contrast,
deeper teal) · `03` Faded (soft pastel, heavy grain).

CLUT-based looks (HaldCLUT film emulations from the public-domain
RawTherapee Film Simulation Collection + real-camera Fuji X-Trans samples,
vendored in `cluts/`):
- `fuji` — `01` Classic Chrome · `02` Velvia · `03` Astia · `04` Acros (B&W)
- `portra` — `01` 160 · `02` 400 · `03` 800 (warm, soft negative film)
- `kodachrome` — `01` 25 · `02` 64 · `03` 200 (vintage slide film)
- `polaroid` — `01` 669 · `02` PX-680 · `03` Lomo X-Pro (instant / lo-fi)
- `bw` — `01` Tri-X 400 · `02` HP5 Plus · `03` Delta 3200 (classic B&W)

## Layout

```
bin/            shared pipeline (rtcli, film_fx.py, web_export.py,
                contact_sheet.py, process.sh)
cluts/              vendored HaldCLUT PNGs used by the looks
boardwalk/, fuji/, portra/, kodachrome/, polaroid/, bw/   one folder per look:
  rawtherapee/  the .pp3 color grades (also loadable in RawTherapee GUI:
                Processing Profiles → load from file)
  fx.conf       per-variant grain strength/size + halation dose
```

## Adding a new look

Copy `boardwalk/` to a new folder, edit the `.pp3` files and `fx.conf`,
then `process.sh <photos> <new-folder-name>`. No script changes needed.

## Tuning

- Grain / halation: numbers in `<look>/fx.conf`
- Vignette: `[PCVignette] Strength` in each .pp3 (scale −6…6; currently mild)
- Color/tone: everything else in the .pp3 files (plain text)

## Setting up on a (new) machine

Two files are deliberately not in the repo:

1. `bin/rtcli` — machine-specific binary; recreate it (see Notes below).
2. The four `cluts/Fuji XTrans III - *.png` CLUTs used by the `fuji` look —
   author allows free use but grants no redistribution license, so download
   them yourself from https://blog.sowerby.me/fuji-film-simulation-profiles/
   and drop them into `cluts/` with those exact names. All other looks work
   without them.

Also note the `.pp3` files reference `cluts/` by absolute path. If this repo
lives anywhere other than `/Users/conorschmertz/Desktop/rawtherapee-presets`,
fix the paths once:

```
cd rawtherapee-presets
LC_ALL=C find . -name '*.pp3' -exec sed -i '' "s|/Users/conorschmertz/Desktop/rawtherapee-presets|$(pwd)|g" {} +
```

## Notes

- `bin/rtcli` is a re-signed copy of RawTherapee's CLI (the one inside
  /Applications crashes when launched from a terminal because of its App
  Sandbox entitlement). After a RawTherapee update, recreate it:
  copy `rawtherapee-cli` out of the app bundle, then
  `codesign --remove-signature <copy>` and `codesign --force --sign - <copy>`.
- Requires: RawTherapee (brew cask), python3 with numpy + Pillow.
