"""Cliente mínimo compartido para la API GraphQL de Cults3D (lectura de .env, reintentos)."""
import base64
import os
import pathlib
import sys
import time

import requests

API = "https://cults3d.com/graphql"
ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_env():
    for env in (ROOT / ".env", ROOT / "tools" / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
    user, key = os.getenv("CULTS_USERNAME"), os.getenv("CULTS_API_KEY")
    if not user or not key:
        sys.exit("Faltan CULTS_USERNAME / CULTS_API_KEY (archivo .env o secrets de GitHub).")
    return user, key


class Api:
    def __init__(self, user=None, key=None):
        if not user:
            user, key = load_env()
        tok = base64.b64encode(f"{user}:{key}".encode()).decode()
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Basic {tok}", "Content-Type": "application/json"})

    def q(self, query, variables=None):
        wait = 5
        for _ in range(6):
            r = self.s.post(API, json={"query": query, "variables": variables or {}}, timeout=60)
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

    def paginate(self, build_query, path, lote=100, maximo=2000):
        """build_query(limit, offset) -> query string; path = keys to reach the results list."""
        out, offset = [], 0
        while offset < maximo:
            data = self.q(build_query(lote, offset))
            for k in path:
                data = data[k]
            res = data["results"] if isinstance(data, dict) else data
            out += res
            if len(res) < lote:
                break
            offset += lote
            time.sleep(1)
        return out
