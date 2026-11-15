"""AIFEC — fábrica de temas: puerta «estructura» (que el tema no es un clon).

Pinta portada, listado, ficha y carrito con el candidato y con cada uno de los demás temas, saca de cada
página las cinco superficies por sus clases de contrato (`af-header`, `af-product-card` —la primera—,
`af-listing`, `af-product`, `af-footer`), las reduce a su esqueleto (ver `_html.py`) y mide el parecido de
0 a 1. No pasa si una superficie llega a `umbral_estructura` (0,82) con otro tema, o a 0,90 con su tema
padre: es una superficie heredada sin rediseñar. Sin otros temas con los que comparar, pasa y lo dice.

Se usa también suelta, para comparar dos páginas:

    python puertas/estructura.py --comparar <html A> <html B>

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
import _html  # noqa: E402

LIMITE_PADRE = 0.90
NOMBRES = {"cabecera": "cabecera", "tarjeta": "tarjeta de producto", "listado": "listado", "ficha": "ficha", "pie": "pie"}


def cifra(valor: float) -> str:
    return ("%.2f" % valor).replace(".", ",")


def tabla(columnas: dict) -> list:
    """Las líneas de la tabla superficie × tema. `columnas`: tema -> {superficie: parecido}."""
    if not columnas:
        return []
    temas = list(columnas)
    ancho = max([len(NOMBRES[s]) for s in _html.SUPERFICIES] + [10])
    lineas = ["%-*s  %s" % (ancho, "superficie", "  ".join("%-10s" % t[:10] for t in temas))]
    for superficie in _html.SUPERFICIES:
        celdas = []
        for tema in temas:
            valor = columnas[tema].get(superficie)
            celdas.append("%-10s" % (cifra(valor) if valor is not None else "-"))
        lineas.append("%-*s  %s" % (ancho, NOMBRES[superficie], "  ".join(celdas)))
    return lineas


def el_mas_alto(columnas: dict):
    """(parecido, superficie, tema) del par más parecido, o None."""
    mejor = None
    for tema, valores in columnas.items():
        for superficie, valor in valores.items():
            if mejor is None or valor > mejor[0]:
                mejor = (valor, superficie, tema)
    return mejor


def comparar_ficheros(a: str, b: str) -> int:
    """Modo suelto: dos páginas HTML, una tabla y su cifra más alta."""
    paginas = []
    for ruta in (a, b):
        if not Path(ruta).is_file():
            print("no existe el fichero: " + ruta)
            return 2
        paginas.append(_html.superficies_de(_html.leer(_comun.leer_texto(ruta))))
    valores = _html.comparar(paginas[0], paginas[1])
    for linea in tabla({Path(b).stem: valores}):
        print(linea)
    mejor = el_mas_alto({Path(b).stem: valores})
    if mejor is None:
        print("Ninguna superficie del contrato está en las dos páginas.")
        return 2
    print("Más alto: %s con %s (%s)" % (NOMBRES[mejor[1]], cifra(mejor[0]), Path(b).stem))
    return 0


def puerta(ctx) -> int:
    umbral = float(ctx.opcion("umbral_estructura", 0.82))
    padre = _comun.padre_del_candidato(ctx)
    propio = _comun.paginas_de(ctx, ctx.slug)
    if not propio:
        raise _comun.NoPasa("no hay páginas del candidato que comparar")
    detalles = ["%s: %s" % (ctx.slug, f) for f in propio.fallos]
    if propio.fallos and "portada" not in propio.html:
        raise _comun.NoPasa("el candidato no se pinta: " + "; ".join(propio.fallos))
    nuestras = _html.superficies_de_paginas(propio.html)

    faltan = [NOMBRES[s] for s in _html.SUPERFICIES if s not in nuestras]
    if faltan and not propio.muestra:
        clases = ", ".join("«%s»" % _html.SUPERFICIES[s][0] for s in _html.SUPERFICIES if s not in nuestras)
        raise _comun.NoPasa("el tema no pinta %s: faltan las clases del contrato %s" % (", ".join(faltan), clases))

    columnas = {}
    mala = []
    ajenos = _comun.temas_ajenos(ctx)
    for otro in ajenos:
        pagina = _comun.paginas_de(ctx, otro)
        if not pagina:
            detalles.append("%s: no se pudo pintar, no se compara" % otro)
            continue
        valores = _html.comparar(nuestras, _html.superficies_de_paginas(pagina.html))
        columnas[otro] = valores
        limite = LIMITE_PADRE if otro == padre else umbral
        for superficie, valor in valores.items():
            if valor >= limite:
                if otro == padre:
                    mala.append("%s hereda del tema padre «%s» (parecido %s, límite %s): superficie heredada sin rediseñar"
                                % (NOMBRES[superficie], otro, cifra(valor), cifra(limite)))
                else:
                    mala.append("%s se parece al tema «%s» (parecido %s, límite %s)"
                                % (NOMBRES[superficie], otro, cifra(valor), cifra(limite)))

    detalles = tabla(columnas) + detalles
    mejor = el_mas_alto(columnas)
    medidas = {"temas_comparados": len(columnas), "umbral": umbral, "limite_padre": LIMITE_PADRE}
    if mejor:
        medidas.update({"maximo": round(mejor[0], 4), "superficie": mejor[1], "tema": mejor[2]})
        detalles.append("Más alto: %s con %s (tema «%s»)" % (NOMBRES[mejor[1]], cifra(mejor[0]), mejor[2]))
    detalles += propio.notas
    if propio.muestra and faltan:
        detalles.append("sin productos en el banco no hay %s: no se compara" % ", ".join(faltan))
    if mala:
        return ctx.terminar(_comun.NO_PASA, "%d superficie(s) demasiado parecidas a otro tema" % len(mala), mala + detalles, medidas)
    if not columnas:
        return ctx.terminar(_comun.PASA, "no hay otros temas con los que comparar", detalles, medidas)
    return ctx.terminar(_comun.PASA, "estructura propia: lo más parecido es %s con «%s» (%s de %s)"
                        % (NOMBRES[mejor[1]], mejor[2], cifra(mejor[0]), cifra(umbral)) if mejor else "sin parecidos que medir",
                        detalles, medidas)


def main() -> int:
    if "--comparar" in sys.argv[1:]:
        resto = [a for a in sys.argv[1:] if a != "--comparar"]
        if len(resto) != 2:
            print("uso: python puertas/estructura.py --comparar <html A> <html B>")
            return 2
        return comparar_ficheros(resto[0], resto[1])
    return _comun.ejecutar("estructura", puerta)


if __name__ == "__main__":
    sys.exit(main())
