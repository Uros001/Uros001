"""Edit decision list for THE PEMMICAN WAR (15:00).

CLIPS: (start, shot, xfade) — start is a narration anchor (see core.anchor) or seconds; each clip runs to
the next clip's start. xfade > 0 dissolves into the clip over that many seconds, centred on the cut;
a negative xfade dips through black for |xfade| seconds.
OVERLAYS: (t0, t1, fn(L, t)) drawn on a Skia layer over the graded picture.
"""
from . import core, gfx, mapseq as MS, text as T
from .shots import Plate, Func, Black
from .core import anchor as A

# ------------------------------------------------------------------ atmosphere presets
DAWN_FOG = dict(density=0.30, speed=(0.010, 0.0), color=(0.78, 0.80, 0.82), band=(0.05, 0.55), soft=0.3)
LOW_FOG = dict(density=0.26, speed=(0.006, 0.0), color=(0.80, 0.78, 0.72), band=(0.35, 0.8), soft=0.35)
DUSK_FOG = dict(density=0.24, speed=(0.005, 0.0), color=(0.45, 0.5, 0.6), band=(0.35, 0.75), soft=0.35)
DUST = dict(n=220, opacity=0.28, size=1.5, drift=(0.003, -0.001), color=(1.0, 0.92, 0.78))
MOTES = dict(n=260, opacity=0.45, size=1.3, drift=(0.0015, -0.0006), color=(1.0, 0.9, 0.75), sway=0.003)
SNOW = dict(n=520, opacity=0.65, size=2.0, drift=(0.004, 0.0), fall=0.035, sway=0.008, color=(0.95, 0.97, 1.0), seed=8)
EMBERS = dict(n=70, opacity=0.9, size=1.5, drift=(0.0, -0.03), sway=0.012, color=(1.0, 0.62, 0.25), seed=12)

G_DAWN = dict(contrast=1.04, sat=0.9, temp=0.25)
G_GOLD = dict(contrast=1.05, sat=0.92, temp=0.35, gamma=1.02)
G_WINTER = dict(contrast=1.03, sat=0.82, temp=-0.35, gamma=1.0)
G_DUSK = dict(contrast=1.06, sat=0.85, temp=-0.2, gain=0.92)
G_CANDLE = dict(contrast=1.06, sat=0.95, temp=0.2)
G_STORE = dict(contrast=1.06, sat=0.9, temp=0.15)


def _meta(name):
    import json, os
    p = os.path.join(core.ROOT, 'renders/plates', name + '_meta.json')
    return json.load(open(p)) if os.path.exists(p) else {}


def default_life(name):
    """Natural motion per scene family (see film.life). Emitter sizes scale with camera distance."""
    fam, cam = name.split('_')[0], name.split('_')[1]
    pts = _meta(name).get('points', {})

    def em(prefix, ref):
        out = []
        for k, (x, y, d) in pts.items():
            if k.startswith(prefix) and -0.05 < x < 1.05 and -0.05 < y < 1.0 and d > 0:
                out.append((x, y, min(3.0, ref / d)))
        return out

    L = {}
    if fam == 'dock':
        L['water'] = dict(strength=1.1)
    elif fam == 'camp':
        if cam in ('R1', 'R3', 'R3b', 'R2'):
            L['wind'] = dict(strength=0.9)
            L['clouds'] = dict(cover=0.38, opacity=0.55, speed=0.003, tint=(1.0, 0.95, 0.88) if cam != 'R3b' else (1.0, 0.82, 0.8))
            e = em('lodge', 20.0) + (em('fire', 8.0) if cam != 'R3b' else [])
            if e:
                L['smoke'] = dict(points=e, rate=4, rise=0.018, drift=(0.012, 0), size=0.006, grow=0.035, opacity=0.4,
                                  color=(0.66, 0.66, 0.68))
        if cam in ('K1', 'K3'):
            L['wind'] = dict(strength=0.7, y0=0.0)
        if cam == 'K2':
            L['wind'] = dict(strength=0.6, y0=0.0)
            L['heat'] = dict(box=(0.22, 0.0, 0.78, 0.3), strength=3.0)
            L['smoke'] = dict(points=[(0.5, 0.2, 2.2)], rate=6, rise=0.03, drift=(0.01, 0), size=0.02, grow=0.12, opacity=0.22,
                              color=(0.7, 0.68, 0.66))
    elif fam == 'plain':
        L['wind'] = dict(strength=1.3 if cam in ('G2',) else 1.0)
        if cam in ('G1', 'G3', 'G4'):
            L['fgwind'] = dict(strength=0.8, y0=0.0, speed=0.08)
        if cam != 'G2':
            L['clouds'] = dict(cover=0.4, opacity=0.6, speed=0.003,
                               tint=(1.0, 0.82, 0.78) if cam in ('G3', 'B2') else (1.0, 0.94, 0.86))
    elif fam == 'fort':
        winter = cam in ('F1', 'F2')
        L['clouds'] = dict(cover=0.62 if winter else 0.4, opacity=0.6, speed=0.003, tint=(0.95, 0.97, 1.0) if winter else (1.0, 0.95, 0.88))
        L['wind'] = dict(strength=0.6)
        e = em('chimney', 60.0)
        if e:
            L['smoke'] = dict(points=e, rate=5, rise=0.02, drift=(0.012, 0), size=0.008, grow=0.05, opacity=0.6 if winter else 0.4,
                              color=(0.55, 0.57, 0.61) if winter else (0.7, 0.7, 0.72))
    return L


