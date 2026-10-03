"""Calendario comercial para Cults3D: fechas que venden, cuándo publicar y cuándo descontar.

Cada evento tiene:
  - fecha del evento (se recalcula cada año);
  - ventana de publicación: de `publicar_desde` semanas antes hasta `publicar_hasta` días antes
    (los compradores imprimen con anticipación, así que publicar tarde no sirve);
  - opcional: descuento automático (porcentaje y duración) que aplica tools/descuentos.py.

Las plantillas de templates/ con `temporada: <clave>` solo entran a la cola dentro de la ventana
de su evento, y priorizar.py las pone primeras mientras la ventana está abierta.

Uso: python tools/calendario.py            -> muestra los próximos eventos y qué hacer hoy
     python tools/calendario.py --generar  -> crea en queue/ los productos de temporada que tocan
"""
import argparse
import datetime as dt
import pathlib

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _nth_weekday(year, month, weekday, n):
    """n-ésimo día `weekday` (0 = lunes) del mes; n = -1 para el último."""
    if n > 0:
        d = dt.date(year, month, 1)
        d += dt.timedelta(days=(weekday - d.weekday()) % 7)
        return d + dt.timedelta(weeks=n - 1)
    d = dt.date(year + (month == 12), month % 12 + 1, 1) - dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - weekday) % 7)


def _black_friday(y):
    return _nth_weekday(y, 11, 3, 4) + dt.timedelta(days=1)  # viernes después del 4° jueves


EVENTOS = {
    "halloween":   {"nombre": "Halloween", "fecha": lambda y: dt.date(y, 10, 31),
                    "publicar_desde": 7, "publicar_hasta": 7},
    "black_friday": {"nombre": "Black Friday + Cyber Monday", "fecha": _black_friday,
                     "publicar_desde": 0, "publicar_hasta": 0,
                     "descuento": {"porcentaje": 30, "dias": 4}},
    "navidad":     {"nombre": "Navidad", "fecha": lambda y: dt.date(y, 12, 25),
                    "publicar_desde": 9, "publicar_hasta": 10,
                    "descuento": {"porcentaje": 20, "dias": 7, "empieza_dias_antes": 14}},
    "san_valentin": {"nombre": "San Valentín", "fecha": lambda y: dt.date(y, 2, 14),
                     "publicar_desde": 6, "publicar_hasta": 7},
    "dia_madre":   {"nombre": "Día de la Madre (EE. UU./global)", "fecha": lambda y: _nth_weekday(y, 5, 6, 2),
                    "publicar_desde": 6, "publicar_hasta": 7},
    "dia_padre":   {"nombre": "Día del Padre (EE. UU./global)", "fecha": lambda y: _nth_weekday(y, 6, 6, 3),
                    "publicar_desde": 6, "publicar_hasta": 7},
    "vuelta_clases": {"nombre": "Vuelta a clases (hemisferio norte)", "fecha": lambda y: dt.date(y, 8, 25),
                      "publicar_desde": 6, "publicar_hasta": 10},
}


def proxima_fecha(clave, hoy=None):
    hoy = hoy or dt.date.today()
    f = EVENTOS[clave]["fecha"]
    d = f(hoy.year)
    return d if d >= hoy else f(hoy.year + 1)


def ventana(clave, hoy=None):
    ev, d = EVENTOS[clave], proxima_fecha(clave, hoy)
    return d - dt.timedelta(weeks=ev["publicar_desde"]), d - dt.timedelta(days=ev["publicar_hasta"])


def en_ventana(clave, hoy=None):
    if not clave or clave not in EVENTOS or not EVENTOS[clave]["publicar_desde"]:
        return False
    hoy = hoy or dt.date.today()
    ini, fin = ventana(clave, hoy)
    return ini <= hoy <= fin


def descuento_hoy(hoy=None):
    """Devuelve [(clave, porcentaje, fin_datetime)] de los descuentos que arrancan hoy."""
    hoy = hoy or dt.date.today()
    out = []
    for k, ev in EVENTOS.items():
        dsc = ev.get("descuento")
        if not dsc:
            continue
        inicio = proxima_fecha(k, hoy) - dt.timedelta(days=dsc.get("empieza_dias_antes", 0))
        if inicio == hoy:
            fin = dt.datetime.combine(inicio + dt.timedelta(days=dsc["dias"]), dt.time(23, 59))
            out.append((k, dsc["porcentaje"], fin))
    return out


def generar(hoy=None):
    """Crea en queue/ las plantillas de temporada cuya ventana está abierta y no están aún en cola/publicadas."""
    existentes = {yaml.safe_load(p.read_text(encoding="utf-8"))["slug"]
                  for p in list((ROOT / "queue").glob("*.yaml")) + list((ROOT / "published").glob("*.yaml"))}
    siguiente = max([int(p.name[:3]) for p in (ROOT / "queue").glob("[0-9][0-9][0-9]-*.yaml")] or [0]) + 1
    creados = []
    for p in sorted((ROOT / "templates").glob("*.yaml")):
        t = yaml.safe_load(p.read_text(encoding="utf-8"))
        clave = t.get("temporada")
        if clave and en_ventana(clave, hoy) and t["item"]["slug"] not in existentes:
            item = dict(t["item"], temporada=clave)
            dest = ROOT / "queue" / f"{siguiente:03d}-{item['slug']}.yaml"
            dest.write_text(yaml.safe_dump(item, allow_unicode=True, sort_keys=False), encoding="utf-8")
            creados.append(dest.name)
            siguiente += 1
    return creados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generar", action="store_true")
    a = ap.parse_args()
    hoy = dt.date.today()
    print(f"Calendario comercial (hoy {hoy:%d/%m/%Y}):\n")
    for k in sorted(EVENTOS, key=lambda k: proxima_fecha(k, hoy)):
        ev, d = EVENTOS[k], proxima_fecha(k, hoy)
        linea = f"  {d:%d/%m/%Y}  {ev['nombre']:<36}"
        if ev["publicar_desde"]:
            ini, fin = ventana(k, hoy)
            estado = "PUBLICAR AHORA" if ini <= hoy <= fin else ("tarde" if hoy > fin else f"publicar desde {ini:%d/%m}")
            linea += f" {estado}"
        if ev.get("descuento"):
            linea += f"  | descuento {ev['descuento']['porcentaje']} %"
        print(linea)
    if a.generar:
        creados = generar(hoy)
        print("\n" + ("\n".join(f"  + {c}" for c in creados) if creados else "  No hay productos de temporada para agregar hoy."))


if __name__ == "__main__":
    main()
