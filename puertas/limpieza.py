"""AIFEC — fábrica de temas: puerta «limpieza» (nada de fuera ni de sobra).

Tres cosas, ninguna de las cuales mira el validador del sistema de la misma manera:
1. Ninguna dirección de otro dominio (ni `@import`) en hojas, guiones, imágenes SVG ni plantillas: el único
   `http://` admitido es el espacio de nombres de SVG (`www.w3.org`).
2. Ningún fichero que no sea del tema: `.zip` y demás paquetes, mapas de código, `node_modules`, carpetas de
   control de versiones, tipografías que no sean `woff2`/`woff` y capturas o imágenes sueltas fuera de `assets/`
   (solo se admiten `preview.png` y `mockup.png` en la raíz).
3. Sintaxis de PHP correcta en todas las versiones de `php_versiones` del plan (y en la de `php`).

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

DIRECCION = re.compile(r"(?:https?:)?//(?!www\.w3\.org/)[a-z0-9][a-z0-9.\-]*\.[a-z]{2,}", re.I)
PROTOCOLO = re.compile(r"https?://(?!www\.w3\.org/)", re.I)
IMPORTAR = re.compile(r"@import\b", re.I)
PAQUETES = (".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".bz2", ".xz", ".phar")
SUELTOS = (".map", ".psd", ".ai", ".sketch", ".fig", ".log", ".bak", ".orig", ".swp", ".exe", ".dll", ".sh", ".bat")
TIPOGRAFIAS_MALAS = (".ttf", ".otf", ".eot")
CARPETAS_PROHIBIDAS = ("node_modules", ".git", ".github", "capturas", "screenshots", "tests-visuales", "__pycache__")
IMAGENES = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif")
RAIZ_PERMITIDA = ("preview.png", "mockup.png")


def _con_texto(carpeta: Path) -> list:
    """Ficheros donde una dirección ajena sería un problema: plantillas y recursos de texto del tema."""
    elegidos = []
    for relativa in _comun.ficheros(carpeta):
        partes = relativa.split("/")
        sufijo = Path(relativa).suffix.lower()
        if partes[0] == "templates" and sufijo in (".php", ".html"):
            elegidos.append(relativa)
        elif partes[0] == "assets" and sufijo in (".css", ".js", ".svg", ".html", ".php"):
            elegidos.append(relativa)
    return elegidos


def direcciones_ajenas(carpeta: Path) -> list:
    """(fichero, línea, trozo) de cada dirección de otro dominio o `@import`."""
    encontradas = []
    for relativa in _con_texto(carpeta):
        for numero, linea in enumerate(_comun.leer_texto(carpeta / relativa).splitlines(), 1):
            for patron, que in ((PROTOCOLO, "dirección"), (DIRECCION, "dirección"), (IMPORTAR, "@import")):
                coincidencia = patron.search(linea)
                if coincidencia:
                    encontradas.append((relativa, numero, que, linea.strip()[:100]))
                    break
    return encontradas


def ficheros_de_sobra(carpeta: Path) -> list:
    """(fichero, motivo) de lo que no debería estar en un tema."""
    sobra = []
    vistas = set()
    for ruta in sorted(carpeta.rglob("*")):
        relativa = ruta.relative_to(carpeta)
        partes = relativa.parts
        for pieza in partes:
            if pieza in CARPETAS_PROHIBIDAS and pieza not in vistas:
                vistas.add(pieza)
                sobra.append((relativa.as_posix(), "carpeta que no es de un tema («%s»)" % pieza))
        if any(p in CARPETAS_PROHIBIDAS for p in partes) or not ruta.is_file():
            continue
        sufijo = ruta.suffix.lower()
        if sufijo in PAQUETES or ruta.name.lower().endswith((".tar.gz",)):
            sobra.append((relativa.as_posix(), "un paquete comprimido"))
        elif sufijo in SUELTOS:
            sobra.append((relativa.as_posix(), "un fichero de trabajo (%s)" % sufijo))
        elif sufijo in TIPOGRAFIAS_MALAS:
            sobra.append((relativa.as_posix(), "tipografía que no es woff2 (el contrato pide woff2 propias)"))
        elif sufijo in IMAGENES and partes[0] != "assets" and relativa.as_posix().lower() not in RAIZ_PERMITIDA:
            sobra.append((relativa.as_posix(), "una imagen fuera de assets/ (¿una captura?): solo se admiten preview.png y mockup.png"))
    return sobra


def sintaxis(ctx, carpeta: Path) -> tuple:
    """(errores, comprobaciones) de `php -l` en todas las versiones declaradas."""
    programas = []
    principal = ctx.opcion("php", "php")
    for texto in [principal] + [v for v in ctx.opcion("php_versiones", []) if isinstance(v, str)]:
        if texto not in programas:
            programas.append(texto)
    php = [p for p in _comun.ficheros(carpeta, (".php",))]
    errores = []
    hechas = 0
    for texto in programas:
        ejecutable = _comun.ejecutable(texto)
        if ejecutable is None:
            errores.append("no encuentro el PHP «%s» del plan: sin él no se prueba la sintaxis en esa versión" % texto)
            continue
        for relativa in php:
            registro = ctx.sesiones / ("%s.limpieza.lint.log" % ctx.slug)
            if registro.exists():
                registro.unlink()
            codigo = _comun.procesos.lanzar([ejecutable, "-d", "display_errors=1", "-l", str(carpeta / relativa)], carpeta, registro, 2)
            hechas += 1
            if codigo != 0:
                salida = [l for l in _comun.leer_texto(registro).splitlines() if l.strip() and not l.startswith("Errors parsing")]
                errores.append("%s no es PHP válido con %s: %s" % (relativa, Path(ejecutable).parent.name or "php", (salida or ["sin mensaje"])[0][:140]))
    return errores, hechas, len(programas)


def puerta(ctx) -> int:
    carpeta = ctx.candidato
    if not carpeta.is_dir():
        raise _comun.NoPasa("no hay candidato en %s" % carpeta)
    problemas = []
    for relativa, numero, que, linea in direcciones_ajenas(carpeta):
        problemas.append("%s:%d trae %s de otro dominio o @import: %s" % (relativa, numero, que, linea))
    for relativa, motivo in ficheros_de_sobra(carpeta):
        problemas.append("%s: %s" % (relativa, motivo))
    errores, hechas, programas = sintaxis(ctx, carpeta)
    problemas += errores
    medidas = {"ficheros": len(_comun.ficheros(carpeta)), "php_versiones": programas, "lint": hechas, "problemas": len(problemas)}
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas, medidas)
    return ctx.terminar(_comun.PASA, "tema limpio: %d ficheros, sintaxis de PHP correcta con %d versión(es)" % (medidas["ficheros"], programas), [], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("limpieza", puerta))
