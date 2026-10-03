"""Agente Cults3D - punto de entrada único.

  python agente.py analizar            -> baja el mercado y genera cults3d_mercado.xlsx
  python agente.py priorizar           -> muestra qué diseños conviene publicar primero
  python agente.py priorizar --aplicar -> además reordena la cola
  python agente.py generar             -> crea productos nuevos desde plantillas para los nichos rentables
  python agente.py construir           -> genera STL + imágenes del próximo diseño (para revisar)
  python agente.py publicar --prueba   -> simula la publicación del próximo diseño
  python agente.py publicar            -> publica de verdad (normalmente lo hace GitHub solo)
  python agente.py ventas              -> reporte de TUS ventas y acciones por diseño (ventas_propias.xlsx)
  python agente.py ventas --aplicar-precios -> además ajusta precios en Cults3D según la regla
  python agente.py calendario          -> próximas fechas comerciales y qué publicar
  python agente.py calendario --generar -> agrega a la cola los productos de temporada que tocan
  python agente.py descuentos          -> muestra si hoy empieza alguna promo (--aplicar para crearla)
  python agente.py todo                -> analizar + ventas + temporada + priorizar + generar + reordenar

Credenciales: archivo .env en esta carpeta (CULTS_USERNAME, CULTS_API_KEY y, para publicar
desde la PC, CDN_REPO y CDN_TOKEN). Nunca las escribas dentro del código.
"""
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
TOOLS = ROOT / "tools"


def cargar_env():
    for env in (ROOT / ".env", TOOLS / ".env"):
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def correr(script, *args):
    code = subprocess.call([sys.executable, str(TOOLS / script), *args], cwd=ROOT)
    if code:
        sys.exit(code)


def main():
    cargar_env()
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "ayuda"):
        print(__doc__)
        return
    cmd, extra = sys.argv[1], sys.argv[2:]
    if cmd == "analizar":
        correr("analizador_v2.py", "--salida", str(ROOT / "cults3d_mercado.xlsx"), *extra)
    elif cmd == "priorizar":
        correr("priorizar.py", *extra)
    elif cmd == "generar":
        correr("generar.py", *extra)
    elif cmd == "construir":
        cola = sorted((ROOT / "queue").glob("*.yaml"))
        if not cola:
            sys.exit("La cola está vacía.")
        correr("build.py", str(extra[0] if extra else cola[0]))
        print(f"Revisá los archivos en build/")
    elif cmd == "publicar":
        if "--prueba" in extra:
            os.environ["DRY_RUN"] = "1"
        correr("publish.py")
    elif cmd == "ventas":
        correr("ventas.py", *extra)
    elif cmd == "calendario":
        correr("calendario.py", *extra)
    elif cmd == "descuentos":
        correr("descuentos.py", *extra)
    elif cmd == "todo":
        correr("analizador_v2.py", "--salida", str(ROOT / "cults3d_mercado.xlsx"))
        correr("ventas.py")
        correr("calendario.py", "--generar")
        correr("priorizar.py")
        correr("generar.py")
        correr("priorizar.py", "--aplicar")
    else:
        sys.exit(f"Comando desconocido: {cmd}\n{__doc__}")


if __name__ == "__main__":
    main()
