# Creative look research

This document records the visual targets and public sources used to design the
original curve-based looks. Reference images inform direction only; the final
profiles are calibrated against Conor's Nikon NEFs rather than copied from any
single photograph or commercial preset.

## Night

- **Tungsten:** 3200K-balanced low-light color, cool ambient shadows, warm
  practical lights, soft highlight rolloff, and restrained red-orange halation.
- **Neon:** cyan/blue-green shadows, vivid red and magenta signs, protected
  highlight color, and slightly stronger halation.
- **Sodium:** amber practical lights, deep neutral shadows, muted blues, and a
  heavier high-speed-film texture.

Sources:

- [CineStill 800T product characteristics](https://cinestill.film/products/800tungsten-c41-36exp-35mm-high-speed-color-negative-135)
- [Mastin Labs Night & Day workflow and tools](https://mastinlabs.com/blogs/photoism/mastin-labs-night-and-day-lightroom-presets-pack)

## Editorial

- **Clean:** neutral whites, faithful skin, gentle contrast, low grain.
- **Warm:** cream highlights, warm skin and midtones, softly lifted blacks.
- **Cool:** neutral skin with slate shadows and a restrained fashion-grade
  palette.

Sources:

- [Fujifilm portrait and skin-tone guidance](https://fujifilm-x.com/en-us/wp-content/uploads/sites/11/2021/11/stunning-skin-tones-and-perfect-portraits-with-fujifilm-x-series.pdf)
- [Kodak professional portrait-film characteristics](https://www.kodak.com/en/still-film/product/professional/ektacolor-film/)

## Flash

These profiles grade photographs made with direct flash; they do not attempt to
simulate the physical direction, shadows, falloff, or catchlights of flash on a
non-flash exposure.

- **Disposable:** warm whites, lifted blacks, visible grain, softened contrast.
- **Afterparty:** cooler flash whites, strong reds and blues, dark background.
- **Gloss:** cleaner whites, crisp contrast, restrained grain and saturation.

Sources:

- [Mastin Labs Night & Day flash and strobe tools](https://mastinlabs.com/blogs/photoism/mastin-labs-night-and-day-lightroom-presets-pack)
- [Adobe's portrait and subject-oriented preset model](https://helpx.adobe.com/lightroom/mobile/work-with-presets/apply-presets.html)

## Bleach Bypass

These curve-based profiles reproduce the progressively stronger contrast,
desaturation, and visible silver associated with partial and full
bleach-bypass processing without depending on a third-party CLUT:

- **Half:** partial bypass with moderate contrast and enough retained color for
  general use.
- **Silver:** the classic cold, low-saturation silver-retention treatment.
- **Grit:** hard contrast, near-monochrome color, an olive bias, and coarse
  grain as a deliberately more aggressive creative extension.

The original `cinema/04` profile remains available for compatibility and is
closest to **Silver**.

Source:

- [Fujifilm ETERNA Bleach Bypass](https://www.fujifilm-x.com/en-sg/products/film-simulation/eterna-bleach-bypass/)

## Landscape

- **Golden:** warm earth and highlights, rich but controlled blue skies.
- **Alpine:** clean whites, cool shadows, crisp blues, restrained greens.
- **Forest:** deep differentiated greens, warm earth, gentle highlight rolloff.

Sources:

- [Kodak EKTAR 100 characteristics](https://www.kodak.com/en/still-film/product/professional/ektar-100-film/)
- [Fujifilm film simulations for landscape and golden hour](https://www.fujifilm-x.com/en-gb/learning-centre/empower-your-photography-with-fujifilm-film-simulations/)

## Validation coverage

The July 2026 test set contains 19 Nikon NEFs covering bright water and sky,
foliage, overcast autumn, snow, fog, architecture, reflective surfaces, one
warm-lamp night, and one mixed-light night. Night, Bleach Bypass, and Landscape
can be visually calibrated against this set. Editorial and Flash are initial
reference-grounded profiles until close portraits and direct-flash NEFs are
added.
