"""AIFEC — fábrica de temas: lector de HTML y esqueleto de las cinco superficies.

Convierte una página en un árbol (con la biblioteca estándar, tolerante con el HTML mal cerrado), busca
elementos por clase y reduce cada superficie de la tienda (cabecera, tarjeta, listado, ficha y pie) a su
esqueleto: una lista de marcas «profundidad:etiqueta.clases-af» en orden. Las clases `af-…` del contrato se
conservan; las demás clases no cuentan (ni su nombre ni que existan); el texto, los atributos y las imágenes no
cuentan, y los elementos hermanos repetidos seguidos cuentan como uno. Con eso, cambiar nombres, textos,
colores o el número de productos no engaña al comparador: solo cuenta la composición.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

from difflib import SequenceMatcher
from html.parser import HTMLParser

# Etiquetas sin cierre.
VACIAS = frozenset(["area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param",
                    "source", "track", "wbr"])
# Lo que no es composición: guiones, estilos, iconos en línea e imágenes.
IGNORADAS = frozenset(["script", "style", "noscript", "template", "svg", "img", "picture", "source", "head"])
# Etiquetas que se cierran solas al abrir otra de su familia.
AUTOCIERRE = {
    "li": {"li"}, "p": {"p"}, "option": {"option"}, "dt": {"dt", "dd"}, "dd": {"dt", "dd"},
    "tr": {"tr", "td", "th"}, "td": {"td", "th"}, "th": {"td", "th"},
}

# superficie -> (clase del contrato, páginas donde buscarla, en este orden)
SUPERFICIES = {
    "cabecera": ("af-header", ("portada", "listado", "ficha", "carrito", "muestra")),
    "tarjeta": ("af-product-card", ("listado", "portada", "ficha", "muestra")),
    "listado": ("af-listing", ("listado",)),
    "ficha": ("af-product", ("ficha",)),
    "pie": ("af-footer", ("portada", "listado", "ficha", "carrito", "muestra")),
}


class Nodo:
    """Un elemento: etiqueta, atributos y sus hijos."""

    __slots__ = ("etiqueta", "atributos", "hijos", "padre", "texto")

    def __init__(self, etiqueta: str, atributos: dict, padre=None):
        self.etiqueta = etiqueta
        self.atributos = atributos
        self.hijos = []
        self.padre = padre
        self.texto = ""  # el texto que lleva directamente dentro

    @property
    def clases(self) -> list:
        return (self.atributos.get("class") or "").split()

    def tiene_clase(self, clase: str) -> bool:
        return clase in self.clases

    def recorrer(self):
        """Él mismo y todos sus descendientes, en el orden del documento."""
        pila = [self]
        while pila:
            nodo = pila.pop()
            yield nodo
            pila.extend(reversed(nodo.hijos))

    def buscar(self, predicado):
        for nodo in self.recorrer():
            if predicado(nodo):
                return nodo
        return None

    def buscar_todos(self, predicado) -> list:
        return [n for n in self.recorrer() if predicado(n)]

    def con_clase(self, clase: str):
        return self.buscar(lambda n: n.tiene_clase(clase))


class _Lector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = Nodo("#raiz", {})
        self.pila = [self.raiz]

    def _abrir(self, etiqueta, atributos):
        cierra = AUTOCIERRE.get(etiqueta)
        if cierra and len(self.pila) > 1 and self.pila[-1].etiqueta in cierra:
            self.pila.pop()
        nodo = Nodo(etiqueta, {k: (v or "") for k, v in atributos}, self.pila[-1])
        self.pila[-1].hijos.append(nodo)
        return nodo

    def handle_starttag(self, etiqueta, atributos):
        nodo = self._abrir(etiqueta, atributos)
        if etiqueta not in VACIAS:
            self.pila.append(nodo)

    def handle_startendtag(self, etiqueta, atributos):
        self._abrir(etiqueta, atributos)

    def handle_data(self, datos):
        if len(self.pila) > 1 and datos.strip():
            self.pila[-1].texto += datos.strip() + " "

    def handle_endtag(self, etiqueta):
        if etiqueta in VACIAS:
            return
        for posicion in range(len(self.pila) - 1, 0, -1):
            if self.pila[posicion].etiqueta == etiqueta:
                del self.pila[posicion:]
                return


def leer(html: str) -> Nodo:
    """El árbol de una página. Nunca falla: lo que no entiende lo deja pasar."""
    lector = _Lector()
    try:
        lector.feed(html)
        lector.close()
    except Exception:  # un HTML que revienta al lector no debe tirar la puerta
        pass
    return lector.raiz


# ------------------------------------------------------------------ esqueleto


def _marca(nodo: Nodo) -> str:
    """La etiqueta y sus clases del contrato (`af-…`). Las demás clases no cuentan: ni su nombre ni que existan,
    así que renombrar o añadir clases propias no cambia la marca."""
    return nodo.etiqueta + "".join("." + c for c in nodo.clases if c.startswith("af-"))


def _hijos_utiles(nodo: Nodo) -> list:
    """Los hijos que cuentan, sin los hermanos repetidos seguidos (misma marca = uno solo)."""
    utiles = []
    anterior = None
    for hijo in nodo.hijos:
        if hijo.etiqueta in IGNORADAS:
            continue
        marca = _marca(hijo)
        if marca == anterior:
            continue
        anterior = marca
        utiles.append(hijo)
    return utiles


def esqueleto(raiz: Nodo) -> list:
    """La lista de marcas «profundidad:etiqueta.clases» de un elemento y todo lo que lleva dentro."""
    marcas = []
    pila = [(raiz, 0)]
    while pila:
        nodo, profundidad = pila.pop()
        marcas.append("%d:%s" % (profundidad, _marca(nodo)))
        for hijo in reversed(_hijos_utiles(nodo)):
            pila.append((hijo, profundidad + 1))
    return marcas


def superficies_de(arbol: Nodo) -> dict:
    """De una página: superficie -> esqueleto, solo las que trae."""
    encontradas = {}
    for nombre, (clase, _paginas) in SUPERFICIES.items():
        nodo = arbol.con_clase(clase)
        if nodo is not None:
            encontradas[nombre] = esqueleto(nodo)
    return encontradas


def superficies_de_paginas(paginas: dict) -> dict:
    """De las páginas de un tema (`{"portada": html, …}`): para cada superficie, la de la primera página donde sale."""
    arboles = {nombre: leer(html) for nombre, html in paginas.items() if isinstance(html, str) and html}
    resultado = {}
    for nombre, (clase, donde) in SUPERFICIES.items():
        for pagina in donde:
            if pagina not in arboles:
                continue
            nodo = arboles[pagina].con_clase(clase)
            if nodo is not None:
                resultado[nombre] = esqueleto(nodo)
                break
    return resultado


def parecido(a: list, b: list) -> float:
    """Cuánto se parecen dos esqueletos, de 0 a 1."""
    if not a and not b:
        return 1.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def comparar(a: dict, b: dict) -> dict:
    """Superficie -> parecido, solo de las superficies que están en los dos."""
    return {nombre: parecido(a[nombre], b[nombre]) for nombre in SUPERFICIES if nombre in a and nombre in b}
