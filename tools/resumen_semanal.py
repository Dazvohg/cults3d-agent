"""Resumen del análisis semanal (lo usa .github/workflows/semanal.yml).

Lee cults3d_mercado.xlsx, nichos_para_disenar.csv y la cola, y escribe reportes/RESUMEN.md.
Ese mismo texto aparece en la pestaña Actions de GitHub (resumen del run).

Uso: python tools/resumen_semanal.py [--nuevos a.yaml,b.yaml] [--rechazados c.yaml]
"""
import argparse
import datetime as dt
import pathlib

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def tabla(df, cols, n):
    df = df[[c for c in cols if c in df.columns]].head(n)
    if df.empty:
        return "_(sin datos)_\n"
    filas = ["| " + " | ".join(df.columns) + " |", "|" + "---|" * len(df.columns)]
    for _, r in df.iterrows():
        filas.append("| " + " | ".join(str(r[c]) for c in df.columns) + " |")
    return "\n".join(filas) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nuevos", default="")
    ap.add_argument("--rechazados", default="")
    a = ap.parse_args()
    out = [f"# Análisis semanal Cults3D – {dt.date.today():%d/%m/%Y}\n"]

    xlsx = ROOT / "cults3d_mercado.xlsx"
    if xlsx.exists():
        res = pd.read_excel(xlsx, sheet_name="resumen")
        out.append("## Mercado (últimos 90 días)\n")
        out.append(tabla(res, ["métrica", "valor"], 20))
        tags = pd.read_excel(xlsx, sheet_name="tags")
        if "propiedad_intelectual_ajena" in tags.columns:
            tags = tags[~tags["propiedad_intelectual_ajena"].astype(bool)]
        out.append("\n## Top 10 nichos por oportunidad\n")
        out.append(tabla(tags, ["tag", "disenos", "ventas_por_dia_mediana", "precio_mediano_usd",
                                "pct_gratis", "saturado", "indice_oportunidad"], 10))

    nuevos = [x for x in a.nuevos.split(",") if x]
    out.append("\n## Productos nuevos agregados a la cola\n")
    out.append("\n".join(f"- {pathlib.Path(x).stem.split('-', 1)[-1]}" for x in nuevos) + "\n" if nuevos else "Ninguno esta semana.\n")
    rech = [x for x in a.rechazados.split(",") if x]
    if rech:
        out.append("\n## Rechazados por el control de calidad (movidos a rechazados/)\n")
        out.append("\n".join(f"- {pathlib.Path(x).name}" for x in rech) + "\n")

    cola = sorted((ROOT / "queue").glob("*.yaml"))
    out.append(f"\n## Cola de publicación ({len(cola)} productos; los primeros 5)\n")
    for f in cola[:5]:
        it = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        out.append(f"- {f.name}: {it.get('name', '?')} (USD {it.get('price', 0)})")
    out.append("")

    csv = ROOT / "nichos_para_disenar.csv"
    if csv.exists() and csv.stat().st_size > 5:
        nd = pd.read_csv(csv)
        out.append("\n## Nichos rentables sin plantilla (pasáselos a Claude para diseñar)\n")
        out.append(tabla(nd, ["tag", "nicho", "disenos", "ventas_por_dia_mediana", "precio_mediano_usd",
                              "saturado", "indice_oportunidad"], 10))

    texto = "\n".join(out)
    (ROOT / "reportes").mkdir(exist_ok=True)
    (ROOT / "reportes" / "RESUMEN.md").write_text(texto, encoding="utf-8")
    print(texto)


if __name__ == "__main__":
    main()
