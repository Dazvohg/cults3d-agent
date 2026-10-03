"""Reporte de TUS ventas en Cults3D y acciones recomendadas por diseño.

Qué hace:
  1. Baja tus diseños publicados (myself.creationsBatch) y tus ventas (myself.salesBatch).
  2. Por diseño calcula: días online, vistas, ventas, ingreso, conversión y ventas de los últimos 30 días.
  3. Clasifica cada diseño y recomienda una acción:
       ESTRELLA        >= 3 ventas en 30 días     -> subir precio 10 % y crear variantes del mismo tipo
       NO CONVIERTE    >= 21 días, >= 150 vistas, 0 ventas -> bajar precio 20 % y mejorar portada/fotos
       NO SE VE        >= 21 días, < 150 vistas   -> problema de visibilidad: mejorar título y tags
       VENDE POCO      alguna venta, pero < 3 en 30 días -> mantener
       NUEVO           < 21 días online           -> esperar, todavía no hay datos suficientes
  4. Guarda ventas_propias.xlsx y estrellas.csv (tags de lo que más vende; priorizar.py los usa
     para empujar arriba en la cola los diseños parecidos a tus éxitos).

Uso:
  python tools/ventas.py                   -> solo reporte
  python tools/ventas.py --aplicar-precios -> además cambia los precios en Cults3D según la regla
                                              (piso USD 1.49, techo USD 4.99, nunca toca diseños gratis)
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from cults_api import ROOT, Api  # noqa: E402

PISO, TECHO = 1.49, 4.99
DIAS_MIN, VISTAS_MIN, ESTRELLA_30D = 21, 150, 3


def bajar(api):
    creaciones = api.paginate(lambda l, o: f"""{{ myself {{ creationsBatch(limit: {l}, offset: {o}) {{ results {{
        id name(locale: EN) shortUrl publishedAt price(currency: USD) {{ value }}
        downloadsCount viewsCount likesCount tags(locale: EN) }} }} }} }}""", ["myself", "creationsBatch"])
    ventas = api.paginate(lambda l, o: f"""{{ myself {{ salesBatch(limit: {l}, offset: {o}) {{ results {{
        id createdAt income(currency: USD) {{ value }} discount {{ percentage }}
        creation {{ name(locale: EN) }} }} }} }} }}""", ["myself", "salesBatch"])
    return creaciones, ventas


def analizar(creaciones, ventas, hoy=None):
    hoy = hoy or pd.Timestamp.now(tz='UTC')
    v = pd.DataFrame([{
        "fecha": pd.to_datetime(s.get("createdAt"), utc=True, errors="coerce"),
        "diseno": (s.get("creation") or {}).get("name"),
        "ingreso_usd": float((s.get("income") or {}).get("value") or 0),
        "con_descuento": bool((s.get("discount") or {}).get("percentage")),
    } for s in ventas]) if ventas else pd.DataFrame(columns=["fecha", "diseno", "ingreso_usd", "con_descuento"])

    filas = []
    for c in creaciones:
        nombre = c.get("name")
        vd = v[v["diseno"] == nombre]
        pub = pd.to_datetime(c.get("publishedAt"), utc=True, errors="coerce")
        dias = max(1, (hoy - pub).days) if pd.notna(pub) else 1
        precio = float((c.get("price") or {}).get("value") or 0)
        vistas = int(c.get("viewsCount") or 0)
        n_ventas = len(vd) if precio > 0 else 0
        v30 = int((vd["fecha"] >= hoy - pd.Timedelta(days=30)).sum()) if len(vd) else 0
        if precio == 0:
            estado, accion, nuevo = "GRATIS", f"Imán de seguidores: {int(c.get('downloadsCount') or 0)} descargas", 0.0
        elif dias < DIAS_MIN:
            estado, accion, nuevo = "NUEVO", "Esperar: todavía no hay datos suficientes", precio
        elif precio > 0 and v30 >= ESTRELLA_30D:
            estado, accion = "ESTRELLA", "Subir precio 10 % y crear variantes del mismo tipo"
            nuevo = min(TECHO, round(precio * 1.10, 2))
        elif precio > 0 and n_ventas == 0 and vistas >= VISTAS_MIN:
            estado, accion = "NO CONVIERTE", "Bajar precio 20 % y mejorar portada / fotos reales"
            nuevo = max(PISO, round(precio * 0.80, 2))
        elif vistas < VISTAS_MIN:
            estado, accion, nuevo = "NO SE VE", "Mejorar título y tags (problema de visibilidad, no de precio)", precio
        else:
            estado, accion, nuevo = "VENDE POCO", "Mantener", precio
        filas.append({
            "id": c.get("id"), "diseno": nombre, "url": c.get("shortUrl"), "dias_online": dias,
            "precio_usd": precio, "vistas": vistas, "likes": int(c.get("likesCount") or 0),
            "ventas": n_ventas, "ventas_30d": v30, "ingreso_usd": round(vd["ingreso_usd"].sum(), 2),
            "conversion": round(n_ventas / vistas, 4) if vistas else 0.0,
            "estado": estado, "accion": accion, "precio_sugerido_usd": nuevo,
            "tags": ", ".join(c.get("tags") or []),
        })
    d = pd.DataFrame(filas)
    if d.empty:
        return d, v, pd.DataFrame()
    orden = {"ESTRELLA": 0, "NO CONVIERTE": 1, "NO SE VE": 2, "VENDE POCO": 3, "NUEVO": 4, "GRATIS": 5}
    d = d.sort_values(by=["estado", "ingreso_usd"], key=lambda s: s.map(orden) if s.name == "estado" else -s)
    resumen = pd.DataFrame({
        "métrica": ["Diseños publicados", "Ventas totales", "Ingreso total (USD)", "Ventas últimos 30 días",
                    "Estrellas", "No convierten", "No se ven", "Nuevos"],
        "valor": [len(d), int(d["ventas"].sum()), round(d["ingreso_usd"].sum(), 2), int(d["ventas_30d"].sum()),
                  int((d["estado"] == "ESTRELLA").sum()), int((d["estado"] == "NO CONVIERTE").sum()),
                  int((d["estado"] == "NO SE VE").sum()), int((d["estado"] == "NUEVO").sum())],
    })
    return d, v, resumen


def aplicar_precios(api, d):
    cambios = d[(d["precio_usd"] > 0) & (d["precio_sugerido_usd"] != d["precio_usd"])]
    for _, r in cambios.iterrows():
        m = f"""mutation {{ updateCreation(id: {json.dumps(r['id'])}, downloadPrice: {float(r['precio_sugerido_usd'])},
                currency: USD) {{ creation {{ id }} errors }} }}"""
        res = api.q(m)["updateCreation"]
        estado = "OK" if not res.get("errors") else f"ERROR {res['errors']}"
        print(f"  {r['diseno'][:50]:<50} USD {r['precio_usd']} -> {r['precio_sugerido_usd']}  {estado}")
    return len(cambios)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar-precios", action="store_true")
    a = ap.parse_args()
    api = Api()
    print("Descargando tus diseños y ventas...")
    creaciones, ventas = bajar(api)
    d, v, resumen = analizar(creaciones, ventas)
    if d.empty:
        print("Todavía no tenés diseños publicados.")
        return
    salida = ROOT / "ventas_propias.xlsx"
    with pd.ExcelWriter(salida, engine="openpyxl") as xw:
        resumen.to_excel(xw, sheet_name="resumen", index=False)
        d.to_excel(xw, sheet_name="por_diseno", index=False)
        v.assign(fecha=v["fecha"].dt.tz_localize(None) if len(v) else v["fecha"]).to_excel(
            xw, sheet_name="ventas", index=False)
    estrellas = d[d["estado"] == "ESTRELLA"][["diseno", "ventas_30d", "tags"]]
    estrellas.to_csv(ROOT / "estrellas.csv", index=False, encoding="utf-8-sig")
    print(resumen.to_string(index=False))
    print("\nAcciones:")
    for _, r in d[~d["estado"].isin(["VENDE POCO"])].iterrows():
        print(f"  [{r['estado']:<12}] {r['diseno'][:55]:<55} {r['accion']}")
    if a.aplicar_precios:
        print("\nAplicando cambios de precio en Cults3D...")
        print(f"{aplicar_precios(api, d)} precios actualizados.")
    print(f"\nListo: {salida.name} y estrellas.csv")


if __name__ == "__main__":
    main()
