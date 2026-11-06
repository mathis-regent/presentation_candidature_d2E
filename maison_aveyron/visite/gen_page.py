"""Generate the shareable page (renders + 360° virtual tour).

usage: python gen_page.py <dir with pano json files> <out_dir>
Writes out_dir/index.html (artifact body) and out_dir/standalone.html (full document).
"""
import json, math, os, sys

SRC, OUT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
CSS = open(os.path.join(HERE, 'pannellum-2.5.6.css')).read()

SCENES = [  # id, json, image, title, initial look-at point (x, y, z)
    ('jardin', 'pj.json', 'panos/jardin.jpg', 'Jardin', (-6.0, 2.0, 3.0)),
    ('terrasse', 'pr.json', 'panos/terrasse.jpg', 'Terrasse sous la pergola', (-20.0, 30.0, 1.4)),
    ('sejour', 'ps.json', 'panos/sejour.jpg', 'Séjour et cuisine', (2.6, 3.6, 1.3)),
]
LINKS = {  # scene -> [(target scene, 3D point to place the arrow, label)]
    'jardin': [('terrasse', (7.3, 6.6, 0.6), 'Aller sur la terrasse')],
    'terrasse': [('jardin', (-12.0, 14.0, 0.4), 'Retour au jardin'),
                 ('sejour', (5.17, 4.6, 1.0), 'Entrer dans le séjour')],
    'sejour': [('terrasse', (5.17, 4.35, 1.1), 'Sortir sur la terrasse')],
}
INFO = {  # scene -> [(3D point, text)]
    'jardin': [((60.0, -18.0, -2.0), 'Vallée et plateau du Causse'),
               ((-12.5, 0.0, 9.0), 'Pignon ouest, toit de lauzes'),
               ((5.2, 8.4, 3.2), 'Pergola en chêne et vigne')],
    'terrasse': [((5.17, 4.7, 2.95), 'Baie vitrée du séjour'),
                 ((5.2, 4.7, 4.7), 'Palier de l’étage')],
    'sejour': [((-2.1, -3.35, 1.2), 'Cheminée en pierre'),
               ((0.5, 2.6, 1.3), 'Cuisine, îlot central'),
               ((5.6, 2.5, 1.0), 'Table devant la baie'),
               ((6.8, -3.8, 1.6), 'Escalier vers l’étage'),
               ((-2.25, -1.2, 1.6), 'Bibliothèque')],
}


def look(meta, p):
    c = meta['cam']
    yaw = meta['yaw']
    f = (math.cos(yaw), math.sin(yaw))
    r = (math.sin(yaw), -math.cos(yaw))
    d = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
    fx = d[0] * f[0] + d[1] * f[1]
    rx = d[0] * r[0] + d[1] * r[1]
    hz = math.hypot(fx, rx)
    return round(math.degrees(math.atan2(d[2], hz)), 2), round(math.degrees(math.atan2(rx, fx)), 2)


scenes = {}
for sid, js, img, title, init in SCENES:
    meta = json.load(open(os.path.join(SRC, js)))
    p0, y0 = look(meta, init)
    hs = []
    for (tgt, pt, label) in LINKS[sid]:
        p, y = look(meta, pt)
        hs.append(dict(pitch=p, yaw=y, type='scene', text=label, sceneId=tgt))
    for (pt, text) in INFO[sid]:
        p, y = look(meta, pt)
        hs.append(dict(pitch=p, yaw=y, type='info', text=text))
    scenes[sid] = dict(title=title, type='equirectangular', panorama=img, pitch=p0, yaw=y0, hfov=105, hotSpots=hs)

config = dict(default=dict(firstScene='jardin', sceneFadeDuration=900, autoLoad=True, showControls=True,
                           compass=False, hfov=105, minHfov=50, maxHfov=120, autoRotate=0,
                           strings=dict(loadingLabel='Chargement…', loadButtonLabel='Cliquer pour charger',
                                        bylineLabel='')),
              scenes=scenes)

PAGE = open(os.path.join(HERE, 'page_template.html')).read()
PAGE = PAGE.replace('/*PANNELLUM_CSS*/', CSS).replace('/*TOUR_CONFIG*/', json.dumps(config, ensure_ascii=False))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w').write(PAGE)
open(os.path.join(OUT, 'standalone.html'), 'w').write(
    '<!doctype html>\n<html lang="fr">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n</head>\n<body>\n'
    + PAGE + '\n</body>\n</html>\n')
print('ok', {k: len(v['hotSpots']) for k, v in scenes.items()})