def P(name, s=(1.0, 1.08), c=((0.5, 0.5), (0.5, 0.5)), **kw):
    fam = name.split('_')[0]
    if 'life' not in kw:
        kw['life'] = default_life(name)
    defaults = dict(
        dock=dict(fog=DAWN_FOG, dust=dict(DUST, opacity=0.18), grade=G_DAWN),
        camp=dict(dust=DUST, grade=G_GOLD),
        fort=dict(grade=G_WINTER),
        plain=dict(dust=DUST, grade=G_GOLD),
        desk=dict(grade=G_CANDLE, bloom=(0.72, 0.3)),
        store=dict(dust=MOTES, grade=G_STORE, bloom=(0.75, 0.25)),
    ).get(fam, {})
    d = dict(defaults)
    d.update(kw)
    return Plate(name, s=s, c=c, **d)


def F(fn, desc, source='Original motion graphic'):
    return Func(fn, desc=desc, source=source)


def cont(fn, start, total_end):
    """Run a map/graphic on its own clock (from `start`) even when the edit cuts away and back."""
    return lambda tl, dur, t: fn(t - A(start), A(total_end) - A(start), t)


def chapter(n, title, plate=None):
    return F(gfx.chapter(n, title, plate), f'Chapter card {n}: {title}' + (f' over `{plate}`' if plate else ''))


def tl_view(t0=None):
    return F(lambda tl, dur, t: gfx.timeline(tl, dur, t), 'Timeline 1812–1816')


