"""Control dimensional: mide el STL real (no el código) y lo compara con la medida esperada.

Cada variante de una ficha puede tener `checks:`, por ejemplo:
  checks:
    - {type: bbox, expect: [41.5, 41.5, 25.4], tol: 0.05}           # tamaño total (mm)
    - {type: hole, z: 12, expect: 15.1, tol: 0.15, count: 8}          # agujeros a la altura z
    - {type: outer, z: 0.05, expect: [35.6, 35.6], tol: 0.1}          # contorno exterior a la altura z
    - {type: hole_max, z: 3, expect: 9.36, tol: 0.2}                  # agujero más grande a esa altura
    - {type: fit, z: 100, expect: 134}                                # entra un objeto redondo de Ø134

`hole` mide cada agujero de la sección como su ancho mínimo (= diámetro de un círculo,
= distancia entre caras de un hexágono). `note` es el texto que se publica en la ficha.

Uso: python tools/medidas.py archivo.stl '<json de checks>'
"""
import json
import sys

import numpy as np
import trimesh


def _seccion(mesh, z):
    sec = mesh.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
    if sec is None:
        return []
    planar, _ = sec.to_2D(to_2D=np.array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, -z], [0, 0, 0, 1]], dtype=float))
    return list(planar.polygons_full)


def _ancho_min(poly):
    """Shorter side of the minimum rotated rectangle (= diameter / across-flats)."""
    r = poly.minimum_rotated_rectangle
    xs, ys = r.exterior.coords.xy
    lados = sorted({round(float(np.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i])), 4) for i in range(4)})
    return lados[0], lados[-1]


def medir(mesh, check):
    t = check["type"]
    if t == "bbox":
        return [round(float(v), 3) for v in mesh.extents]
    polys = _seccion(mesh, check["z"])
    if t == "outer":
        return [list(_ancho_min(p)) for p in polys]
    if t == "fit":  # largest round object that fits through each hole (inscribed circle diameter)
        from shapely.geometry import Polygon, Point
        from shapely.ops import polylabel
        res = []
        for p in polys:
            for i in p.interiors:
                hp = Polygon(i)
                c = polylabel(hp, tolerance=0.01)
                res.append(round(2 * hp.exterior.distance(Point(c.x, c.y)), 3))
        return res
    if t in ("hole", "hole_max"):
        from shapely.geometry import Polygon
        holes = [_ancho_min(Polygon(i))[0] for p in polys for i in p.interiors]
        return holes
    raise ValueError(f"check desconocido: {t}")


def verificar(mesh, checks):
    """Returns (ok, results). Each result: dict(check, measured, ok, msg)."""
    out, ok_all = [], True
    for c in checks or []:
        m = medir(mesh, c)
        tol = float(c.get("tol", 0.1))
        exp = c["expect"]
        if c["type"] == "bbox":
            ok = all(abs(a - b) <= tol for a, b in zip(sorted(m), sorted(exp)))
            msg = f"size {m} vs {exp}"
        elif c["type"] == "outer":
            ok = bool(m) and all(abs(w[0] - min(exp)) <= tol and abs(w[1] - max(exp)) <= tol for w in m)
            msg = f"outline at z={c['z']}: {m} vs {exp}"
        elif c["type"] == "hole":
            near = [h for h in m if abs(h - exp) <= max(tol * 4, 1.0)]  # holes of that family
            ok = bool(near) and all(abs(h - exp) <= tol for h in near)
            if "count" in c:
                ok = ok and len(near) == int(c["count"])
            msg = f"{len(near)} holes Ø~{np.mean(near):.2f} at z={c['z']} vs {exp}" if near else f"no hole ~{exp} at z={c['z']} (found {m})"
        elif c["type"] == "fit":
            best = max(m) if m else 0
            ok = best >= exp - tol   # minimum required: a round object of Ø expect must pass
            msg = f"largest round object through the opening at z={c['z']}: Ø{best:.2f} (needs >= {exp})"
        else:  # hole_max
            big = max(m) if m else 0
            ok = abs(big - exp) <= tol
            msg = f"largest hole at z={c['z']}: {big:.2f} vs {exp}"
        ok_all &= ok
        out.append({"check": c, "measured": m if c["type"] != "hole" else sorted(set(round(h, 2) for h in m)),
                    "ok": ok, "msg": msg})
    return ok_all, out


if __name__ == "__main__":
    mesh = trimesh.load(sys.argv[1])
    ok, res = verificar(mesh, json.loads(sys.argv[2]))
    for r in res:
        print(("OK   " if r["ok"] else "FAIL ") + r["msg"])
    sys.exit(0 if ok else 1)
