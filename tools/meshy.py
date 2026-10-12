"""Crea una figura con Meshy (texto -> 3D) y la deja lista en la cola.

Uso: python tools/meshy.py --slug ronin-samurai --height 90 --price 5.99 \
        --name "Ronin Samurai Figure ..." --prompt "original masculine ronin ..." [--tags a,b,c]

Necesita MESHY_API_KEY en el entorno (secret de GitHub). Mantiene la forma que genera Meshy:
solo repara la malla (une vértices, cierra agujeros, normales), la escala de forma uniforme a
--height mm y la apoya en z=0. No simplifica ni esculpe. Si la malla no queda cerrada y de una
sola pieza, falla y no deja nada en la cola.
"""
import argparse
import os
import pathlib
import sys
import time

import requests
import trimesh
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
API = "https://api.meshy.ai/openapi/v2/text-to-3d"


def generar(prompt, key, espera_max=1800):
    h = {"Authorization": f"Bearer {key}"}
    r = requests.post(API, headers=h, timeout=60, json={
        "mode": "preview", "prompt": prompt, "art_style": "realistic", "should_remesh": True})
    r.raise_for_status()
    tid = r.json()["result"]
    t0 = time.time()
    while time.time() - t0 < espera_max:
        d = requests.get(f"{API}/{tid}", headers=h, timeout=60).json()
        print(f"  meshy {tid}: {d.get('status')} {d.get('progress', 0)}%", flush=True)
        if d["status"] == "SUCCEEDED":
            return d["model_urls"]
        if d["status"] in ("FAILED", "CANCELED"):
            sys.exit(f"Meshy falló: {d.get('task_error')}")
        time.sleep(15)
    sys.exit("Meshy: tiempo agotado")


def preparar(url, destino, altura):
    glb = destino.with_suffix(".glb")
    glb.write_bytes(requests.get(url, timeout=300).content)
    m = trimesh.load(glb, force="mesh")
    m.merge_vertices()
    m.update_faces(m.nondegenerate_faces())
    trimesh.repair.fix_normals(m)
    trimesh.repair.fill_holes(m)
    if not m.is_watertight:
        sys.exit("La malla de Meshy no quedó cerrada: probá otro prompt o semilla.")
    partes = m.split(only_watertight=False)
    if len(partes) > 1:  # se queda con la pieza principal; descarta motas flotantes
        m = max(partes, key=lambda x: x.volume)
    m.apply_scale(altura / m.extents[2])  # escala uniforme: la forma no cambia
    m.apply_translation([-m.bounds[:, 0].mean(), -m.bounds[:, 1].mean(), -m.bounds[0][2]])
    m.export(destino)
    glb.unlink()
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--height", type=float, default=90)
    ap.add_argument("--price", type=float, default=5.99)
    ap.add_argument("--tags", default="figure,miniature,fantasy,tabletop,original design")
    a = ap.parse_args()
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        sys.exit("Falta MESHY_API_KEY.")
    urls = generar(a.prompt, key)
    rel = pathlib.Path("figures") / a.slug
    (ROOT / rel).mkdir(parents=True, exist_ok=True)
    stl = rel / f"{a.slug}_{int(a.height)}mm.stl"
    m = preparar(urls["glb"], ROOT / stl, a.height)
    n = max([int(p.name[:3]) for p in (ROOT / "queue").glob("[0-9][0-9][0-9]-*.yaml")] or [0]) + 1
    item = dict(
        slug=a.slug, variants=[dict(file=stl.name, source=stl.as_posix())],
        display_rotate=[0, 0, 0], render_angles=[35, 70], render_colors=["#6E6E78", "#8C1C2B"],
        cover_badge=f"Original figure · {int(a.height)} mm tall", print_settings=[
            "0.12-0.16 mm layers", "Tree supports recommended", "Resin or FDM", "Paint-ready surface"],
        name=a.name, price=a.price, currency="USD", category="Art", subcategory="",
        tags=[t.strip() for t in a.tags.split(",")][:20],
        description=(f"{a.name}\n\nOriginal figure, {int(a.height)} mm tall, designed with AI assistance "
                     "and checked for a closed, single-piece mesh. Not affiliated with any brand or character.\n\n"
                     "**Print settings**\n- 0.12-0.16 mm layers\n- Tree supports recommended\n- Works on resin and FDM"))
    (ROOT / "queue" / f"{n:03d}-{a.slug}.yaml").write_text(
        yaml.safe_dump(item, sort_keys=False, allow_unicode=True, width=100), encoding="utf-8")
    print(f"OK: queue/{n:03d}-{a.slug}.yaml ({[round(float(x), 1) for x in m.extents]} mm)")


if __name__ == "__main__":
    main()
