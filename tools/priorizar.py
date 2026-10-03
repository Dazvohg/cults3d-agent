"""Une el análisis de mercado con la cola de publicación.

Lee cults3d_mercado.xlsx (generado por analizador_v2.py) y:
  1. Reordena queue/ para que salgan primero los diseños cuyos tags coinciden con los
     nichos que más venden (renombra 001-, 002-, ... según el puntaje).
  2. Genera nichos_sin_cubrir.csv: nichos rentables para los que todavía no hay diseño.
     Esa lista es la que se le pasa a Claude para que diseñe los próximos modelos.

Uso: python tools/priorizar.py [--excel cults3d_mercado.xlsx] [--top 40] [--aplicar]
Sin --aplicar solo muestra el orden propuesto (no renombra nada).
"""
import argparse
import pathlib
import re

import pandas as pd
import yaml

import sys
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from calendario import en_ventana  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]


def cargar_tags(excel, top):
    tags = pd.read_excel(excel, sheet_name="tags")
    tags = tags[~tags["propiedad_intelectual_ajena"].astype(bool)]
    if "disenable" in tags:  # solo nichos de objetos funcionales: figuras y miniaturas no son diseñables acá
        tags = tags[tags["disenable"].astype(bool)]
    orden = ["indice_oportunidad"] if "indice_oportunidad" in tags else ["ventas_por_dia_mediana", "ingreso_estimado_total_usd"]
    tags = tags.sort_values(orden, ascending=False).head(top)
    tags = tags.reset_index(drop=True)
    # peso por posición: el 1° vale top, el último vale 1
    tags["peso"] = len(tags) - tags.index
    return tags


def tokens(texto):
    # singulariza plurales simples para que "miniatures" cubra "miniature"
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in re.findall(r"[a-z0-9]+", str(texto).lower())}


def puntaje(item, tags):
    propios = {" ".join(sorted(tokens(t))) for t in item.get("tags", [])}
    palabras = set().union(*(tokens(t) for t in propios)) | tokens(item.get("name", ""))
    total, matches = 0, []
    for _, r in tags.iterrows():
        tag = str(r["tag"]).lower()
        if " ".join(sorted(tokens(tag))) in propios:
            total += r["peso"] * 2  # coincidencia exacta de tag
            matches.append(tag)
        elif tokens(tag) and tokens(tag) <= palabras:
            total += r["peso"]      # coincidencia por palabras
            matches.append(tag)
    return total, matches


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--excel", default=str(ROOT / "cults3d_mercado.xlsx"))
    ap.add_argument("--top", type=int, default=40)
    ap.add_argument("--aplicar", action="store_true")
    a = ap.parse_args()

    tags = cargar_tags(a.excel, a.top)
    # Tags de tus propios éxitos (los genera ventas.py): lo parecido a lo que ya te vende sube en la cola.
    estrellas = set()
    est_csv = ROOT / "estrellas.csv"
    if est_csv.exists():
        for t in pd.read_csv(est_csv).get("tags", pd.Series(dtype=str)).dropna():
            for tag in str(t).split(","):
                estrellas |= tokens(tag)
    cola = sorted((ROOT / "queue").glob("*.yaml"))
    filas = []
    for p in cola:
        item = yaml.safe_load(p.read_text(encoding="utf-8"))
        s, m = puntaje(item, tags)
        if estrellas:
            comunes = set().union(*(tokens(t) for t in item.get("tags", []))) & estrellas
            if len(comunes) >= 2:
                s += 15
                m.insert(0, "parecido a tus más vendidos")
        if en_ventana(item.get("temporada")):
            s += 1000  # temporada abierta: sale primero sí o sí
            m.insert(0, f"TEMPORADA {item['temporada']}")
        filas.append({"archivo": p, "slug": item["slug"], "puntaje": s, "nichos": ", ".join(m[:6])})
    orden = sorted(filas, key=lambda f: (-f["puntaje"], f["archivo"].name))

    print("Orden propuesto de publicación:")
    for i, f in enumerate(orden, 1):
        print(f"  {i:>2}. {f['slug']:<30} puntaje {f['puntaje']:>4}   {f['nichos'] or '(sin coincidencias)'}")

    # Nichos que ningún diseño (en cola o publicado) cubre
    todos = [yaml.safe_load(p.read_text(encoding="utf-8"))
             for p in list((ROOT / "queue").glob("*.yaml")) + list((ROOT / "published").glob("*.yaml"))]
    cubiertos = set()
    for it in todos:
        for t in it.get("tags", []):
            cubiertos |= tokens(t)
        cubiertos |= tokens(it.get("name", ""))
    sin = tags[~tags["tag"].apply(lambda t: bool(tokens(t)) and tokens(t) <= cubiertos)]
    cols = ["tag", "disenos", "ventas_por_dia_mediana", "precio_mediano_usd", "ingreso_estimado_total_usd",
            "pct_gratis", "saturado", "indice_oportunidad"]
    sin = sin[[c for c in cols if c in sin.columns]]
    salida = ROOT / "nichos_sin_cubrir.csv"
    sin.to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"\n{len(sin)} nichos rentables sin diseño -> {salida.name} (pasáselo a Claude para diseñar)")

    if a.aplicar:
        tmp = []
        for i, f in enumerate(orden, 1):  # renombrado en dos pasos para evitar choques
            t = f["archivo"].with_name(f"_tmp_{i:03d}.yaml")
            f["archivo"].rename(t)
            tmp.append((t, f"{i:03d}-{f['slug']}.yaml"))
        for t, nombre in tmp:
            t.rename(t.with_name(nombre))
        print("Cola reordenada. Subí los cambios de queue/ a GitHub.")


if __name__ == "__main__":
    main()
