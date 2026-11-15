"""AIFEC — motor de fábrica: la cola de encargos y el estado de cada uno.

La cola (`cola.json`) es una lista de encargos con `slug` obligatorio y único. El estado de cada
encargo vive aparte, en `estado/encargos/<slug>.json`, con su historial y solo las transiciones
permitidas: cualquier otra es un error.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
from datetime import datetime

from . import estado

ESTADOS = ("pendiente", "en_curso", "en_puertas", "hecho", "aprobado", "rechazado", "atascado")

TRANSICIONES = {
    "pendiente": {"en_curso"},
    "en_curso": {"en_puertas"},
    "en_puertas": {"hecho", "rechazado"},
    "hecho": {"aprobado", "rechazado"},
    "aprobado": {"rechazado"},
    "rechazado": {"en_curso", "atascado"},
    "atascado": set(),
}

_SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class ColaInvalida(Exception):
    """La cola no vale (slug mal escrito o repetido, o no es una lista)."""


class TransicionInvalida(Exception):
    """Se intentó pasar un encargo a un estado al que no puede ir desde el que tiene."""


def slug_valido(slug) -> bool:
    return isinstance(slug, str) and bool(_SLUG.match(slug))


def validar(encargos) -> list:
    """Errores de una lista de encargos (vacía si todo está bien)."""
    errores = []
    if not isinstance(encargos, list):
        return ["la cola tiene que ser una lista de encargos"]
    vistos = set()
    for posicion, encargo in enumerate(encargos, 1):
        if not isinstance(encargo, dict):
            errores.append("encargo %d: tiene que ser un objeto" % posicion)
            continue
        slug = encargo.get("slug")
        if not slug_valido(slug):
            errores.append("encargo %d: «slug» obligatorio, en minúsculas y con guiones (valor: %r)" % (posicion, slug))
            continue
        if slug in vistos:
            errores.append("encargo %d: el slug «%s» está repetido" % (posicion, slug))
        vistos.add(slug)
        if "nombre" in encargo and not isinstance(encargo["nombre"], str):
            errores.append("encargo «%s»: «nombre» tiene que ser un texto" % slug)
    return errores


class Cola:
    def __init__(self, rutas, reloj=None):
        self.rutas = rutas
        self._reloj = reloj or datetime.now

    def ahora(self) -> datetime:
        return self._reloj()

    # ---- la lista de encargos -------------------------------------------------------------

    def encargos(self) -> list:
        datos = estado.leer(self.rutas.cola, [])
        if isinstance(datos, dict) and isinstance(datos.get("encargos"), list):
            datos = datos["encargos"]
        errores = validar(datos)
        if errores:
            raise ColaInvalida("cola.json: " + "; ".join(errores))
        return datos

    def obtener(self, slug: str) -> dict:
        for encargo in self.encargos():
            if encargo["slug"] == slug:
                return encargo
        raise ColaInvalida("no hay ningún encargo con slug «%s» en la cola" % slug)

    def anadir(self, encargo: dict) -> None:
        actuales = self.encargos() if self.rutas.cola.exists() else []
        nueva = actuales + [encargo]
        errores = validar(nueva)
        if errores:
            raise ColaInvalida("; ".join(errores))
        estado.escribir(self.rutas.cola, nueva)

    # ---- el estado de cada encargo --------------------------------------------------------

    def estado(self, slug: str) -> dict:
        datos = estado.leer(self.rutas.estado_de(slug), None)
        if isinstance(datos, dict) and datos.get("estado") in ESTADOS:
            return datos
        return {"slug": slug, "estado": "pendiente", "intentos": 0, "motivo": "", "historial": []}

    def guardar(self, slug: str, datos: dict) -> None:
        estado.escribir(self.rutas.estado_de(slug), datos)

    def fijar(self, slug: str, **campos) -> dict:
        datos = self.estado(slug)
        datos.update(campos)
        self.guardar(slug, datos)
        return datos

    def transicionar(self, slug: str, a: str, nota: str = "", **campos) -> dict:
        """Pasa el encargo a `a` si se puede; apunta el paso con fecha en el historial."""
        datos = self.estado(slug)
        actual = datos["estado"]
        if a not in ESTADOS or a not in TRANSICIONES.get(actual, set()):
            raise TransicionInvalida("un encargo «%s» no puede pasar a «%s»" % (actual, a))
        datos["historial"] = list(datos.get("historial") or []) + [
            {"fecha": self.ahora().isoformat(timespec="seconds"), "de": actual, "a": a, "nota": nota}]
        datos["estado"] = a
        datos.update(campos)
        self.guardar(slug, datos)
        return datos

    def comenzar_intento(self, slug: str) -> dict:
        """pendiente o rechazado → en_curso, y cuenta un intento más."""
        intentos = int(self.estado(slug).get("intentos") or 0) + 1
        return self.transicionar(slug, "en_curso", "intento %d" % intentos, intentos=intentos, entregado=False)

    def rechazar(self, slug: str, motivo: str, max_intentos: int) -> str:
        """hecho, aprobado o en_puertas → rechazado (con el motivo) y, si ya no quedan intentos,
        atascado. Devuelve el estado final."""
        datos = self.transicionar(slug, "rechazado", motivo, motivo=motivo)
        if int(datos.get("intentos") or 0) >= int(max_intentos):
            self.transicionar(slug, "atascado", "intentos agotados (%d)" % int(max_intentos))
            return "atascado"
        return "rechazado"

    def en_orden_de_trabajo(self, max_intentos: int) -> list:
        """Los slugs que quedan por trabajar, en el orden en que se les dará: primero los que
        quedaron a medias (en_curso o en_puertas), después los rechazados con intentos, después los
        pendientes; dentro de cada grupo, en el orden de la cola."""
        encargos = self.encargos()
        estados = {e["slug"]: self.estado(e["slug"]) for e in encargos}
        lista = []
        for grupo in (("en_curso", "en_puertas"), ("rechazado",), ("pendiente",)):
            for encargo in encargos:
                datos = estados[encargo["slug"]]
                if datos["estado"] not in grupo:
                    continue
                if datos["estado"] == "rechazado" and int(datos.get("intentos") or 0) >= int(max_intentos):
                    continue
                lista.append(encargo["slug"])
        return lista

    def siguiente(self, max_intentos: int):
        """El slug que toca ahora, o None si no queda nada por trabajar."""
        lista = self.en_orden_de_trabajo(max_intentos)
        return lista[0] if lista else None

    def cuentas(self) -> dict:
        cuentas = {e: 0 for e in ESTADOS}
        for encargo in self.encargos():
            cuentas[self.estado(encargo["slug"])["estado"]] += 1
        return cuentas
