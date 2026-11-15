"""AIFEC — fábrica de temas: puerta «movil» (contrato de móvil, contratos/04-temas.md § 7).

En lo pintado (portada, listado, ficha y carrito del banco): hay cabecera `af-header`, hay barra inferior
`af-mobile-bar` con accesos REALES a Buscar y Carrito (un enlace con dirección o un botón que abre un panel que
existe en la página; nunca un `#` ni un panel que no está), el carrito trae su contador (`data-af-cart-count`),
cada acceso tiene nombre accesible, y Filtros solo sale donde la página tiene filtros (y entonces su panel
existe). En la hoja, tal como la carga el tema (la de sus padres y la suya): cabecera pegajosa, barra fija,
`env(safe-area-inset-bottom)`, espacio reservado bajo el contenido, zonas táctiles de 44 px y foco visible.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402
import _css  # noqa: E402
import _html  # noqa: E402

TACTIL = 44.0


def _ids(arbol) -> set:
    return {n.atributos["id"] for n in arbol.recorrer() if n.atributos.get("id")}


def _con_nombre(nodo) -> bool:
    """¿Tiene nombre un acceso? Un aria-label o title en él o dentro, o texto visible (la etiqueta de la barra)."""
    for hijo in nodo.recorrer():
        if hijo.atributos.get("aria-label", "").strip() or hijo.atributos.get("title", "").strip() or hijo.texto.strip():
            return True
    return False


def _acceso_real(nodo, ids: set):
    """Devuelve (es real, motivo si no). Un enlace con dirección, o algo que abre un panel que existe."""
    abre = nodo.atributos.get("data-af-drawer-open", "").strip()
    if abre:
        if abre in ids:
            return True, ""
        return False, "abre el panel «%s» y la página no lo trae" % abre
    if nodo.etiqueta == "a":
        destino = nodo.atributos.get("href", "").strip()
        if destino and destino != "#" and not destino.lower().startswith("javascript:"):
            return True, ""
        return False, "es un enlace sin dirección"
    if nodo.etiqueta == "button" and nodo.atributos.get("type", "").lower() == "submit":
        return True, ""
    return False, "no es un enlace ni abre ningún panel"


def mirar_pagina(nombre: str, html: str) -> list:
    """Problemas de una página pintada (lista vacía si cumple)."""
    problemas = []
    arbol = _html.leer(html)
    ids = _ids(arbol)
    if arbol.con_clase("af-header") is None:
        problemas.append("«%s»: no hay cabecera (clase af-header)" % nombre)
    barra = arbol.con_clase("af-mobile-bar")
    if barra is None:
        problemas.append("«%s»: no hay barra inferior de móvil (clase af-mobile-bar)" % nombre)
        return problemas
    accesos = [n for n in barra.recorrer() if n is not barra and n.etiqueta in ("a", "button")]

    def abre(nodo) -> str:
        return nodo.atributos.get("data-af-drawer-open", "").lower()

    def cuenta_carrito(nodo) -> bool:
        return any("data-af-cart-count" in c.atributos for c in nodo.recorrer())

    def rotulo(nodo) -> str:
        """Lo que dice un acceso: su texto y los aria-label y title que lleve dentro."""
        return " ".join([n.texto + " " + n.atributos.get("aria-label", "") + " " + n.atributos.get("title", "") for n in nodo.recorrer()])

    buscar = [n for n in accesos if "search" in abre(n) or re.search(r"(buscar|search)", n.atributos.get("href", "") + " " + rotulo(n), re.I)]
    carrito = [n for n in accesos if cuenta_carrito(n) or "cart" in abre(n)
               or re.search(r"(carrito|cart|cesta)", n.atributos.get("href", "") + " " + rotulo(n), re.I)]
    if not buscar:
        problemas.append("«%s»: la barra no tiene el acceso a Buscar" % nombre)
    if not carrito:
        problemas.append("«%s»: la barra no tiene el acceso a Carrito" % nombre)
    for acceso in buscar[:1] + carrito[:1]:
        real, motivo = _acceso_real(acceso, ids)
        if not real:
            problemas.append("«%s»: un acceso de la barra no funciona (%s)" % (nombre, motivo))
    if carrito and not any(cuenta_carrito(a) for a in carrito):
        problemas.append("«%s»: el acceso a Carrito no tiene contador (data-af-cart-count)" % nombre)
    if any(not _con_nombre(a) for a in accesos):
        problemas.append("«%s»: un acceso de la barra no tiene nombre accesible (ni texto ni aria-label)" % nombre)
    filtros_en_barra = [n for n in accesos if "filter" in abre(n)]
    hay_filtros = arbol.con_clase("af-listing-filters") is not None
    if filtros_en_barra and not hay_filtros and nombre != "muestra":
        problemas.append("«%s»: la barra enseña Filtros y la página no tiene filtros (af-listing-filters)" % nombre)
    if hay_filtros and not filtros_en_barra:
        problemas.append("«%s»: la página tiene filtros y la barra no enseña el botón Filtros" % nombre)
    for acceso in filtros_en_barra:
        if abre(acceso) not in {i.lower() for i in ids}:
            problemas.append("«%s»: el botón Filtros abre un panel que no está en la página" % nombre)
    return problemas


def mirar_hoja(texto: str) -> tuple:
    """(problemas, comprobaciones hechas) de la hoja efectiva."""
    problemas = []
    hechas = []
    reglas = _css.analizar(texto)
    variables = _css.variables(reglas)
    if not reglas:
        return ["el tema no trae ninguna hoja de estilos"], hechas

    posicion = _css.declarada(reglas, "af-header", "position", solo_movil=True)
    if (posicion or "").lower() in ("sticky", "fixed", "-webkit-sticky"):
        hechas.append("cabecera pegajosa (position: %s)" % posicion)
    else:
        problemas.append("la cabecera (.af-header) no es pegajosa: falta position: sticky o fixed")

    posicion = _css.declarada(reglas, "af-mobile-bar", "position", solo_movil=True)
    if (posicion or "").lower() in ("fixed", "sticky", "-webkit-sticky"):
        hechas.append("barra inferior fija (position: %s)" % posicion)
    else:
        problemas.append("la barra de móvil (.af-mobile-bar) no es fija: falta position: fixed")

    if re.search(r"env\(\s*safe-area-inset-bottom", texto):
        hechas.append("respeta env(safe-area-inset-bottom)")
    else:
        problemas.append("la hoja no usa env(safe-area-inset-bottom): la barra se pisaría con la zona del sistema")

    reservado = False
    for regla in reglas:
        if not regla.vale_en_movil:
            continue
        if any(re.search(r"\.af-has-bar(?![\w-])|^body$|\.af-main(?![\w-])|^main$", s.split()[-1] if s.split() else "") for s in regla.selectores):
            if any(p in regla.declaraciones and regla.declaraciones[p].strip() not in ("0", "0px")
                   for p in ("padding-bottom", "margin-bottom", "padding", "scroll-padding-bottom")):
                reservado = True
    if reservado:
        hechas.append("espacio reservado bajo el contenido")
    else:
        problemas.append("el contenido no reserva el alto de la barra: falta padding-bottom en .af-has-bar (o en body/main)")

    alto = None
    ancho = None
    for regla in _css.reglas_de(reglas, "af-mobile-bar-item", solo_movil=True):
        for propiedad in ("min-height", "height"):
            if propiedad in regla.declaraciones:
                alto = _css.a_pixeles(regla.declaraciones[propiedad], variables)
        if "min-width" in regla.declaraciones:
            ancho = _css.a_pixeles(regla.declaraciones["min-width"], variables)
        if "flex" in regla.declaraciones and ancho is None:
            ancho = TACTIL
    if alto is None:
        problemas.append("no se puede saber el alto de .af-mobile-bar-item: declara min-height con una medida en px, rem o una variable de :root")
    elif alto < TACTIL:
        problemas.append("la zona táctil de la barra mide %d px de alto y el mínimo es 44" % alto)
    else:
        hechas.append("zona táctil de la barra: %d px de alto" % alto)
    if ancho is not None and ancho < TACTIL:
        problemas.append("la zona táctil de la barra mide %d px de ancho y el mínimo es 44" % ancho)
    if ":focus-visible" in texto:
        hechas.append("foco visible (:focus-visible)")
    else:
        problemas.append("la hoja no define :focus-visible: el foco del teclado no se vería")
    return problemas, hechas


def puerta(ctx) -> int:
    problemas = []
    detalles = []
    hoja = _comun.hoja_efectiva(ctx)
    de_hoja, hechas = mirar_hoja(hoja)
    problemas += de_hoja
    detalles += ["bien: " + h for h in hechas]

    try:
        paginas = _comun.paginas_de(ctx, ctx.slug)
    except _comun.NoAplica as motivo:
        paginas = _comun.Paginas(ctx.slug)
        detalles.append("no se pudo pintar el tema, así que lo pintado no se mira: %s" % motivo)
    mirar = ("portada", "listado", "ficha", "carrito") if not paginas.muestra else ("portada", "listado", "carrito")
    miradas = 0
    for nombre in mirar:
        html = paginas.html.get(nombre)
        if html is None:
            continue
        miradas += 1
        problemas += mirar_pagina(nombre, html)
    if paginas.html and miradas == 0:
        problemas.append("no hay ninguna página pintada que mirar")
    detalles += paginas.notas
    medidas = {"paginas_miradas": miradas, "problemas": len(problemas)}
    if not paginas.html and not problemas:
        return ctx.terminar(_comun.NO_APLICA, "solo se pudo mirar la hoja: no hay páginas pintadas (banco sin preparar)", detalles, medidas)
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas + detalles, medidas)
    return ctx.terminar(_comun.PASA, "contrato de móvil cumplido en %d páginas y en la hoja" % miradas, detalles, medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("movil", puerta))
