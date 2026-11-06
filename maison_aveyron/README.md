# Maison en Aveyron: exterior render built from the hand-drawn plan

![render](rendu/maison_aveyron_golden_hour.jpg)

This picture is **not** an AI image. It is a physically based path-traced render
(Blender Cycles) of a 3D model built from the sketch (`plan_croquis.jpg`), so the footprint,
proportions, rooms and openings follow the plan exactly.

## How the plan was read

The plan's outer rectangle (both floors share the same footprint) is mapped to **25.0 m × 9.4 m**.
The top edge of the plan is the **garden side**. The only window drawn on the plan (above the table)
is there. The entrance **E** and the staircase are on the bottom edge. The garage is at the right end.

| Room (plan) | Floor | Facade opening in the model |
|---|---|---|
| chambre | RDC | garden window with oak shutters + left-gable window |
| SDB | RDC | small window, single oak shutter (garden) |
| WC | RDC | small fixed window (garden) |
| cuisine (L worktop + island) | RDC | window above the worktop, oak shutters (garden) |
| table, opening drawn on the plan | RDC | **large modern glass sliding bay**, oak lintel, terrace + oak pergola with vine |
| zone hachurée | RDC | blind stone wall (no opening) |
| bureau / bibliothèque | RDC | left-gable window (the bookcase wall, on the entrance side, stays blind) |
| buanderie / cellier / PC | RDC | small window on the entrance side |
| salon: canapé, cheminée, TV | RDC | stone chimney stack on the roof |
| entrée **E** | RDC | oak plank door (entrance side) |
| garage | RDC | oak double garage door (right gable) |
| chambre 1 | étage | garden window + left-gable window, oak shutters |
| chambre 2 | étage | garden window, oak shutters |
| jeux | étage | **large modern window** (garden) |
| palier / escalier | étage | **large modern window**, aligned above the glass bay |
| chambre 3, SDB, WC | étage | windows on the entrance side and left gable |
| unlabeled area above the garage | étage | no opening (attic) |

The interior partitions and the main furniture (kitchen worktop, island, table, sofa) are also modelled from the
plan, so what you see through the glass is consistent.

Assumptions: the sketch has no scale, so the 25 m × 9.4 m size was chosen to give realistic room sizes.
The hatched area is read as an enclosed space with no window. Windows that the plan does not draw were
placed one per room, centred on each room's exterior wall.

## Architecture / setting

* Coursed rubble limestone walls (warm beige-golden), lime pointing, dressed quoins, lintels and sills
* Steep (47°) roof of individual schist *lauzes* (several thousand individually modelled slabs), stone chimney with lauze cap
* Natural oak plank shutters with battens, painted casement windows, anthracite frames on the modern openings
* Limestone-paved terrace, oak pergola with vine, lavender, potted box balls, stepping-stone path across the lawn
* Dry-stone walls, gravel courtyard and drive to the garage, old chestnut and oak trees
* Gentle slope above a valley, bocage hills and the Causse escarpment; golden hour sun,
  aerial haze and mist in the valley (height-fog post-process)
* 24 mm lens, full frame, eye level, vertical lines kept straight

## Re-render

```bash
pip install bpy==5.2.3 OpenEXR pillow   # Python 3.13
cd blender
python build_scene.py final ../rendu/render.exr   # ~15 min on 4 CPU cores
python post.py ../rendu/render.exr ../rendu/maison_aveyron_golden_hour.jpg
```

`CAM='{"pos":[-30,24],"target":[8,-2]}'` changes the viewpoint. Presets: `preview`, `mid`, `final`.

To use an AI image generator instead, see [`PROMPT_IA.md`](PROMPT_IA.md). Give it the render as the
reference image so it keeps the layout.
