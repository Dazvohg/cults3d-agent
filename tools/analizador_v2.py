"""Analizador de mercado Cults3D v2.

Qué corrige respecto de la v1:
  - Muestra: trae hasta 500 diseños PAGOS publicados en los últimos N días, ordenados
    por descargas (la v1 traía los 100 más nuevos, que casi no tienen descargas).
  - Normaliza por antigüedad: descargas por día desde la publicación.
  - Estima ingresos: en diseños pagos, cada descarga es una venta -> descargas x precio.
  - Mide conversión: descargas / vistas.
  - Rankea tags y categorías por MEDIANA (no por suma) y exige un mínimo de diseños,
    así un solo modelo exitoso no distorsiona el ranking.
  - Marca tags de propiedad intelectual ajena (Warhammer, Marvel, etc.): no se pueden vender.
  - La API key se lee de variables de entorno / archivo .env, nunca del código.

Uso (en tu PC):
  1) Creá un archivo .env al lado de este script con:
       CULTS_USERNAME=tu_nick
       CULTS_API_KEY=tu_key
  2) pip install requests pandas openpyxl
  3) python analizador_v2.py --dias 90 --max 500
Salida: cults3d_mercado.xlsx (hojas: resumen, tags, categorias, disenos)
"""
import argparse
import base64
import datetime as dt
import os
import pathlib
import sys
import time

import pandas as pd
import requests

API = "https://cults3d.com/graphql"
MIN_DISENOS = 5  # un tag/categoría necesita al menos esta cantidad de diseños para rankear

# Tags que indican propiedad intelectual de terceros: vender algo así es infracción y Cults lo da de baja.
IP_TERMS = [
    "warhammer", "wh40k", "40k", "horus", "space marine", "adeptus", "astartes", "konrad curze",
    "lorgar", "magnus", "thousand sons", "marvel", "avengers", "captain america", "red skull",
    "spider", "batman", "dc", "star wars", "mandalorian", "pokemon", "pikachu", "disney", "pixar",
    "minecraft", "funko", "nintendo", "mario", "zelda", "sailor moon", "dragon ball", "naruto",
    "one piece", "harry potter", "lord of the rings", "god of war", "godofwar", "league of legends",
    "arcane", "barbie", "ben10", "omnitrix", "rick and mor", "deltarune", "risk of rain", "dune",
    "gijoe", "porsche", "volkswagen", "vw", "nissan", "sailorpluto", "sailorscouts",
    "xmen", "x-men", "thor", "blade", "berserk", "resident evil", "looney tunes", "peaky blinders",
    "coraline", "strahd", "gta", "grand theft auto", "ghostbusters", "transformers", "predator",
    "terminator", "stranger things", "game of thrones", "witcher", "elden ring", "dark souls",
    "fortnite", "overwatch", "diablo", "castlevania", "street fighter", "mortal kombat",
    "final fantasy", "tomb raider", "sonic", "kirby", "genshin", "fallout", "skyrim", "star trek",
    "jurassic", "hellboy", "venom", "deadpool", "wolverine", "iron man", "hulk", "joker", "superman",
    "hello kitty", "my little pony", "tanuki", "rayman", "donkey kong", "metroid",
]

# Lo que SÍ podemos diseñar con OpenSCAD: piezas funcionales/paramétricas. Las figuras, bustos y
# miniaturas (categoría Art, USD 20, de estudios grandes) no son un mercado al que podamos entrar.
CATEGORIAS_FUNCIONALES = {"home", "gadget", "tool", "various"}
PALABRAS_FUNCIONALES = [
    "gridfinity", "organizer", "organiser", "holder", "stand", "planter", "pot", "tray", "dice",
    "clip", "hook", "bracket", "storage", "box", "mount", "bin", "tool", "drawer", "cable",
    "headphone", "phone", "vase", "lamp", "coaster", "key", "shelf", "hanger", "dock", "tower",
    "insert", "magnet", "replacement", "adapter", "handle", "knob", "lantern", "ornament",
    "snowflake", "tealight", "candle", "basket", "dispenser", "rack", "support", "divider",
]
# Tags que describen el tipo de archivo o son relleno: no son nichos.
TAGS_GENERICOS = {
    "fun", "death", "evil", "stylized", "video", "video game", "movie", "female", "woman", "figure",
    "figurine", "figurines", "3dprinted", "3dmodel", "3dprinting", "3dprint", "cults3d", "stl",
    "fan art", "fanart", "resin", "garage kit", "game art figurine", "action", "cartoon figure",
    "god", "ghost", "cartoon", "sculpture", "bust", "miniature", "miniatures", "model", "art",
    "character", "characters", "digital", "stl file", "print", "printable", "3d", "3dprintable",
    "stl printable model", "printable model", "3d printing", "beginner", "nan", "cats", "cat", "dog", "dogs",
}
MIN_DIAS_TASA = 14  # un diseño de 2 días con 400 descargas (lanzamiento de un estudio) no es una tasa diaria real


