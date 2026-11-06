# Prompt for an AI image generator (Midjourney / DALL·E / Firefly / SDXL…)

Image generators cannot read a floor plan precisely. For the strictest fidelity to the plan,
use `rendu/maison_aveyron_golden_hour.png` (3D render built from the plan) as the reference
image (image-to-image or ControlNet *depth/canny* ~0.6–0.8), together with this prompt:

```
Photorealistic real-estate exterior photograph of a renovated traditional Aveyron farmhouse
(southern France). Long rectangular two-storey house, about 25 m by 9.5 m, single volume
under a steep 47° dark schist "lauze" stone roof with gable ends and a stone chimney near
the ridge. Thick walls of warm beige-golden limestone rubble with lime pointing, dressed
stone quoins, lintels and sills. Garden facade (long side): ground floor, from left to right:
bedroom window with oak shutters, small bathroom window with one oak shutter, tiny WC window,
kitchen window with oak shutters, then a large modern floor-to-ceiling glass sliding bay
(dark anthracite frame, oak beam lintel) opening onto a small limestone-paved terrace under
an oak pergola covered with a vine; blind stone wall section at the garage end.
First floor: two bedroom windows with natural oak plank shutters folded open, then two large
modern glass windows with thin anthracite frames (play room and stair landing, the latter
right above the glass bay). Left gable: two windows per floor with oak shutters.
Right gable: oak plank garage double door. Setting: on a gentle slope overlooking green
rolling hills and the Causses plateau, dry-stone limestone walls, old chestnut and oak trees,
gravel courtyard and driveway, lavender. Golden hour, soft warm low sunlight, long shadows,
light mist in the valley, warm glow in the windows. Shot on full-frame camera, 24 mm lens,
eye level, vertical lines kept straight, natural colours, ultra realistic.
No people, no text, no watermark.
```

Negative prompt (if supported): `people, text, watermark, logo, cartoon, CGI look, oversaturated,
distorted perspective, extra floors, balcony, swimming pool, red tile roof, render artifacts`
