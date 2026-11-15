"""AIFEC — fábrica de temas: puerta «peso» (presupuesto del tema).

Comprueba los tres números del contrato 04 § 8 y el HTML que sirve: toda hoja de estilos del tema pesa 45 KB
o menos (45 000 bytes), todo guion propio 25 KB o menos, y la ficha de producto pintada, sin imágenes (sin las
etiquetas `<img>`, `<picture>` y `<source>` ni los `data:`), 150 KB o menos. Además, toda imagen de lo pintado
lleva `width` y `height` (sin ellos la página salta al cargar).

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

CSS_MAXIMO = 45000
JS_MAXIMO = 25000
FICHA_MAXIMO = 150000

IMAGENES = re.compile(r"<(?:img|picture|source)\b[^>]*>|</picture>", re.I | re.S)
DATA_URI = re.compile(r"data:[a-z/+.\-]+;[^\"')\s]*", re.I)


def sin_imagenes(html: str) -> str:
    """El HTML sin lo que no pesa en el documento sino en la red: imágenes y sus `data:`."""
    return DATA_URI.sub("", IMAGENES.sub("", html))


def imagenes_sin_medidas(html: str) -> int:
    """Cuántas `<img>` de una página no traen `width` y `height`."""
    cuantas = 0
    for etiqueta in re.findall(r"<img\b[^>]*>", html, flags=re.I | re.S):
        if not re.search(r"\swidth\s*=", etiqueta, re.I) or not re.search(r"\sheight\s*=", etiqueta, re.I):
            cuantas += 1
    return cuantas


def puerta(ctx) -> int:
    problemas = []
    detalles = []
    medidas = {}
    hojas = 0
    mayor_css = 0
    mayor_js = 0
    for relativa in _comun.ficheros(ctx.candidato / "assets", (".css", ".js")):
        tamano = (ctx.candidato / "assets" / relativa).stat().st_size
        if relativa.endswith(".css"):
            hojas += 1
            mayor_css = max(mayor_css, tamano)
            if tamano > CSS_MAXIMO:
                problemas.append("assets/%s pesa %s y el límite es %s" % (relativa, _comun.kb(tamano), _comun.kb(CSS_MAXIMO)))
            else:
                detalles.append("assets/%s: %s de %s" % (relativa, _comun.kb(tamano), _comun.kb(CSS_MAXIMO)))
        else:
            mayor_js = max(mayor_js, tamano)
            if tamano > JS_MAXIMO:
                problemas.append("assets/%s pesa %s y el límite es %s" % (relativa, _comun.kb(tamano), _comun.kb(JS_MAXIMO)))
            else:
                detalles.append("assets/%s: %s de %s" % (relativa, _comun.kb(tamano), _comun.kb(JS_MAXIMO)))
    medidas.update({"css_bytes": mayor_css, "js_bytes": mayor_js, "hojas": hojas})

    try:
        paginas = _comun.paginas_de(ctx, ctx.slug)
    except _comun.NoAplica as motivo:
        paginas = _comun.Paginas(ctx.slug)
        detalles.append("no se pudo pintar el tema, así que la ficha no se mide: %s" % motivo)
    ficha = paginas.html.get("ficha")
    if ficha is None:
        detalles.append("sin ficha de producto pintada: no se mide su peso")
    else:
        tamano = len(sin_imagenes(ficha).encode("utf-8"))
        medidas["ficha_bytes"] = tamano
        if tamano > FICHA_MAXIMO:
            problemas.append("la ficha de producto pintada pesa %s sin imágenes y el límite es %s" % (_comun.kb(tamano), _comun.kb(FICHA_MAXIMO)))
        else:
            detalles.append("ficha de producto: %s de %s (sin imágenes)" % (_comun.kb(tamano), _comun.kb(FICHA_MAXIMO)))
    sin_medida = {nombre: imagenes_sin_medidas(html) for nombre, html in paginas.html.items()}
    sin_medida = {n: c for n, c in sin_medida.items() if c}
    medidas["imagenes_sin_medidas"] = sum(sin_medida.values())
    for nombre, cuantas in sorted(sin_medida.items()):
        problemas.append("la página «%s» tiene %d imagen(es) sin width y height" % (nombre, cuantas))
    detalles += paginas.notas

    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas + detalles, medidas)
    resumen = "CSS %s de %s, JS %s de %s" % (_comun.kb(mayor_css), _comun.kb(CSS_MAXIMO), _comun.kb(mayor_js), _comun.kb(JS_MAXIMO))
    if "ficha_bytes" in medidas:
        resumen += ", ficha %s de %s" % (_comun.kb(medidas["ficha_bytes"]), _comun.kb(FICHA_MAXIMO))
    return ctx.terminar(_comun.PASA, resumen, detalles, medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("peso", puerta))
