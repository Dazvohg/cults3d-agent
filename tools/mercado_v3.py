#!/usr/bin/env python3
"""Análisis de mercado v3: mira lo que PUEDE copiarse, no lo que vende el top con audiencia propia.

Por qué existe: en el top 500 de Cults, ~46 % de los diseños tiene conversión > 20 % (descargas / vistas).
Eso no es un buen listado: son creadores con seguidores o suscriptores que descargan solos. Medir contra ellos
da nichos que un recién llegado no puede alcanzar. Este análisis:

  1. Saca IP ajena, la categoría Art y los diseños con "audiencia propia" (conversión > 20 %).
  2. Compara el ALCANCE (vistas por día) de lo que queda contra el de tus fichas.
  3. Busca qué tienen en común los que despegaron rápido (<= 45 días, >= 100 descargas): etiquetas, precio, rasgos.
  4. Marca lo estacional, y lo que ya cubrís vos.

Uso:  python tools/mercado_v3.py            (lee reportes/cults3d_mercado.xlsx y reportes/ventas_propias.xlsx)
Salida: reportes/mercado_v3.md y reportes/mercado_v3_tags.csv
Es descriptivo: el top 500 solo muestra ganadores, no cuántos fracasaron. Sirve para elegir dónde apostar, no para prometer ventas.
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REP = ROOT / "reportes"
CONV_AUDIENCIA = 0.20      # conversión por encima de esto = seguidores/suscriptores, no mercado abierto
DIAS_DESPEGUE = 45         # "despegó rápido": publicado hace <= 45 días ...
DESCARGAS_DESPEGUE = 100   # ... y con >= 100 descargas
MIN_DISENOS_TAG = 3
ESTACIONAL = ("halloween", "spooky", "ghost", "christmas", "xmas", "advent", "easter", "valentine", "pumpkin",
              "witch", "skull", "death", "mood ghost")
RASGOS = ("print in place", "articulated", "flexi", "ams", "multi-part", "multicolor", "customizable", "modular",
          "no support", "mate", "clicker", "fidget", "magnet", "keychain", "holder", "organizer", "candle", "tealight")


def cargar():
    d = pd.read_excel(REP / "cults3d_mercado.xlsx", sheet_name="disenos")
    d["tags_l"] = d["tags"].fillna("").str.lower().str.split(r"\s*,\s*")
    d["nombre_l"] = d["nombre"].str.lower()
    d["v_dia"] = d["vistas"] / d["dias_online"].clip(lower=1)
    d["dl_dia"] = d["descargas"] / d["dias_online"].clip(lower=1)
    return d


def propios():
    p = REP / "ventas_propias.xlsx"
    if not p.exists():
        return None
    x = pd.read_excel(p, sheet_name="por_diseno")
    x = x[x["precio_usd"] > 0]
    x["v_dia"] = x["vistas"] / x["dias_online"].clip(lower=1)
    return x


def tiene_rasgo(row, rasgo):
    return rasgo in row["nombre_l"] or any(rasgo in t for t in row["tags_l"])


def main():
    d = cargar()
    n0 = len(d)
    ip = d["tiene_ip_ajena"].fillna(False).astype(bool)
    aud = d["conversion"] > CONV_AUDIENCIA
    art = d["categoria"].eq("Art")
    org = d[~ip & ~aud & ~art].copy()
    despega = org[(org["dias_online"] <= DIAS_DESPEGUE) & (org["descargas"] >= DESCARGAS_DESPEGUE)]
    out = []
    out.append(f"# Mercado v3 – {pd.Timestamp.now():%d/%m/%Y}\n")
    out.append("## 1. Cuánto del top es copiable\n")
    out.append("| grupo | diseños | % |\n|---|---|---|")
    for nom, m in (("IP ajena", ip), ("Art (figuras/bustos)", art & ~ip), ("Audiencia propia (conv. > 20 %)", aud & ~ip & ~art),
                   ("Orgánicos copiables (resto)", ~ip & ~aud & ~art)):
        out.append(f"| {nom} | {int(m.sum())} | {m.mean() * 100:.0f} % |")
    out.append(f"\nSobre {n0} diseños analizados. Los orgánicos son el único grupo comparable con una tienda nueva.\n")

    out.append("## 2. Alcance: vistas por día\n")
    mp = propios()
    out.append(f"- Orgánicos del top: mediana {org['v_dia'].median():.0f} vistas/día, {org['dl_dia'].median():.1f} descargas/día, "
               f"conversión mediana {org['conversion'].median() * 100:.1f} %, precio mediano USD {org['precio_usd'].median():.2f}.")
    if mp is not None and len(mp):
        vm = mp[mp["dias_online"] >= 5]["v_dia"].median()
        out.append(f"- Tus fichas pagas (>= 5 días): mediana {vm:.1f} vistas/día (incluye el pico de lanzamiento, así que es una cota alta).")
        out.append(f"- Diferencia: ~{org['v_dia'].median() / max(vm, 0.1):.0f} veces. Tu problema principal es llegar a la gente, no el diseño.")
    out.append("")

    out.append(f"## 3. Los que despegaron rápido (<= {DIAS_DESPEGUE} días, >= {DESCARGAS_DESPEGUE} descargas): {len(despega)}\n")
    out.append("| nombre | días | USD | descargas | vistas | likes |\n|---|---|---|---|---|---|")
    for _, r in despega.sort_values("descargas", ascending=False).head(25).iterrows():
        out.append(f"| {r['nombre'][:60]} | {int(r['dias_online'])} | {r['precio_usd']:.2f} | {int(r['descargas'])} | {int(r['vistas'])} | {int(r['likes'])} |")
    out.append("")

    out.append("## 4. Rasgos que se repiten (descargas/día vs. el resto de los orgánicos)\n")
    base = org["dl_dia"].median()
    out.append(f"Base: mediana {base:.1f} descargas/día.\n\n| rasgo | diseños | desc./día | veces la base | precio med. |\n|---|---|---|---|---|")
    filas = []
    for rg in RASGOS:
        m = org[org.apply(lambda r: tiene_rasgo(r, rg), axis=1)]
        if len(m) >= MIN_DISENOS_TAG:
            filas.append((m["dl_dia"].median() / base, rg, len(m), m["dl_dia"].median(), m["precio_usd"].median()))
    for lift, rg, n, v, pr in sorted(filas, reverse=True):
        out.append(f"| {rg} | {n} | {v:.1f} | {lift:.1f}x | {pr:.2f} |")
    out.append("")

    ex = org.explode("tags_l")
    g = ex.groupby("tags_l").agg(disenos=("nombre", "nunique"), dl_dia=("dl_dia", "median"), v_dia=("v_dia", "median"),
                                 precio=("precio_usd", "median"), conv=("conversion", "median")).reset_index()
    g = g[(g["disenos"] >= MIN_DISENOS_TAG) & (g["tags_l"] != "")]
    g["estacional"] = g["tags_l"].apply(lambda t: any(k in t for k in ESTACIONAL))
    g["lift"] = g["dl_dia"] / base
    g = g.sort_values("dl_dia", ascending=False)
    g.to_csv(REP / "mercado_v3_tags.csv", index=False)
    out.append("## 5. Etiquetas con más descargas por día (solo orgánicos, no estacionales)\n")
    out.append("| etiqueta | diseños | desc./día | vistas/día | precio |\n|---|---|---|---|---|")
    for _, r in g[~g["estacional"]].head(20).iterrows():
        out.append(f"| {r['tags_l']} | {int(r['disenos'])} | {r['dl_dia']:.1f} | {r['v_dia']:.0f} | {r['precio']:.2f} |")
    out.append("\nEstacionales (para planificar el año que viene, no para ahora): " +
               ", ".join(g[g["estacional"]].head(8)["tags_l"].tolist()) + "\n")

    reg = org[org.apply(lambda r: any(k in r["nombre_l"] or any(k in t for t in r["tags_l"])
                                      for k in ("matera", "mate holder", "argentin", "yerba", "termo")), axis=1)]
    if len(reg):
        out.append("## 6. Nicho regional (mate / Argentina)\n")
        out.append("| nombre | días | USD | descargas | vistas |\n|---|---|---|---|---|")
        for _, r in reg.sort_values("descargas", ascending=False).iterrows():
            out.append(f"| {r['nombre'][:60]} | {int(r['dias_online'])} | {r['precio_usd']:.2f} | {int(r['descargas'])} | {int(r['vistas'])} |")
        out.append("")
    (REP / "mercado_v3.md").write_text("\n".join(out), encoding="utf-8")
    print("\n".join(out))


if __name__ == "__main__":
    sys.exit(main())
