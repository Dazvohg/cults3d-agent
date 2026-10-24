#!/usr/bin/env python3
"""Radar de nichos: busca qué se BUSCA y está mal cubierto, en vez de copiar lo que descarga el top.

Por qué: el top 500 por descargas muestra ganadores con audiencia propia, IP o novedad viral. Un recién llegado
no compite ahí. Las dos ventas reales vinieron de un nicho técnico (escudo para sensores). Este radar prueba
términos concretos (semillas) y mide para cada uno:
  - DEMANDA   : vistas/día de los 20 resultados orgánicos mejor posicionados (sin IP, sin Art, sin audiencia propia)
  - COMPETENCIA: cuántos resultados orgánicos hay y cuánto cobran
  - OPORTUNIDAD = demanda / (1 + resultados orgánicos / 10)   (mucha demanda, pocos competidores)
Marca cada término como APOSTAR / PROBAR / EVITAR y lista qué ya cubrimos.

Modos:
  python tools/radar_nichos.py            consulta la API de Cults (necesita CULTS_USERNAME / CULTS_API_KEY)
  python tools/radar_nichos.py --offline  usa reportes/cults3d_mercado.xlsx (menos preciso, sirve para probar)
  python tools/radar_nichos.py --schema   solo guarda los argumentos reales de creationsBatch (reportes/schema_creationsBatch.json)
Semillas: specs/semillas_nichos.txt (una por línea, # comentarios). Se amplía sola con tags de nuestras ventas.
Salida: reportes/radar_nichos.md y reportes/radar_nichos.csv
Es descriptivo: la API no da búsquedas ni volumen de consultas; el ranking de resultados es un proxy de demanda.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reportes"
SEMILLAS = ROOT / "specs" / "semillas_nichos.txt"
TOP_N = 20
CONV_AUDIENCIA = 0.20
FIELDS = """identifier name(locale: EN) publishedAt price(currency: USD) { value }
  downloadsCount likesCount viewsCount tags(locale: EN) category { name(locale: EN) }"""


def semillas():
    out = []
    if SEMILLAS.exists():
        out = [l.strip() for l in SEMILLAS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    p = REP / "ventas_propias.xlsx"
    if p.exists():  # tags de lo que ya vendió: vecinos de lo único que funciona
        try:
            x = pd.read_excel(p, sheet_name="por_diseno")
            if "ventas" in x.columns and "tags" in x.columns:
                for t in x[x["ventas"] > 0]["tags"].dropna():
                    out += [s.strip().lower() for s in str(t).split(",") if len(s.strip()) > 3]
        except Exception as e:  # noqa: BLE001
            print("  (no pude leer ventas_propias:", e, ")")
    seen, res = set(), []
    for s in out:
        if s.lower() not in seen:
            seen.add(s.lower())
            res.append(s)
    return res


def es_ip(texto):
    from analizador_v2 import IP_TERMS
    t = texto.lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", t) for k in IP_TERMS)


def limpiar(df):
    """Filtra IP, Art y audiencia propia; calcula tasas diarias."""
    if df.empty:
        return df
    df = df.copy()
    df["dias"] = (pd.Timestamp.now(tz="UTC") - pd.to_datetime(df["publicado"], utc=True)).dt.days.clip(lower=1)
    df["v_dia"] = df["vistas"] / df["dias"]
    df["dl_dia"] = df["descargas"] / df["dias"]
    df["conv"] = df["descargas"] / df["vistas"].clip(lower=1)
    ip = df.apply(lambda r: es_ip(f"{r['nombre']} {r['tags']}"), axis=1)
    return df[~ip & (df["categoria"] != "Art") & (df["conv"] <= CONV_AUDIENCIA) & (df["dias"] >= 14)]


def puntuar(termino, df):
    org = limpiar(df)
    if org.empty:
        return dict(termino=termino, resultados=0, organicos=0, demanda_v_dia=0, dl_dia=0, precio=0, conv=0, oportunidad=0, veredicto="SIN DATOS")
    top = org.sort_values("v_dia", ascending=False).head(TOP_N)
    dem = float(top["v_dia"].median())
    opp = dem / (1 + len(org) / 10)
    if len(org) < 3:
        ver = "SIN SEÑAL"
    elif dem >= 15 and len(org) <= 60:
        ver = "APOSTAR"
    elif dem >= 5:
        ver = "PROBAR"
    else:
        ver = "EVITAR"
    return dict(termino=termino, resultados=len(df), organicos=len(org), demanda_v_dia=round(dem, 1),
                dl_dia=round(float(top["dl_dia"].median()), 2), precio=round(float(top["precio"].median()), 2),
                conv=round(float(top["conv"].median()) * 100, 1), oportunidad=round(opp, 2), veredicto=ver)


def esquema(api):
    q = """{ __type(name: "Query") { fields { name args { name type { name kind ofType { name } } } } } }"""
    data = api.q(q)["__type"]["fields"]
    cb = next((f for f in data if f["name"] == "creationsBatch"), None)
    sorts = api.q('{ __type(name: "CreationsSortingEnum") { enumValues { name } } }').get("__type") or {}
    info = {"creationsBatch_args": [a["name"] for a in (cb or {}).get("args", [])],
            "sort_values": [e["name"] for e in sorts.get("enumValues", [])]}
    (REP / "schema_creationsBatch.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    print("creationsBatch acepta:", info)
    return info


def buscar_api(api, termino, tiene_query, maximo=100):
    if not tiene_query:
        return pd.DataFrame()
    rows, off = [], 0
    while off < maximo:
        t = termino.replace('"', "")
        qq = f'{{ creationsBatch(query: "{t}", onlyPriced: true, limit: 100, offset: {off}) {{ results {{ {FIELDS} }} }} }}'
        res = api.q(qq)["creationsBatch"]["results"]
        rows += res
        if len(res) < 100:
            break
        off += 100
        time.sleep(0.5)
    return pd.DataFrame([dict(nombre=r["name"], publicado=r["publishedAt"], precio=(r["price"] or {}).get("value", 0),
                              descargas=r["downloadsCount"], likes=r["likesCount"], vistas=r["viewsCount"],
                              tags=", ".join(r.get("tags") or []), categoria=(r.get("category") or {}).get("name", ""))
                         for r in rows])


def buscar_offline(termino):
    d = pd.read_excel(REP / "cults3d_mercado.xlsx", sheet_name="disenos")
    m = d[d["nombre"].str.lower().str.contains(re.escape(termino.lower())) | d["tags"].fillna("").str.lower().str.contains(re.escape(termino.lower()))]
    pub = pd.Timestamp.now(tz="UTC") - pd.to_timedelta(m["dias_online"], unit="D")
    return pd.DataFrame(dict(nombre=m["nombre"], publicado=pub, precio=m["precio_usd"], descargas=m["descargas"],
                             likes=m["likes"], vistas=m["vistas"], tags=m["tags"].fillna(""), categoria=m["categoria"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--schema", action="store_true")
    a = ap.parse_args()
    REP.mkdir(exist_ok=True)
    api, tiene_query = None, False
    if not a.offline:
        from analizador_v2 import Api, load_env
        api = Api(*load_env())
        info = esquema(api)
        tiene_query = "query" in info["creationsBatch_args"] or "search" in info["creationsBatch_args"]
        if a.schema:
            return
        if not tiene_query:
            print("La API no expone búsqueda por texto en creationsBatch: paso a modo offline con el último análisis.")
            a.offline = True
    filas = []
    for s in semillas():
        df = buscar_offline(s) if a.offline else buscar_api(api, s, tiene_query)
        filas.append(puntuar(s, df))
    res = pd.DataFrame(filas).sort_values("oportunidad", ascending=False)
    res.to_csv(REP / "radar_nichos.csv", index=False)
    md = [f"# Radar de nichos – {pd.Timestamp.now():%d/%m/%Y} ({'offline: muestra del top' if a.offline else 'búsqueda directa en Cults'})\n",
          "Demanda = vistas/día mediana de los 20 orgánicos mejor posicionados. Competencia = orgánicos encontrados. "
          "Oportunidad = demanda / (1 + competencia/10).\n",
          "| término | resultados | orgánicos | vistas/día | desc./día | USD | conv. % | oportunidad | veredicto |", "|---|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        md.append(f"| {r['termino']} | {r['resultados']} | {r['organicos']} | {r['demanda_v_dia']} | {r['dl_dia']} | {r['precio']} | {r['conv']} | {r['oportunidad']} | {r['veredicto']} |")
    (REP / "radar_nichos.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    sys.exit(main())
