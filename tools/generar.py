"""Genera productos nuevos a partir del análisis de mercado.

Lee nichos_sin_cubrir.csv (lo arma priorizar.py) y lo cruza con la biblioteca de
plantillas paramétricas de templates/. Por cada nicho rentable que coincide con una
plantilla que todavía no está en la cola ni publicada:
  - crea la ficha en queue/ (título, descripción, tags, precio, variantes);
  - agrega el tag del nicho a la ficha si no lo tenía;
  - ajusta el precio a la mediana del nicho (dentro de un rango razonable).
Los nichos sin plantilla van a nichos_para_disenar.csv: esa lista es para Claude.

Uso: python tools/generar.py [--max 3] [--sin-precio]
"""
import argparse
import pathlib
import re

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PRECIO_MIN, PRECIO_MAX = 1.49, 4.99


def tokens(texto):
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w
            for w in re.findall(r"[a-z0-9]+", str(texto).lower())}


def coincide(nicho, keywords):
    tn = tokens(nicho)
    return any(tokens(k) and (tokens(k) <= tn or tn <= tokens(k)) for k in keywords)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3, help="máximo de productos nuevos por corrida")
    ap.add_argument("--sin-precio", action="store_true", help="no ajustar el precio al mercado")
    a = ap.parse_args()

    csv = ROOT / "nichos_sin_cubrir.csv"
    if not csv.exists():
        raise SystemExit("Falta nichos_sin_cubrir.csv: corré antes `python agente.py priorizar`.")
    try:
        nichos = pd.read_csv(csv)
    except pd.errors.EmptyDataError:
        nichos = pd.DataFrame(columns=["tag"])
    existentes = {yaml.safe_load(p.read_text(encoding="utf-8"))["slug"]
                  for p in list((ROOT / "queue").glob("*.yaml")) + list((ROOT / "published").glob("*.yaml"))}
    plantillas = [yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted((ROOT / "templates").glob("*.yaml"))]
    siguiente = max([int(p.name[:3]) for p in (ROOT / "queue").glob("[0-9][0-9][0-9]-*.yaml")] or [0]) + 1

    creados, sin_plantilla, usadas = [], [], set()
    for _, n in nichos.iterrows():
        nicho = str(n["tag"])
        saturado = str(n.get("saturado", False)).strip().lower() == "true"
        candidatas = [t for t in plantillas if coincide(nicho, t["keywords"]) and not t.get("temporada")]
        if saturado:
            # nicho lleno de oferta gratis: solo sirven plantillas diferenciadas
            dif = [t for t in candidatas if t.get("diferenciado")]
            if candidatas and not dif:
                print(f"  ! {nicho}: nicho saturado de diseños gratis; la plantilla básica no se publica."
                      " Hace falta una versión diferenciada.")
            candidatas = dif
        else:
            candidatas.sort(key=lambda t: bool(t.get("diferenciado")))  # sin saturar: primero la básica
        pendientes = [t for t in candidatas if t["item"]["slug"] not in existentes | usadas]
        match = pendientes[0] if pendientes else None
        if not match:
            if not candidatas:
                sin_plantilla.append(n)
            continue
        item = dict(match["item"])
        if len(creados) >= a.max:
            continue
        if nicho.lower() not in [t.lower() for t in item["tags"]]:
            item["tags"] = [nicho.lower()] + item["tags"][:19]
        if not a.sin_precio and float(item.get("price", 0)) > 0 and pd.notna(n.get("precio_mediano_usd")):
            item["price"] = round(min(PRECIO_MAX, max(PRECIO_MIN, float(n["precio_mediano_usd"]) * 0.9)), 2)
        destino = ROOT / "queue" / f"{siguiente:03d}-{item['slug']}.yaml"
        destino.write_text(yaml.safe_dump(item, allow_unicode=True, sort_keys=False), encoding="utf-8")
        usadas.add(item["slug"])
        creados.append((nicho, destino.name, item["price"]))
        siguiente += 1

    for nicho, archivo, precio in creados:
        print(f"  + {archivo}  (nicho: {nicho}, precio USD {precio})")
    if not creados:
        print("  No hay plantillas nuevas que coincidan con los nichos rentables.")
    out = ROOT / "nichos_para_disenar.csv"
    pd.DataFrame(sin_plantilla).to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n{len(sin_plantilla)} nichos sin plantilla -> {out.name} (pasáselo a Claude para diseñar)")
    if creados:
        print("Corré `python agente.py construir queue/<archivo>` para revisar los STL e imágenes antes de subir.")


if __name__ == "__main__":
    main()
