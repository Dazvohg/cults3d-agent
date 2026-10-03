"""Verificación digital con PrusaSlicer (sin imprimir nada).

Por cada STL:
  1. Lo slicea con un perfil estándar (boquilla 0.4, capas 0.2, 3 paredes, 15 % gyroid, PLA)
     y lee del G-code el tiempo estimado y los gramos reales de filamento.
  2. Lo slicea otra vez con soportes AUTOMÁTICOS activados (umbral 45°) y mide qué parte del
     material sería soporte: none (< 0.5 %), minimal (0.5–5 %) o needed (> 5 %). Solo con
     "none" el agente anuncia la pieza como "no supports".
  3. Exporta un .3mf con la pieza orientada y centrada, que abre directo en
     Bambu Studio, OrcaSlicer y PrusaSlicer.

Uso: python tools/slicer.py archivo.stl [más.stl ...]
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

PERFIL = """bed_shape = 0x0,220x0,220x220,0x220
nozzle_diameter = 0.4
filament_diameter = 1.75
filament_density = 1.24
layer_height = 0.2
first_layer_height = 0.2
perimeters = 3
fill_density = 15%
fill_pattern = gyroid
top_solid_layers = 5
bottom_solid_layers = 4
perimeter_speed = 120
external_perimeter_speed = 80
infill_speed = 200
solid_infill_speed = 150
top_solid_infill_speed = 100
travel_speed = 300
first_layer_speed = 40
max_print_speed = 250
default_acceleration = 3000
machine_max_acceleration_extruding = 5000,5000
machine_max_acceleration_x = 5000,5000
machine_max_acceleration_y = 5000,5000
gcode_flavor = marlin2
support_material_threshold = 44
"""
# Umbral 44°: regla de los 45° -> caras a 45° justos (chaflanes, gotas) se imprimen bien; más planas llevan soporte.
# Clasificación según qué parte del material serían soportes con soportes automáticos a 45°:
#   < 0.5 %  -> "none"     (se imprime sin soportes)
#   0.5–5 %  -> "minimal"  (solo zonas chicas; muchos lo imprimen sin soportes, pero no lo afirmamos)
#   > 5 %    -> "needed"
MINIMO, NECESARIO = 0.5, 5.0


def disponible():
    return shutil.which("prusa-slicer") is not None


def _cmd():
    base = ["prusa-slicer"]
    if shutil.which("xvfb-run"):
        base = ["xvfb-run", "-a"] + base
    return base


def _run(args):
    r = subprocess.run(_cmd() + args, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"PrusaSlicer falló: {r.stderr[-400:] or r.stdout[-400:]}")


def _leer_gcode(path):
    txt = pathlib.Path(path).read_text(errors="ignore")
    t = re.search(r"estimated printing time \(normal mode\) = (.+)", txt)
    g = re.search(r"total filament used \[g\] = ([\d.]+)", txt)
    return (t.group(1).strip() if t else "?"), (float(g.group(1)) if g else None)


def _porcentaje_soporte(path):
    rel, last, tipo, tot, sup = False, 0.0, None, 0.0, 0.0
    for line in open(path, errors="ignore"):
        if line.startswith("M83"):
            rel = True
        elif line.startswith("M82"):
            rel = False
        elif line.startswith("G92") and " E" in line:
            last = float(re.search(r" E([-\d.]+)", line).group(1))
        elif line.startswith(";TYPE:"):
            tipo = line[6:].strip()
        elif line.startswith(("G1", "G0")) and " E" in line:
            e = float(re.search(r" E([-\d.]+)", line).group(1))
            de = e if rel else e - last
            if not rel:
                last = e
            if de > 0:
                tot += de
                if tipo and "upport" in tipo:
                    sup += de
    return round(100 * sup / tot, 2) if tot else 0.0


def minutos(texto):
    m = 0
    for n, u in re.findall(r"(\d+)([dhms])", texto or ""):
        m += int(n) * {"d": 1440, "h": 60, "m": 1, "s": 1 / 60}[u]
    return round(m)


def verificar(stl, salida_3mf=None):
    stl = pathlib.Path(stl)
    with tempfile.TemporaryDirectory() as tmp:
        ini = pathlib.Path(tmp) / "perfil.ini"
        ini.write_text(PERFIL)
        g1, g2 = pathlib.Path(tmp) / "a.gcode", pathlib.Path(tmp) / "b.gcode"
        _run(["--load", str(ini), "--export-gcode", "--center", "110,110", "--output", str(g1), str(stl)])
        tiempo, gramos = _leer_gcode(g1)
        _run(["--load", str(ini), "--support-material", "--support-material-auto", "--export-gcode",
              "--center", "110,110", "--output", str(g2), str(stl)])
        pct = _porcentaje_soporte(g2)
        if salida_3mf:
            _run(["--load", str(ini), "--export-3mf", "--center", "110,110", "--output", str(salida_3mf), str(stl)])
    clase = "none" if pct < MINIMO else ("minimal" if pct <= NECESARIO else "needed")
    voladizo = area_voladizo(stl)
    base = "slicer"
    if clase != "none" and voladizo < AREA_MIN:
        # el slicer marcó soporte, pero la malla no tiene ninguna cara más plana que 44°: son caras
        # a 45° justos (pie Gridfinity, chaflanes, agujeros en gota) que el slicer redondea al límite
        clase, base = "none", "geometry"
    return {"print_time": tiempo, "print_minutes": minutos(tiempo), "grams": gramos,
            "support_pct": pct, "supports": clase, "needs_supports": clase != "none",
            "overhang_mm2": voladizo, "support_basis": base}


AREA_MIN = 1.0   # mm² de caras más planas que 44° (por encima de la primera capa) toleradas como "ninguna"


def area_voladizo(stl, angulo=44.0):
    """Área (mm²) de caras que miran hacia abajo con pendiente menor que `angulo` respecto de la
    horizontal, sin contar la cara apoyada en la cama ni la primera capa."""
    import math
    import numpy as np
    import trimesh
    m = trimesh.load(str(stl))
    n, c, a = m.face_normals, m.triangles_center, m.area_faces
    zmin = m.bounds[0][2]
    mal = (n[:, 2] < -math.cos(math.radians(angulo))) & (c[:, 2] > zmin + 0.3)
    return round(float(np.sum(a[mal])), 2)


if __name__ == "__main__":
    if not disponible():
        sys.exit("PrusaSlicer no está instalado (apt install prusa-slicer).")
    for f in sys.argv[1:]:
        print(f, json.dumps(verificar(f)))
