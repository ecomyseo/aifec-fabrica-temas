"""AIFEC — fábrica de temas: lector de hojas de estilo.

Lo justo para que la puerta de móvil mire reglas de verdad y no cadenas sueltas: separa la hoja en reglas
(con los `@media` en que viven), lee sus declaraciones, recoge las variables de `:root` y convierte una
medida a píxeles cuando se puede (`44px`, `2.75rem`, `var(--bar-h)`).

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re

_COMENTARIOS = re.compile(r"/\*.*?\*/", re.S)
_ARROBAS_SIN_REGLAS = ("@keyframes", "@-webkit-keyframes", "@font-face", "@page", "@property", "@counter-style")
_VAR = re.compile(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)")


class Regla:
    """Una regla de la hoja: sus selectores, sus declaraciones y los `@media` que la envuelven."""

    __slots__ = ("selectores", "declaraciones", "medios")

    def __init__(self, selectores, declaraciones, medios):
        self.selectores = selectores
        self.declaraciones = declaraciones
        self.medios = medios

    @property
    def es_de_impresion(self) -> bool:
        return any("print" in m.lower() for m in self.medios)

    @property
    def vale_en_movil(self) -> bool:
        """False si la regla solo existe a partir de un ancho de ordenador (`min-width` mayor que 430 px)."""
        for medio in self.medios:
            for numero, unidad in re.findall(r"min-width\s*:\s*([0-9.]+)\s*(px|em|rem)", medio.lower()):
                if float(numero) * (1 if unidad == "px" else 16) > 430:
                    return False
        return not self.es_de_impresion


def _trozos(texto: str, separador: str) -> list:
    """Parte por un separador sin romper lo que va entre paréntesis, corchetes o comillas."""
    trozos = []
    actual = []
    profundidad = 0
    comilla = ""
    for caracter in texto:
        if comilla:
            actual.append(caracter)
            if caracter == comilla:
                comilla = ""
            continue
        if caracter in "\"'":
            comilla = caracter
        elif caracter in "([":
            profundidad += 1
        elif caracter in ")]":
            profundidad = max(0, profundidad - 1)
        elif caracter == separador and profundidad == 0:
            trozos.append("".join(actual))
            actual = []
            continue
        actual.append(caracter)
    trozos.append("".join(actual))
    return trozos


def _declaraciones(cuerpo: str) -> dict:
    declaraciones = {}
    for trozo in _trozos(cuerpo, ";"):
        if ":" not in trozo:
            continue
        propiedad, valor = trozo.split(":", 1)
        propiedad = propiedad.strip().lower()
        valor = re.sub(r"\s*!important\s*$", "", valor.strip(), flags=re.I)
        if propiedad:
            declaraciones[propiedad] = valor
    return declaraciones


def _bloques(texto: str) -> list:
    """Los pares (preludio, cuerpo) del primer nivel de un trozo de hoja."""
    bloques = []
    profundidad = 0
    inicio = 0
    preludio = ""
    comilla = ""
    for posicion, caracter in enumerate(texto):
        if comilla:
            if caracter == comilla:
                comilla = ""
            continue
        if caracter in "\"'":
            comilla = caracter
        elif caracter == "{":
            if profundidad == 0:
                preludio = texto[inicio:posicion].strip()
                inicio = posicion + 1
            profundidad += 1
        elif caracter == "}":
            profundidad -= 1
            if profundidad == 0:
                bloques.append((preludio, texto[inicio:posicion]))
                inicio = posicion + 1
            elif profundidad < 0:
                profundidad = 0
                inicio = posicion + 1
    return bloques


def _reglas(texto: str, medios: tuple) -> list:
    reglas = []
    for preludio, cuerpo in _bloques(texto):
        if preludio.startswith("@"):
            if preludio.lower().startswith(_ARROBAS_SIN_REGLAS):
                continue
            reglas.extend(_reglas(cuerpo, medios + (preludio,)))
            continue
        selectores = [s.strip() for s in _trozos(preludio, ",") if s.strip()]
        if selectores:
            reglas.append(Regla(selectores, _declaraciones(cuerpo), medios))
    return reglas


def analizar(texto: str) -> list:
    """Todas las reglas de una hoja, en orden."""
    return _reglas(_COMENTARIOS.sub("", texto), ())


def variables(reglas: list) -> dict:
    """Las variables (`--x`) declaradas en `:root`, `html` o `body`; la última declaración gana."""
    encontradas = {}
    for regla in reglas:
        if regla.es_de_impresion:
            continue
        if not any(re.fullmatch(r"(:where\()?(:root|html|body)\)?", s.strip()) for s in regla.selectores):
            continue
        for propiedad, valor in regla.declaraciones.items():
            if propiedad.startswith("--"):
                encontradas[propiedad] = valor
    return encontradas


def apunta_a(selector: str, clase: str) -> bool:
    """¿El último tramo del selector (el elemento al que se aplica) lleva esa clase?"""
    ultimo = re.split(r"[\s>+~]+", selector.strip())[-1] if selector.strip() else ""
    return re.search(r"\." + re.escape(clase) + r"(?![\w-])", ultimo) is not None


def reglas_de(reglas: list, clase: str, sin_impresion: bool = True, solo_movil: bool = False) -> list:
    """Las reglas cuyo elemento destino lleva esa clase (con `solo_movil`, las que valen a 390 px de ancho)."""
    return [r for r in reglas if any(apunta_a(s, clase) for s in r.selectores)
            and not (sin_impresion and r.es_de_impresion) and (r.vale_en_movil or not solo_movil)]


def declarada(reglas: list, clase: str, propiedad: str, solo_movil: bool = False):
    """El último valor de esa propiedad en las reglas de esa clase (None si ninguna la declara)."""
    valor = None
    for regla in reglas_de(reglas, clase, solo_movil=solo_movil):
        if propiedad in regla.declaraciones:
            valor = regla.declaraciones[propiedad]
    return valor


def a_pixeles(valor, variables_css: dict, _nivel: int = 0):
    """Una medida en píxeles, o None si no se puede saber sin un navegador (porcentajes, calc con variables…)."""
    if valor is None or _nivel > 6:
        return None
    texto = str(valor).strip().lower()
    encontrada = _VAR.fullmatch(texto)
    if encontrada:
        interior = variables_css.get(encontrada.group(1))
        if interior is None:
            interior = encontrada.group(2)
        return a_pixeles(interior, variables_css, _nivel + 1)
    medida = re.fullmatch(r"(-?[0-9]*\.?[0-9]+)(px|rem|em)?", texto)
    if medida:
        numero = float(medida.group(1))
        return numero * 16 if medida.group(2) in ("rem", "em") else numero
    suma = re.fullmatch(r"calc\((.+)\)", texto)
    if suma:
        # En CSS los operadores de calc() van entre espacios: «var(--a) + 4px».
        partes = re.split(r"\s+([+-])\s+", suma.group(1).strip())
        total = 0.0
        signo = "+"
        for posicion, parte in enumerate(partes):
            if posicion % 2 == 1:
                signo = parte
                continue
            medida_parte = a_pixeles(parte.strip(), variables_css, _nivel + 1)
            if medida_parte is None:
                return None
            total += -medida_parte if signo == "-" else medida_parte
        return total
    return None
