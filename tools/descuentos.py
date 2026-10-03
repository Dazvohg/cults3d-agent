"""Descuentos automáticos en fechas clave (Black Friday, Navidad...) con createDiscount.

La API de Cults3D arranca el descuento en el momento en que se crea y solo recibe la fecha de fin,
por eso este script corre TODOS LOS DÍAS (GitHub Actions) y solo actúa el día en que empieza cada
promoción definida en tools/calendario.py. Si ese día ya corrió, no duplica nada.

Uso:
  python tools/descuentos.py                -> muestra qué haría hoy (no toca nada)
  python tools/descuentos.py --aplicar      -> crea los descuentos que empiezan hoy
  python tools/descuentos.py --forzar 25 --dias 3 --aplicar  -> promo manual ya mismo (25 %, 3 días)
"""
import argparse
import datetime as dt
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from calendario import EVENTOS, descuento_hoy  # noqa: E402
from cults_api import ROOT, Api  # noqa: E402

REGISTRO = ROOT / "descuentos_aplicados.csv"


def mis_disenos_pagos(api):
    res = api.paginate(lambda l, o: f"""{{ myself {{ creationsBatch(limit: {l}, offset: {o}) {{ results {{
        id name(locale: EN) price(currency: USD) {{ value }} discount {{ percentage endAt }} }} }} }} }}""",
                       ["myself", "creationsBatch"])
    return [c for c in res if float((c.get("price") or {}).get("value") or 0) > 0]


def ya_aplicado(clave, fecha):
    return REGISTRO.exists() and f"{fecha:%Y-%m-%d},{clave}," in REGISTRO.read_text(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--forzar", type=int, help="porcentaje para una promo manual inmediata")
    ap.add_argument("--dias", type=int, default=3)
    a = ap.parse_args()

    hoy = dt.date.today()
    promos = descuento_hoy(hoy)
    if a.forzar:
        promos = [("manual", a.forzar, dt.datetime.combine(hoy + dt.timedelta(days=a.dias), dt.time(23, 59)))]
    if not promos:
        print(f"Hoy ({hoy:%d/%m}) no empieza ninguna promoción. Próximas:")
        for k, ev in EVENTOS.items():
            if ev.get("descuento"):
                print(f"  - {ev['nombre']}: {ev['descuento']['porcentaje']} % durante {ev['descuento']['dias']} días")
        return

    api = Api()
    disenos = mis_disenos_pagos(api)
    for clave, pct, fin in promos:
        if clave != "manual" and ya_aplicado(clave, hoy):
            print(f"{clave}: ya se aplicó hoy, no se duplica.")
            continue
        pendientes = [c for c in disenos if not (c.get("discount") or {}).get("percentage")]
        print(f"{clave}: {pct} % hasta {fin:%d/%m %H:%M} en {len(pendientes)} diseños pagos"
              f" ({len(disenos) - len(pendientes)} ya tenían descuento)")
        if not a.aplicar:
            print("  (modo vista previa: agregá --aplicar para crear los descuentos)")
            continue
        ok = 0
        for c in pendientes:
            m = f"""mutation {{ createDiscount(creationId: {json.dumps(c['id'])}, discountPercentage: {int(pct)},
                    discountEndAt: {json.dumps(fin.strftime('%Y-%m-%dT%H:%M:%S-03:00'))}) {{ errors }} }}"""
            errs = api.q(m)["createDiscount"].get("errors")
            ok += not errs
            if errs:
                print(f"  ERROR en {c['name'][:50]}: {errs}")
        nuevo = not REGISTRO.exists()
        with open(REGISTRO, "a", encoding="utf-8") as f:
            if nuevo:
                f.write("fecha,evento,porcentaje,disenos\n")
            f.write(f"{hoy:%Y-%m-%d},{clave},{pct},{ok}\n")
        print(f"  {ok} descuentos creados.")


if __name__ == "__main__":
    main()
