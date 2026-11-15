"""AIFEC — fábrica de temas: crea un tema nuevo a partir del esqueleto de `plantillas/esqueleto/`.

    python skill/esqueleto.py <slug> "<Nombre del tema>" [--salida <carpeta>] [--prefijo xx] [--forzar]

Copia el esqueleto (un tema hijo de `base` con las cinco superficies ya propias y que pasa `theme:check`),
sustituye las marcas `__slug__` y `__Nombre__`, deja `NOTAS.md` con la tabla de descomposición y cambia el prefijo de clases propias `sk-` por uno del tema
(por defecto, las iniciales del slug), para que dos temas nunca compartan nombres de clase. Por defecto escribe
en `salida/<slug>/` de la fábrica. Sale con 0 si lo ha creado, con 2 si los datos no valen o la carpeta ya existe.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

RAIZ = Path(__file__).resolve().parent.parent
ESQUELETO = RAIZ / "plantillas" / "esqueleto"
DESCOMPOSICION = RAIZ / "skill" / "plantillas" / "descomposicion.md"
TEXTOS = (".php", ".css", ".js", ".json", ".md", ".svg")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def prefijo_por_defecto(slug: str) -> str:
    """Las iniciales del slug (hasta tres letras); si salen menos de dos, sus primeras letras. Nunca «af» ni «sk»."""
    iniciales = "".join(parte[0] for parte in slug.split("-") if parte)[:3]
    if len(iniciales) < 2:
        iniciales = re.sub(r"[^a-z]", "", slug)[:3]
    if iniciales in ("af", "sk") or len(iniciales) < 2:
        iniciales = "t" + (iniciales or "x")
    return iniciales


def crear(slug: str, nombre: str, destino: Path, prefijo: str = "", forzar: bool = False) -> list:
    """Crea el tema y devuelve la lista de ficheros escritos. Lanza ValueError si los datos no valen."""
    if not SLUG.match(slug):
        raise ValueError("el slug tiene que ir en minúsculas, con cifras y guiones: %r" % slug)
    if not nombre.strip() or len(nombre) > 60:
        raise ValueError("el nombre no puede estar vacío ni pasar de 60 caracteres")
    prefijo = prefijo or prefijo_por_defecto(slug)
    if not re.fullmatch(r"[a-z][a-z0-9]{1,5}", prefijo) or prefijo in ("af", "sk"):
        raise ValueError("el prefijo tiene que ser de 2 a 6 letras y cifras, y no puede ser «af» ni «sk»: %r" % prefijo)
    if not ESQUELETO.is_dir():
        raise ValueError("no encuentro el esqueleto en %s" % ESQUELETO)
    if destino.exists() and any(destino.iterdir()):
        if not forzar:
            raise ValueError("ya hay algo en %s (usa --forzar para rehacerlo)" % destino)
        shutil.rmtree(str(destino))
    escritos = []
    for origen in sorted(ESQUELETO.rglob("*")):
        if not origen.is_file() or "__pycache__" in origen.parts:
            continue
        relativa = origen.relative_to(ESQUELETO)
        salida = destino / relativa
        salida.parent.mkdir(parents=True, exist_ok=True)
        if origen.suffix.lower() in TEXTOS:
            texto = origen.read_text(encoding="utf-8")
            valor_nombre = json.dumps(nombre, ensure_ascii=False)[1:-1] if origen.suffix.lower() == ".json" else nombre
            texto = texto.replace("__slug__", slug).replace("__Nombre__", valor_nombre)
            texto = re.sub(r"(?<![A-Za-z0-9_-])sk-", prefijo + "-", texto)
            salida.write_bytes(texto.encode("utf-8"))
        else:
            shutil.copy2(str(origen), str(salida))
        escritos.append(relativa.as_posix())
    # La tabla de la fase 2 vive con el tema: `NOTAS.md`, con el nombre y el slug ya puestos.
    if DESCOMPOSICION.is_file() and not (destino / "NOTAS.md").exists():
        notas = DESCOMPOSICION.read_text(encoding="utf-8").replace("{{nombre}}", nombre).replace("{{slug}}", slug)
        (destino / "NOTAS.md").write_bytes(notas.encode("utf-8"))
        escritos.append("NOTAS.md")
    return escritos


def main() -> int:
    analizador = argparse.ArgumentParser(description="Crea un tema desde el esqueleto de la fábrica")
    analizador.add_argument("slug")
    analizador.add_argument("nombre")
    analizador.add_argument("--salida", default=None, help="carpeta del tema (por defecto salida/<slug>/)")
    analizador.add_argument("--prefijo", default="", help="prefijo de las clases propias (por defecto, las iniciales del slug)")
    analizador.add_argument("--forzar", action="store_true", help="rehace la carpeta si ya existe")
    args = analizador.parse_args()
    destino = Path(args.salida) if args.salida else RAIZ / "salida" / args.slug
    try:
        escritos = crear(args.slug, args.nombre, destino, args.prefijo, args.forzar)
    except ValueError as error:
        print("no se ha creado nada: %s" % error)
        return 2
    print("Tema «%s» creado en %s (%d ficheros, prefijo de clases «%s-»)" % (
        args.slug, destino, len(escritos), args.prefijo or prefijo_por_defecto(args.slug)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
