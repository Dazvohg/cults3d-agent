#!/usr/bin/env python3
"""Radar de nichos v4: encuentra nichos funcionales con demanda y poca competencia.

Qué descubrimos (esquema real de la API, 24/10/2026): creationsBatch NO tiene búsqueda por texto. Acepta
categorySlugEn, onlyFree, onlyPriced, submittedAfter/Before, sort, direction, limit y offset.
El top 500 general es 85 % Art, por eso no veía nada funcional. Solución: bajar muestras POR CATEGORÍA funcional
(Home, Gadget, Tool, Game, Various...) pagas y gratis, y analizarlas acá:
  1. Mide cada semilla de specs/semillas_nichos.txt (demanda, competencia paga, competencia gratis, precio).
  2. DESCUBRE etiquetas con buena demanda aunque no estén en la lista de semillas.
Excluye IP ajena, Art, audiencia propia (conversión > 20 %) y diseños de menos de 14 días.

Modos:
  python tools/radar_nichos.py            baja las muestras de la API (CULTS_USERNAME / CULTS_API_KEY) y las guarda en reportes/cults3d_funcional.csv
  python tools/radar_nichos.py --offline  usa lo ya guardado (reportes/cults3d_funcional.csv o cults3d_mercado.xlsx)
  python tools/radar_nichos.py --schema   solo guarda los argumentos de creationsBatch
Salida: reportes/radar_nichos.md, reportes/radar_nichos.csv, reportes/radar_descubiertos.csv, reportes/radar_error.txt si algo falla.
Es descriptivo: no hay volumen de búsquedas; vistas/día de los mejores resultados es un proxy de demanda.
"""
import argparse
import datetime as dt
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
CACHE = REP / "cults3d_funcional.csv"
TOP_N = 20
CONV_AUDIENCIA = 0.20
DIAS = 180
POR_CATEGORIA = 500
CATEGORIAS = ["home", "gadget", "tool", "game", "various", "fashion", "jewelry", "architecture"]
FIELDS = """identifier name(locale: EN) publishedAt price(currency: USD) { value }
  downloadsCount likesCount viewsCount tags(locale: EN) category { name(locale: EN) }"""
CREADOR = " creator { nick }"   # si la API no lo acepta, se baja sin creador
ESTACIONAL = ("halloween", "spooky", "ghost", "christmas", "xmas", "advent", "easter", "valentine", "pumpkin", "witch", "skull", "death")


def semillas():
    out = []
    if SEMILLAS.exists():
        out = [l.strip() for l in SEMILLAS.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
    p = REP / "ventas_propias.xlsx"
    if p.exists():  # tags de lo que ya vendió
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


IP_EXTRA = ["green lantern", "ork", "orks", "elvis", "gta", "gta 6", "vice city", "playmobil", "kinder", "frieren", "lego",
            "boca juniors", "river plate", "peñarol", "penarol", "club nacional", "racing club", "independiente", "san lorenzo",
            "real madrid", "barcelona", "messi", "copa do mundo", "fifa", "nfl", "nba", "hot wheels", "stlflix"]


def es_ip(texto):
    from analizador_v2 import IP_TERMS
    t = texto.lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(k)}(?![a-z0-9])", t) for k in list(IP_TERMS) + IP_EXTRA)


def preparar(df):
    """Agrega tasas diarias, conversión y marca de IP."""
    df = df.copy()
    df["dias"] = (pd.Timestamp.now(tz="UTC") - pd.to_datetime(df["publicado"], utc=True)).dt.days.clip(lower=1)
    df["v_dia"] = df["vistas"] / df["dias"]
    df["dl_dia"] = df["descargas"] / df["dias"]
    df["conv"] = df["descargas"] / df["vistas"].clip(lower=1)
    df["tags"] = df["tags"].fillna("")
    df["ip"] = df.apply(lambda r: es_ip(f"{r['nombre']} {r['tags']}"), axis=1)
    df["gratis"] = df["precio"].fillna(0) <= 0
    return df


def organicos(df):
    return df[~df["ip"] & ~df["gratis"] & (df["categoria"] != "Art") & (df["conv"] <= CONV_AUDIENCIA) & (df["dias"] >= 14)]


def coincide(df, termino):
    t = rf"(?<![a-z0-9]){re.escape(termino.lower())}(?![a-z0-9])"   # palabra completa: "mate" no cuenta "ultimate"
    return df[df["nombre"].str.lower().str.contains(t, regex=True) | df["tags"].str.lower().str.contains(t, regex=True)]