# ------------------------------------------------------------------ clips
CLIPS = [
    # ---------------- cold open
    (0.0, P('dock_D1', s=(1.0, 1.16), c=((0.5, 0.52), (0.47, 0.58)), p=0.07, desc='The bag on the landing at dawn: slow push-in'), 0),
    ('P01.2-0.35', P('dock_D2', s=(1.08, 1.16), c=((0.44, 0.5), (0.56, 0.5)), p=0.05, desc='Seam macro: lacing and greased edge'), 0.6),
    ('P02.0-0.45', P('dock_C1', s=(1.0, 1.08), c=((0.5, 0.5), (0.52, 0.5)), desc='Northern canoe at the landing'), 0.7),
    ('P02.1-0.15', P('fort_F1', s=(1.0, 1.1), c=((0.5, 0.52), (0.52, 0.5)), dust=SNOW, desc='Palisaded post in winter (Red River colony, illustrative)'), 0.8),
    ('P02.1+6.5', P('desk_W2', s=(1.04, 1.16), c=((0.55, 0.5), (0.6, 0.48)), p=0.04, flicker=0.025, desc='Quill on a written sheet by candlelight'), 0.6),
    ('P02.1e+0.8', F(gfx.not_move, 'Typographic beat: "Not illegal to eat. Illegal to move."'), 0.5),
    ('P04.0-0.5', P('plain_G3', s=(1.0, 1.07), c=((0.5, 0.5), (0.5, 0.48)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Frog Plain after sunset'), -0.9),
    ('P04.1-0.25', P('plain_G2', s=(1.04, 1.12), c=((0.45, 0.55), (0.55, 0.55)), p=0.12, grade=G_DUSK, desc='Grass close-up, evening'), 0.6),
    ('P05.0-0.35', P('dock_D3', s=(1.0, 1.1), c=((0.5, 0.5), (0.48, 0.52)), p=0.08, desc='The bag, low angle, river mist'), 0.8),
    ('P05.1+2.6', P('camp_K1', s=(1.0, 1.1), c=((0.5, 0.5), (0.48, 0.52)), desc='Pounded meat on a spread hide, stone maul'), 0.7),
    ('TITLE', F(gfx.title_card, 'Title card'), -1.0),
    # ---------------- I. Meat That Keeps
    ('TITLE.e', F(gfx.water, 'Graphic: fresh meat is about three-quarters water'), -1.0),
    ('P06.2-0.3', P('plain_B1', s=(1.04, 1.12), c=((0.42, 0.5), (0.58, 0.5)), p=0.05, desc='Bison herd on the northern plains (reconstruction)'), 0.6),
    ('P06.3-0.3', P('camp_R1', s=(1.0, 1.08), c=((0.5, 0.5), (0.52, 0.5)), desc='Plains camp with drying racks'), 0.6),
    ('P07.0-0.45', P('dock_C2', s=(1.04, 1.12), c=((0.45, 0.5), (0.55, 0.5)), desc='Canoe from water level'), 0.6),
    ('P07.2-0.3', F(MS.plains_peoples, 'Map: Cree and Assiniboine lands where they met the fur trade'), 0.7),
    ('P07.3-0.3', F(gfx.word_card, 'Word card: pimîhkân (Cree)'), 0.6),
    ('P08.0-0.25', P('camp_R2', s=(1.0, 1.12), c=((0.5, 0.45), (0.5, 0.52)), p=0.08, desc='Thin-cut meat drying on a rack'), 0.6),
    ('P08.1-0.3', P('camp_K1', s=(1.14, 1.24), c=((0.5, 0.5), (0.47, 0.5)), p=0.05, desc='Pounding on a spread hide'), 0.5),
    ('P08.2-0.3', P('camp_K2', s=(1.0, 1.1), c=((0.5, 0.55), (0.5, 0.5)), dust=EMBERS, flicker=0.04, desc='Rendering fat in a trade kettle'), 0.5),
    ('P08.3-0.3', P('camp_K3', s=(1.02, 1.12), c=((0.5, 0.5), (0.5, 0.48)), p=0.05, desc='Dried berries in a wooden bowl'), 0.5),
    ('P08.4-0.3', P('dock_D2', s=(1.2, 1.28), c=((0.6, 0.45), (0.48, 0.5)), p=0.05, desc='Laced seam of a rawhide bag'), 0.6),
    ('P09.0-0.45', P('camp_R3', s=(1.0, 1.08), c=((0.48, 0.5), (0.53, 0.5)), desc='Camp: hide frame, racks and lodges'), 0.7),
    ('P10.0-0.45', F(gfx.steps, 'Graphic: what each step does'), 0.6),
    ('P10.2-0.3', F(gfx.ratio, 'Graphic: 5–6 lb fresh meat to 1 lb dried'), 0.5),
    ('P11.0-0.3', F(gfx.energy, 'Graphic: energy per gram, fat vs protein'), 0.5),
    ('P11.2-0.3', F(gfx.section, 'Diagram: cross-section of a filled bag'), 0.5),
    ('P12.0-0.45', P('store_S2', s=(1.0, 1.1), c=((0.5, 0.5), (0.46, 0.5)), p=0.05, desc='Stacked bags in a store'), 0.7),
    ('P12.2-0.3', P('store_S1', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), desc='Depot storehouse, light from the door'), 0.6),
    ('P12.3-0.3', P('dock_C3b', s=(1.0, 1.1), c=((0.5, 0.5), (0.48, 0.52)), desc='Bags and bales loaded in the canoe'), 0.6),
    ('CH2', chapter('II', 'The Canoe Road', 'dock_C2'), -1.0),
    # ---------------- II. The Canoe Road
    ('CH2.e', P('dock_C2', s=(1.12, 1.2), c=((0.6, 0.5), (0.45, 0.5)), p=0.06, desc='Canoe, low side angle'), -1.0),
    ('P14.0-0.5', F(MS.canoe_road, 'Map: the North West Company canoe road, Montreal to Athabasca'), 0.7),
    ('P15.0-0.4', P('dock_C1', s=(1.1, 1.2), c=((0.45, 0.5), (0.55, 0.52)), desc='Canoe at the landing, mist'), 0.7),
    ('P15.2-0.3', F(gfx.cargo, 'Graphic: food versus cargo in one load'), 0.5),
    ('P15.3-0.3', P('dock_D4', s=(1.0, 1.08), c=((0.5, 0.5), (0.5, 0.5)), desc='River landing, wide'), 0.5),
    ('P16.0-0.45', F(gfx.ration, 'Graphic: about 2 lb a day'), 0.6),
    ('P16.2-0.3', F(MS.depots, 'Map: plains provisioning and depots on the route'), 0.6),
    ('P16.4-0.3', F(gfx.depot_math, 'Graphic: four 90-lb bags per canoe'), 0.6),
    ('P17.0-0.45', P('fort_F3', s=(1.0, 1.08), c=((0.5, 0.5), (0.48, 0.5)), desc='A trading post on the river in summer'), 0.7),
    ('P17.1-0.3', F(MS.metis_rivers, 'Map: Métis communities on the Red and Assiniboine'), 0.6),
    ('P17.2-0.3', P('plain_B3', s=(1.0, 1.1), c=((0.42, 0.5), (0.55, 0.5)), p=0.05, desc='A line of Red River carts on the plains'), 0.7),
    ('P17.3-0.3', P('store_S1', s=(1.12, 1.2), c=((0.42, 0.55), (0.38, 0.55)), desc='Bags stacked at a post'), 0.6),
    ('P18.0-0.45', P('plain_B1', s=(1.15, 1.25), c=((0.55, 0.52), (0.45, 0.52)), p=0.05, desc='Bison herd, closer'), 0.7),
    ('P18.1-0.3', F(MS.furs_fuel, 'Map: furs from the north, fuel from bison country'), 0.6),
    ('P19.0-0.45', P('fort_F3', s=(1.06, 1.12), c=((0.5, 0.5), (0.52, 0.5)), desc='A post on the river'), 0.7),
    ('P19.1-0.35', F(cont(MS.two_routes, 'P19.0-0.45', 'CH3'), "Map: Hudson's Bay Company by sea vs North West Company by canoe; zoom to the Forks"), 0.6),
    ('CH3', chapter('III', 'The Order', 'desk_W1'), -1.0),
    # ---------------- III. The Order
    ('CH3.e', F(cont(MS.assiniboia_map, 'CH3.e', 'P21.0-0.45'), 'Map: the Selkirk grant (Assiniboia) and Italy at the same scale'), -1.0),
    ('P20.2-0.3', P('plain_G4', s=(1.0, 1.08), c=((0.5, 0.5), (0.5, 0.48)), desc='Open land under a bur oak'), 0.6),
    ('P20.3-0.35', F(cont(MS.assiniboia_map, 'CH3.e', 'P21.0-0.45'), 'Map: Assiniboia, the Forks'), 0.6),
    ('P21.0-0.45', P('fort_F3', s=(1.12, 1.2), c=((0.45, 0.55), (0.5, 0.55)), desc='The post, summer'), 0.7),
    ('P21.1-0.3', P('camp_R3b', s=(1.0, 1.08), c=((0.5, 0.5), (0.5, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Empty racks at dusk'), 0.7),
    ('P21.2-0.3', P('fort_F2', s=(1.0, 1.1), c=((0.5, 0.5), (0.5, 0.48)), dust=SNOW, desc='The gate in winter'), 0.7),
    ('P22.0-0.45', P('desk_W1', s=(1.0, 1.08), c=((0.5, 0.5), (0.52, 0.52)), flicker=0.03, desc='Writing table by candlelight (generated prop document)'), 0.7),
    ('P22.1-0.4', F(gfx.order_terms, "Graphic: the order's main terms, paraphrased"), 0.6),
    ('P23.0-0.45', F(gfx.paper_practice, 'Graphic: on paper vs in practice'), 0.6),
    ('P24.0-0.45', P('fort_F3', s=(1.18, 1.26), c=((0.55, 0.55), (0.6, 0.55)), desc='The post, summer, closer'), 0.6),
    ('P24.1-0.3', F(MS.souris, "Map: the colony to the North West Company post on the Souris"), 0.6),
    ('P24.2-0.4', F(gfx.bags479, 'Graphic: 479 bags seized'), 0.6),
    ('CH4', chapter('IV', 'Frog Plain', 'plain_G3'), -1.0),
    # ---------------- IV. Frog Plain
    ('CH4.e', F(gfx.timeline, 'Timeline 1812–1816'), -1.0),
    ('P25.2-0.35', P('camp_R3b', s=(1.1, 1.18), c=((0.45, 0.5), (0.55, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Empty racks'), 0.7),
    ('P26.0-0.45', P('fort_F3', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), desc='The post, summer 1815'), 0.7),
    ('P26.2-0.4', F(gfx.timeline, 'Timeline: Fort Gibraltar seized'), 0.6),
    ('P27.0-0.45', P('plain_G1', s=(1.0, 1.08), c=((0.5, 0.5), (0.52, 0.5)), desc='Open plain at golden hour'), 0.7),
    ('P27.1-0.3', F(gfx.timeline, "Timeline: Qu'Appelle seizure"), 0.6),
    ('P27.2-0.3', P('store_S2', s=(1.12, 1.22), c=((0.42, 0.5), (0.5, 0.5)), p=0.05, desc='Bags of pemmican'), 0.5),
    ('P28.0-0.45', F(lambda tl, dur, t: MS.frog_plain_map(tl, dur, t, 'route'), "Map: Grant's party toward Lake Winnipeg past the colony"), 0.6),
    ('P28.3-0.25', P('plain_G2', s=(1.0, 1.06), c=((0.5, 0.5), (0.52, 0.5)), p=0.1, desc='Grass of the low plain'), 0.5),
    ('P29.0-0.45', P('plain_G1', s=(1.1, 1.18), c=((0.45, 0.5), (0.5, 0.5)), desc='Frog Plain, evening of 19 June (illustrative)'), 0.7),
    ('P30.0-0.6', P('plain_G3', s=(1.06, 1.14), c=((0.5, 0.5), (0.5, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='The plain at dusk'), 0.9),
    ('P30.4-0.3', P('plain_G4', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.48)), grade=dict(G_DUSK, gain=0.75), dust=None, desc='Under a bur oak, failing light'), 1.0),
    ('P31.0-0.8', P('fort_F3', s=(1.2, 1.28), c=((0.4, 0.55), (0.45, 0.55)), grade=dict(G_GOLD, gain=0.9), desc='The post'), -1.2),
    ('P32.0-0.45', F(gfx.two_names, 'Graphic: two names for one event'), 0.7),
    ('P32.2-0.3', P('plain_G4', s=(1.08, 1.16), c=((0.5, 0.45), (0.5, 0.5)), desc='Bur oak at golden hour'), 0.7),
    ('P32.3-0.3', P('plain_B3', s=(1.15, 1.25), c=((0.55, 0.5), (0.45, 0.5)), p=0.05, desc='Cart line'), 0.7),
    ('P33.0-0.45', P('plain_G3', s=(1.15, 1.2), c=((0.45, 0.5), (0.5, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Dusk'), 0.6),
    ('P33.1-0.3', F(MS.fort_william_map, 'Map: Selkirk seizes Fort William, 1816'), 0.6),
    ('P33.2-0.3', P('desk_W2', s=(1.0, 1.08), c=((0.5, 0.5), (0.45, 0.52)), flicker=0.025, desc='Pen and paper: lawsuits and inquiries'), 0.6),
    ('P33.3-0.3', F(gfx.merger, 'Graphic: 1821 merger'), 0.6),
    ('CH5', chapter('V', 'The Last Hunts', 'plain_B2'), -1.0),
    # ---------------- V. The Last Hunts
    ('CH5.e', P('camp_R1', s=(1.1, 1.18), c=((0.55, 0.5), (0.45, 0.5)), desc='Camp with full racks'), -1.0),
    ('P34.2-0.3', P('plain_B3', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), desc='The Red River hunt: a line of carts'), 0.6),
    ('P34.3-0.3', F(MS.globe_pole, "Globe: pemmican to the South Pole with Amundsen's party, 1911"), 0.7),
    ('P35.0-0.45', P('dock_D3', s=(1.12, 1.2), c=((0.5, 0.52), (0.5, 0.5)), p=0.08, desc='The bag in the mist'), 0.8),
    ('P36.0-0.45', P('dock_D5', s=(1.0, 1.08), c=((0.5, 0.5), (0.5, 0.5)), p=0.06, desc='The bag, side angle'), 0.7),
    ('P36.1-0.3', P('plain_G1', s=(1.18, 1.26), c=((0.5, 0.5), (0.55, 0.5)), desc='The open plain'), 0.6),
    ('P36.2-0.3', P('plain_B1', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), desc='The herd'), 0.7),
    ('P37.0-0.45', P('plain_B1', s=(1.06, 1.0), c=((0.5, 0.5), (0.5, 0.5)), desc='The herd, pulling back'), 0.4),
    ('P37.2-0.3', P('camp_R3b', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Empty racks at dusk'), 0.7),
    ('P37.3-0.3', P('plain_B2', s=(1.0, 1.05), c=((0.5, 0.5), (0.5, 0.5)), p=0.02, dust=None, grade=dict(G_GOLD, temp=0.5),
                    fade_parts=(A('P37.3+1.5'), A('P38.1+2.0')), desc='Bison on the ridge, disappearing one by one'), 0.8),
    ('P38.2-0.3', P('plain_G3', s=(1.0, 1.05), c=((0.5, 0.5), (0.5, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Empty plain at dusk'), 0.8),
    ('P39.0-0.45', P('plain_B2', s=(1.05, 1.1), c=((0.5, 0.5), (0.5, 0.5)), p=0.02, dust=None, fg_alpha=0.0, grade=dict(G_DUSK, temp=0.2),
                     desc='The empty ridge'), 0.8),
    ('P40.0-0.6', P('camp_R3b', s=(1.1, 1.16), c=((0.45, 0.5), (0.5, 0.5)), fog=DUSK_FOG, grade=G_DUSK, dust=None, desc='Empty racks'), 0.8),
    ('P41.0-0.45', P('plain_B1', s=(1.2, 1.28), c=((0.45, 0.5), (0.55, 0.5)), p=0.05, desc='Bison returning'), 0.8),
    ('P41.1-0.3', P('camp_K3', s=(1.12, 1.2), c=((0.5, 0.5), (0.5, 0.5)), desc='Berries for pemmican'), 0.6),
    ('P41.1+4.0', P('camp_K1', s=(1.0, 1.06), c=((0.5, 0.5), (0.5, 0.5)), desc='Pounded meat on a hide'), 0.6),
    ('P41.2-0.3', F(MS.treaty_map, 'Map: the Buffalo Treaty, 2014'), 0.7),
    ('P42.0-0.5', P('dock_D5', s=(1.08, 1.14), c=((0.5, 0.5), (0.52, 0.5)), p=0.06, desc='The bag'), 0.9),
    ('P42.1-0.2', P('desk_W2', s=(1.15, 1.2), c=((0.55, 0.5), (0.55, 0.5)), flicker=0.025, desc='The order'), 0.3),
    ('P42.2-0.2', P('plain_G2', s=(1.15, 1.2), c=((0.5, 0.5), (0.5, 0.5)), grade=G_DUSK, desc='The plain'), 0.3),
    ('P42.3-0.2', P('dock_C3b', s=(1.15, 1.2), c=((0.5, 0.5), (0.5, 0.5)), desc='Cargo'), 0.3),
    ('P42.4-0.3', P('dock_D4', s=(1.12, 1.0), c=((0.5, 0.5), (0.5, 0.5)), p=0.05, desc='Pull back from the landing'), 0.9),
    ('CREDITS', F(gfx.credits, 'Credits and disclosures'), -1.4),
]


# ------------------------------------------------------------------ overlays
def _d(fn, desc):
    fn.desc = desc
    return fn


def lt(name, role, t0, t1):
    return (t0, t1, _d(lambda L, t: T.lower_third(L, t, t0, t1, name, role), f'Lower third: {name} — {role}'))


def sup(l1, l2, t0, t1):
    return (t0, t1, _d(lambda L, t: T.super_label(L, t, t0, t1, l1, l2), f'Super: {l1} / {l2}'))


def recon(t0, t1, txt='Reconstruction'):
    return (t0, t1, _d(lambda L, t: L.text(txt.upper(), 1840, 1040, T.font('sans', 15, 600), T.INK_DIM,
                                           0.75 * T.fade_window(t, t0, t1, 0.6, 0.6), align='right', tracking=3, shadow=0.8),
                       f'Tag: "{txt}"'))


def ovl(fn, *args):
    txt = ' / '.join(str(a) for a in args[2:4])
    return _d(lambda L, t: fn(L, t, *args), f'{fn.__name__.replace("ov_", "").capitalize()}: {txt}')


def build_overlays():
    o = []
    o.append(recon(1.0, 8.0, 'Reconstruction  ·  3D'))
    o.append(sup('Red River colony', '8 January 1814', A('P02.1+0.6'), A('P02.1+6.3')))
    o.append(sup('Frog Plain', '19 June 1816', A('P04.0+0.6'), A('P04.1-0.4')))
    o.append(recon(A('P05.1+2.8'), A('P05.1+6.5'), 'Reconstruction'))
    o.append((A('TITLE.e'), A('TITLE.e+4.4'), _d(lambda L, t: T.chapter_label(L, t, A('TITLE.e') + 0.2, 'I', 'Meat That Keeps'),
                                                 'Chapter label: I Meat That Keeps')))
    o.append(recon(A('P06.2'), A('P06.2+4.0'), 'Reconstruction'))
    o.append(lt('Thomas Douglas, Earl of Selkirk', "Hudson's Bay Company shareholder", A('P20.0+1.5'), A('P20.0+8.0')))
    o.append(lt('Miles Macdonell', 'Governor of the Red River colony', A('P21.0+0.3'), A('P21.0e+0.2')))
    o.append(lt('Robert Semple', 'Governor from the fall of 1815', A('P26.1+1.0'), A('P26.1e+0.3')))
    o.append(lt('Cuthbert Grant', 'Métis leader', A('P27.0+1.6'), A('P27.0e+0.3')))
    o.append(sup('Evening, 19 June 1816', 'Fort Douglas to Frog Plain', A('P29.0+0.3'), A('P29.0e+0.3')))
    o.append(lt('Pierre Falcon', 'Métis songwriter: La Chanson de la Grenouillère', A('P32.2+0.3'), A('P32.2e+0.3')))
    o.append((A('P34.2+0.3'), A('P34.2e+0.8'), ovl(gfx.ov_counter, A('P34.2+0.3'), A('P34.2e+0.8'), 1210, 'carts on the 1840 Red River hunt',
                                                  "as counted by Alexander Ross")))
    o.append((A('P37.1-0.2'), A('P37.1e+1.6'), ovl(gfx.ov_big, A('P37.1-0.2'), A('P37.1e+1.6'), 'TENS OF MILLIONS',
                                                     'estimates vary widely; nobody knows exactly')))
    o.append((A('P38.0-0.1'), A('P38.0e+1.0'), ovl(gfx.ov_big, A('P38.0-0.1'), A('P38.0e+1.0'), '1879', 'Canadian plains', 800, T.OCHRE, 120)))
    o.append(lt('William T. Hornaday', 'Naturalist', A('P39.0+0.4'), A('P39.0e')))
    o.append((A('P39.1-0.1'), A('P40.0-0.8'), ovl(gfx.ov_counter, A('P39.1-0.1'), A('P40.0-0.8'), 1091,
                                                   'bison left in North America', "Hornaday's 1889 count")))
    o.append(recon(A('P41.0'), A('P41.0e'), 'Reconstruction'))
    return o


OVERLAYS = None


def overlays():
    global OVERLAYS
    if OVERLAYS is None:
        OVERLAYS = build_overlays()
    return OVERLAYS


def resolved():
    """List of dicts: start, end, shot, xfade (seconds)."""
    total = core.timing()['total']
    out = []
    for i, (st, shot, xf) in enumerate(CLIPS):
        s = A(st)
        e = A(CLIPS[i + 1][0]) if i + 1 < len(CLIPS) else total
        out.append(dict(start=s, end=e, shot=shot, xfade=xf, anchor=st))
    for a, b in zip(out, out[1:]):
        assert b['start'] > a['start'], (a['anchor'], b['anchor'], a['start'], b['start'])
    return out