def load_env():
    env = pathlib.Path(__file__).with_name(".env")
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    user, key = os.getenv("CULTS_USERNAME"), os.getenv("CULTS_API_KEY")
    if not user or not key:
        sys.exit("Faltan CULTS_USERNAME / CULTS_API_KEY (archivo .env o variables de entorno).")
    return user, key


class Api:
    def __init__(self, user, key):
        tok = base64.b64encode(f"{user}:{key}".encode()).decode()
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Basic {tok}", "Content-Type": "application/json"})

    def q(self, query):
        wait = 5
        for _ in range(6):
            r = self.s.post(API, json={"query": query}, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                print(f"  API ocupada ({r.status_code}), reintento en {wait}s...")
                time.sleep(wait)
                wait *= 2
                continue
            if r.status_code == 401:
                sys.exit("Credenciales rechazadas: revisá usuario y API key.")
            r.raise_for_status()
            data = r.json()
            if data.get("errors"):
                sys.exit(f"Error de la API: {data['errors']}")
            return data["data"]
        sys.exit("La API siguió fallando; probá más tarde (límite ~500 consultas por día).")


FIELDS = """
  identifier name(locale: EN) shortUrl publishedAt
  price(currency: USD) { value }
  downloadsCount likesCount viewsCount
  tags(locale: EN) madeWithAi
  category { name(locale: EN) }
"""


def fetch(api, dias, maximo, gratis=False):
    desde = (dt.datetime.utcnow() - dt.timedelta(days=dias)).strftime("%Y-%m-%dT00:00:00+00:00")
    rows, offset, lote = [], 0, 100
    while offset < maximo:
        filtro = "onlyFree: true" if gratis else "onlyPriced: true"
        query = f"""{{ creationsBatch(sort: BY_DOWNLOADS, {filtro}, submittedAfter: "{desde}",
                        limit: {lote}, offset: {offset}) {{ results {{ {FIELDS} }} }} }}"""
        res = api.q(query)["creationsBatch"]["results"]
        print(f"  lote {offset // lote + 1}: {len(res)} diseños")
        rows += res
        if len(res) < lote:
            break
        offset += lote
        time.sleep(1)
    return rows


def es_ip(tag):
    t = tag.lower()
    return any(term == t or term in t.split() or (len(term) > 4 and term in t) for term in IP_TERMS)


def ip_en_nombre(nombre):
    """IP en el título: solo palabras completas y términos de 6+ letras o varias palabras
    (así 'razor blade holder' o 'ultrasonic' no se marcan por error)."""
    import re
    n = str(nombre).lower()
    return any(re.search(rf"(?<![a-z0-9]){re.escape(t)}(?![a-z0-9])", n)
               for t in IP_TERMS if len(t) >= 6 or " " in t)


def analizar(rows, gratis_rows=None):
    hoy = pd.Timestamp.now(tz='UTC')
    df = pd.DataFrame([{
        "nombre": r.get("name"),
        "url": r.get("shortUrl"),
        "categoria": (r.get("category") or {}).get("name") or "Sin categoría",
        "publicado": pd.to_datetime(r.get("publishedAt"), utc=True, errors="coerce"),
        "precio_usd": float((r.get("price") or {}).get("value") or 0),
        "descargas": int(r.get("downloadsCount") or 0),
        "likes": int(r.get("likesCount") or 0),
        "vistas": int(r.get("viewsCount") or 0),
        "hecho_con_ia": bool(r.get("madeWithAi")),
        "tags": sorted({t.lower().strip() for t in (r.get("tags") or []) if isinstance(t, str) and t.strip()}),
    } for r in rows])
    if df.empty:
        sys.exit("La API no devolvió diseños para ese período.")
    df["dias_online"] = ((hoy - df["publicado"]).dt.days).clip(lower=1).fillna(1)
    df["ventas_por_dia"] = df["descargas"] / df["dias_online"].clip(lower=MIN_DIAS_TASA)
    df["ingreso_estimado_usd"] = df["descargas"] * df["precio_usd"]
    df["conversion"] = (df["descargas"] / df["vistas"].where(df["vistas"] > 0)).fillna(0)
    df["tiene_ip_ajena"] = df["tags"].apply(lambda ts: any(es_ip(t) for t in ts)) | \
        df["nombre"].fillna("").apply(ip_en_nombre)
    texto = (df["nombre"].fillna("") + " " + df["tags"].apply(" ".join)).str.lower()
    tiene_kw = texto.apply(lambda t: any(k in t.replace("-", " ").split() or (len(k) > 4 and k in t)
                                         for k in PALABRAS_FUNCIONALES))
    cat = df["categoria"].str.lower()
    df["funcional"] = (~df["tiene_ip_ajena"]) & (cat.isin(CATEGORIAS_FUNCIONALES) | (tiene_kw & (cat != "art")))

    def agrupar(frame, col):
        g = frame.groupby(col).agg(
            disenos=("nombre", "count"),
            con_ventas=("descargas", lambda s: int((s > 0).sum())),
            ventas_por_dia_mediana=("ventas_por_dia", "median"),
            precio_mediano_usd=("precio_usd", "median"),
            ingreso_estimado_total_usd=("ingreso_estimado_usd", "sum"),
            conversion_mediana=("conversion", "median"),
        ).reset_index()
        g["pct_disenos_con_ventas"] = g["con_ventas"] / g["disenos"]
        g = g[g["disenos"] >= MIN_DISENOS]
        return g.sort_values(["ventas_por_dia_mediana", "ingreso_estimado_total_usd"], ascending=False)

    tags = agrupar(df.explode("tags").dropna(subset=["tags"]).rename(columns={"tags": "tag"}), "tag")
    tags.insert(1, "propiedad_intelectual_ajena", tags["tag"].apply(es_ip))
    # % de los diseños con ese tag que son funcionales: un nicho "diseñable" es uno de objetos útiles
    func = df.explode("tags").dropna(subset=["tags"]).groupby("tags")["funcional"].mean()
    tags["pct_funcional"] = tags["tag"].map(func).fillna(0).round(3)
    tags["disenable"] = (tags["pct_funcional"] >= 0.5) & ~tags["tag"].isin(TAGS_GENERICOS) & \
        ~tags["propiedad_intelectual_ajena"]

    # Saturación: qué tan presente está cada tag entre los diseños GRATIS más descargados,
    # normalizado por el tamaño de cada muestra. Si la mayoría de lo que se baja en ese nicho es
    # gratis, vender la versión básica cuesta: hay que diferenciarse.
    if gratis_rows:
        libres = pd.Series([t.lower().strip() for r in gratis_rows for t in (r.get("tags") or [])
                            if isinstance(t, str) and t.strip()]).value_counts()
        f_libre = tags["tag"].map(libres).fillna(0) / max(len(gratis_rows), 1)
        f_pago = tags["disenos"] / max(len(df), 1)
        tags["pct_gratis"] = (f_libre / (f_libre + f_pago)).round(3)
    else:
        tags["pct_gratis"] = 0.0
    tags["saturado"] = (tags["pct_gratis"] >= 0.6) & (tags["disenos"] >= 10)
    tags["indice_oportunidad"] = (tags["ventas_por_dia_mediana"] * (1 - tags["pct_gratis"])
                                  * tags["pct_disenos_con_ventas"]).round(5)
    tags = tags.sort_values("indice_oportunidad", ascending=False)
    cats = agrupar(df, "categoria")

    resumen = pd.DataFrame({
        "métrica": [
            "Diseños analizados", "Con al menos 1 venta", "Ventas totales (descargas pagas)",
            "Ingreso estimado total (USD)", "Precio mediano (USD)", "Ventas por día (mediana)",
            "Diseños con IP ajena (excluir)", f"Tags con >= {MIN_DISENOS} diseños",
            "Tags saturados de oferta gratis", "Diseños funcionales (los que podemos diseñar)",
            "Tags diseñables",
        ],
        "valor": [
            len(df), int((df["descargas"] > 0).sum()), int(df["descargas"].sum()),
            round(df["ingreso_estimado_usd"].sum(), 2), df["precio_usd"].median(),
            round(df["ventas_por_dia"].median(), 4), int(df["tiene_ip_ajena"].sum()), len(tags),
            int(tags["saturado"].sum()), int(df["funcional"].sum()), int(tags["disenable"].sum()),
        ],
    })
    df["tags"] = df["tags"].apply(", ".join)
    df["publicado"] = df["publicado"].dt.tz_localize(None)
    return resumen, tags, cats, df.sort_values("ventas_por_dia", ascending=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=90, help="ventana de publicación a analizar")
    ap.add_argument("--max", type=int, default=500, help="máximo de diseños (5 consultas por cada 500)")
    ap.add_argument("--salida", default="cults3d_mercado.xlsx")
    a = ap.parse_args()

    api = Api(*load_env())
    print(f"Descargando diseños pagos de los últimos {a.dias} días...")
    pagos = fetch(api, a.dias, a.max)
    print("Descargando una muestra de diseños gratis para medir la saturación de cada nicho...")
    gratis = fetch(api, a.dias, 200, gratis=True)
    resumen, tags, cats, disenos = analizar(pagos, gratis)
    with pd.ExcelWriter(a.salida, engine="openpyxl") as xw:
        resumen.to_excel(xw, sheet_name="resumen", index=False)
        tags.to_excel(xw, sheet_name="tags", index=False)
        cats.to_excel(xw, sheet_name="categorias", index=False)
        disenos.to_excel(xw, sheet_name="disenos", index=False)
    print(resumen.to_string(index=False))
    print("\nTop 15 oportunidades (sin IP ajena, ordenadas por índice de oportunidad):")
    print(tags[tags["disenable"]].head(15)[
        ["tag", "disenos", "ventas_por_dia_mediana", "precio_mediano_usd", "pct_gratis", "saturado", "indice_oportunidad"]
    ].to_string(index=False))
    print(f"\nListo: {a.salida}")


if __name__ == "__main__":
    main()