def puntuar(termino, df):
    m = coincide(df, termino)
    org = organicos(m)
    gratis = int((m["gratis"] & ~m["ip"]).sum())
    if org.empty:
        return dict(termino=termino, pagos=len(m[~m["gratis"]]), organicos=0, gratis=gratis, demanda_v_dia=0, dl_dia=0,
                    precio=0, conv=0, oportunidad=0, veredicto="SIN DATOS")
    top = org.sort_values("v_dia", ascending=False).head(TOP_N)
    dem = float(top["v_dia"].median())
    opp = dem / (1 + len(org) / 10)
    if len(org) < 3:
        ver = "POCOS DATOS"
    elif dem >= 15 and len(org) <= 60:
        ver = "APOSTAR"
    elif dem >= 5:
        ver = "PROBAR"
    else:
        ver = "EVITAR"
    return dict(termino=termino, pagos=len(m[~m["gratis"]]), organicos=len(org), gratis=gratis, demanda_v_dia=round(dem, 1),
                dl_dia=round(float(top["dl_dia"].median()), 2), precio=round(float(top["precio"].median()), 2),
                conv=round(float(top["conv"].median()) * 100, 1), oportunidad=round(opp, 2), veredicto=ver)


def descubrir(df):
    """Etiquetas con >= 3 orgánicos pagos, ordenadas por descargas/día; muestra también cuántos gratis hay."""
    from analizador_v2 import TAGS_GENERICOS
    org = organicos(df).copy()
    org["tag"] = org["tags"].str.lower().str.split(r"\s*,\s*")
    ex = org.explode("tag")
    ex = ex[(ex["tag"].fillna("") != "") & ~ex["tag"].isin(TAGS_GENERICOS)]
    if "creador" not in ex.columns:
        ex["creador"] = ""
    ex["creador"] = ex["creador"].fillna("")
    g = ex.groupby("tag").agg(organicos=("nombre", "nunique"), creadores=("creador", "nunique"), dl_dia=("dl_dia", "median"),
                              v_dia=("v_dia", "median"), precio=("precio", "median")).reset_index()
    tiene_creador = ex["creador"].str.len().gt(0).any()
    # un solo creador con 3 diseños que comparten etiquetas no es un nicho
    g = g[(g["organicos"] >= 5) & ((g["creadores"] >= 3) if tiene_creador else True)]
    if not tiene_creador:
        g["creadores"] = "–"
    libres = df[df["gratis"] & ~df["ip"]].copy()
    libres["tag"] = libres["tags"].str.lower().str.split(r"\s*,\s*")
    nl = libres.explode("tag").groupby("tag")["nombre"].nunique()
    g["gratis"] = g["tag"].map(nl).fillna(0).astype(int)
    g["estacional"] = g["tag"].apply(lambda t: any(k in t for k in ESTACIONAL))
    g["oportunidad"] = (g["v_dia"] / (1 + g["organicos"] / 10)).round(2)
    return g.sort_values("oportunidad", ascending=False)


def esquema(api):
    info = {"metodo": "", "creationsBatch_args": [], "sort_values": [], "pruebas": {}}
    try:
        sch = api.q("{ __schema { queryType { name fields { name args { name } } } } }").get("__schema")
        cb = next((f for f in (sch or {}).get("queryType", {}).get("fields", []) if f["name"] == "creationsBatch"), None)
        if cb:
            info["metodo"] = "introspeccion"
            info["creationsBatch_args"] = [x["name"] for x in cb["args"]]
    except (Exception, SystemExit) as e:  # noqa: BLE001
        info["pruebas"]["introspeccion"] = str(e)[:300]
    (REP / "schema_creationsBatch.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
    print("creationsBatch:", info)
    return info


def _fila(r):
    return dict(nombre=r["name"], publicado=r["publishedAt"], precio=(r["price"] or {}).get("value", 0),
                descargas=r["downloadsCount"], likes=r["likesCount"], vistas=r["viewsCount"],
                tags=", ".join(r.get("tags") or []), categoria=(r.get("category") or {}).get("name", ""),
                creador=(r.get("creator") or {}).get("nick", ""))


def bajar(api, slug, gratis, maximo, campos=None):
    campos = campos or FIELDS + CREADOR
    desde = (dt.datetime.utcnow() - dt.timedelta(days=DIAS)).strftime("%Y-%m-%dT00:00:00+00:00")
    filtro = "onlyFree: true" if gratis else "onlyPriced: true"
    rows, off = [], 0
    while off < maximo:
        q = (f'{{ creationsBatch(sort: BY_DOWNLOADS, {filtro}, categorySlugEn: "{slug}", submittedAfter: "{desde}", '
             f'limit: 100, offset: {off}) {{ results {{ {campos} }} }} }}')
        res = api.q(q)["creationsBatch"]["results"]
        rows += [_fila(r) for r in res]
        if len(res) < 100:
            break
        off += 100
        time.sleep(0.7)
    return rows


def muestra_api(api):
    filas, log = [], []
    for slug in CATEGORIAS:
        for gratis, maximo in ((False, POR_CATEGORIA), (True, 300)):
            try:
                try:
                    r = bajar(api, slug, gratis, maximo)
                except (Exception, SystemExit) as e:  # noqa: BLE001
                    if "creator" not in str(e).lower():
                        raise
                    global CREADOR
                    CREADOR = ""
                    log.append("la API no acepta creator { nick }: sigo sin creador")
                    r = bajar(api, slug, gratis, maximo, FIELDS)
                filas += r
                log.append(f"{slug} {'gratis' if gratis else 'pagos'}: {len(r)}")
            except (Exception, SystemExit) as e:  # noqa: BLE001
                log.append(f"{slug} {'gratis' if gratis else 'pagos'}: ERROR {str(e)[:120]}")
    print("\n".join(log))
    (REP / "radar_log.txt").write_text("\n".join(log), encoding="utf-8")
    return pd.DataFrame(filas).drop_duplicates(subset=["nombre", "publicado"]) if filas else pd.DataFrame()


def cargar_offline():
    partes = []
    if CACHE.exists():
        partes.append(pd.read_csv(CACHE))
    x = REP / "cults3d_mercado.xlsx"
    if x.exists():
        d = pd.read_excel(x, sheet_name="disenos")
        pub = pd.Timestamp.now(tz="UTC") - pd.to_timedelta(d["dias_online"], unit="D")
        partes.append(pd.DataFrame(dict(nombre=d["nombre"], publicado=pub, precio=d["precio_usd"], descargas=d["descargas"],
                                        likes=d["likes"], vistas=d["vistas"], tags=d["tags"].fillna(""), categoria=d["categoria"])))
    if not partes:
        sys.exit("No hay datos: corré sin --offline o subí reportes/cults3d_mercado.xlsx")
    return pd.concat(partes).drop_duplicates(subset=["nombre"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--schema", action="store_true")
    a = ap.parse_args()
    REP.mkdir(exist_ok=True)
    modo = "datos guardados"
    df = None
    if not a.offline:
        try:
            from analizador_v2 import Api, load_env
            api = Api(*load_env())
            esquema(api)
            if a.schema:
                return
            df = muestra_api(api)
            if len(df) >= 50:
                df.to_csv(CACHE, index=False, encoding="utf-8")
                modo = f"muestra por categoría funcional bajada de Cults ({len(df)} diseños)"
            else:
                (REP / "radar_error.txt").write_text(f"La API devolvió solo {len(df)} diseños; ver reportes/radar_log.txt", encoding="utf-8")
                df = None
        except (Exception, SystemExit) as e:  # noqa: BLE001
            (REP / "radar_error.txt").write_text(f"No pude consultar la API: {e!r}", encoding="utf-8")
            print("Error de la API:", e)
    if df is None:
        df = cargar_offline()
    df = preparar(df)
    res = pd.DataFrame([puntuar(s, df) for s in semillas()]).sort_values("oportunidad", ascending=False)
    res.to_csv(REP / "radar_nichos.csv", index=False)
    desc = descubrir(df)
    desc.to_csv(REP / "radar_descubiertos.csv", index=False)
    org = organicos(df)
    md = [f"# Radar de nichos – {pd.Timestamp.now():%d/%m/%Y}\n", f"Fuente: {modo}. Diseños: {len(df)}; orgánicos copiables: {len(org)}.\n",
          "Demanda = vistas/día mediana de los 20 orgánicos mejor posicionados. Oportunidad = demanda / (1 + orgánicos/10).\n",
          "## Semillas medidas\n",
          "| término | pagos | orgánicos | gratis | vistas/día | desc./día | USD | conv. % | oportunidad | veredicto |", "|---|---|---|---|---|---|---|---|---|---|"]
    for _, r in res.iterrows():
        md.append(f"| {r['termino']} | {r['pagos']} | {r['organicos']} | {r['gratis']} | {r['demanda_v_dia']} | {r['dl_dia']} | {r['precio']} | {r['conv']} | {r['oportunidad']} | {r['veredicto']} |")
    techo = org.groupby("categoria")["dl_dia"].describe(percentiles=[.5, .9])[["count", "50%", "90%"]]
    md += ["\n## Techo del mercado por categoría (orgánicos pagos)\n", "| categoría | diseños | desc./día mediana | desc./día p90 |", "|---|---|---|---|"]
    for cat, r in techo.iterrows():
        md.append(f"| {cat} | {int(r['count'])} | {r['50%']:.2f} | {r['90%']:.2f} |")
    md += ["\n## Etiquetas descubiertas (no estacionales, >= 5 orgánicos pagos de >= 3 creadores)\n",
           "| etiqueta | orgánicos | creadores | gratis | vistas/día | desc./día | USD | oportunidad |", "|---|---|---|---|---|---|---|---|"]
    for _, r in desc[~desc["estacional"]].head(30).iterrows():
        md.append(f"| {r['tag']} | {r['organicos']} | {r['creadores']} | {r['gratis']} | {r['v_dia']:.0f} | {r['dl_dia']:.1f} | {r['precio']:.2f} | {r['oportunidad']} |")
    (REP / "radar_nichos.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:25]))


if __name__ == "__main__":
    sys.exit(main())
