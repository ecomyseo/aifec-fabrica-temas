"""AIFEC — motor de fábrica: los motores que hacen el trabajo.

Hay tres: `manual` (una persona), `simulado` (copia un trabajo ya hecho, para pruebas) y `orden`
(lanza el programa que diga el plan, por ejemplo una IA de programación). Ninguno escribe fuera de
`salida/<slug>/`: tras cada sesión se compara una instantánea de la carpeta de la fábrica.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

from . import estado, procesos

_MARCAS = re.compile(r"\{(encargo|texto|trabajo|fabrica)\}")


class Resultado:
    """Lo que devuelve un motor: `listo`, `espera` (una persona tiene que hacer algo), `fallo`
    (se rechaza el intento) o `tope` (el gasto no lo permite y no se lanzó nada)."""

    def __init__(self, estado_: str, motivo: str = ""):
        self.estado = estado_
        self.motivo = motivo


def sustituir(orden: list, valores: dict) -> list:
    """Cambia {encargo}, {texto}, {trabajo} y {fabrica} en una sola pasada (lo que contenga un
    valor no se vuelve a sustituir)."""
    return [_MARCAS.sub(lambda m: str(valores[m.group(1)]), argumento) for argumento in orden]


def sustituir_marcas(orden: list, marcas: dict) -> list:
    """Como `sustituir`, pero con las marcas que se le den ({slug}, {nombre}, {mensaje}…)."""
    patron = re.compile(r"\{(" + "|".join(re.escape(k) for k in marcas) + r")\}")
    return [patron.sub(lambda m: str(marcas[m.group(1)]), argumento) for argumento in orden]


def _coste_sesion_centimos(ctx) -> int:
    return estado.centimos(ctx.plan["gasto"]["por_sesion_eur"])


def puede_lanzar(ctx):
    """¿Se puede empezar una sesión? Solo el motor `orden` gasta: con tope 0 no se lanza nunca, y si
    lo gastado más una sesión pasa del tope, tampoco."""
    if ctx.plan["motor"]["tipo"] != "orden":
        return True, ""
    tope = estado.centimos(ctx.plan["gasto"]["tope_eur"])
    gastado = ctx.libro.gastado_centimos()
    sesion = _coste_sesion_centimos(ctx)
    if tope <= 0:
        return False, "tope de gasto: el tope es 0 y el motor «orden» es de pago"
    if gastado + sesion > tope:
        return False, "tope de gasto: gastado %.2f € y la sesión costaría %.2f € (tope %.2f €)" % (
            gastado / 100.0, sesion / 100.0, tope / 100.0)
    return True, ""


def _hay_algo(carpeta: Path) -> bool:
    return carpeta.is_dir() and any(True for _ in carpeta.rglob("*") if _.is_file())


def instantanea(ctx, slug: str) -> dict:
    """Fecha y tamaño de cada fichero de la fábrica, salvo `salida/<slug>/`, `estado/`, `escaparate/`
    y las cachés de Python (que son lo único donde un motor puede escribir)."""
    raiz = ctx.raiz
    propia = ctx.rutas.salida_de(slug)
    ignorar = {ctx.rutas.estado, ctx.rutas.escaparate, propia, ctx.rutas.cola}
    nombres_ignorados = {"__pycache__", ".git"}
    resultado = {}
    for carpeta, subcarpetas, ficheros in os.walk(str(raiz)):
        actual = Path(carpeta)
        subcarpetas[:] = [s for s in subcarpetas
                          if s not in nombres_ignorados and (actual / s) not in ignorar]
        for fichero in ficheros:
            ruta = actual / fichero
            if ruta == ctx.rutas.cola:
                continue
            try:
                datos = ruta.stat()
            except OSError:
                continue
            resultado[ruta.relative_to(raiz).as_posix()] = (datos.st_size, datos.st_mtime_ns)
    return resultado


def diferencias(antes: dict, despues: dict) -> list:
    """Ficheros nuevos, cambiados o borrados entre dos instantáneas."""
    cambios = []
    for nombre in sorted(set(antes) | set(despues)):
        if nombre not in antes:
            cambios.append("nuevo: " + nombre)
        elif nombre not in despues:
            cambios.append("borrado: " + nombre)
        elif antes[nombre] != despues[nombre]:
            cambios.append("cambiado: " + nombre)
    return cambios


def _manual(ctx, slug: str, ruta_encargo: Path) -> Resultado:
    datos = ctx.cola.estado(slug)
    if datos.get("entregado"):
        return Resultado("listo")
    ctx.cola.fijar(slug, entregado=True)
    return Resultado(
        "espera",
        "el encargo está en %s; cuando el trabajo esté en salida/%s/, vuelve a lanzar `python fabrica.py trabajar`"
        % (ruta_encargo.relative_to(ctx.raiz).as_posix() if str(ruta_encargo).startswith(str(ctx.raiz))
           else ruta_encargo, slug))


def _simulado(ctx, slug: str) -> Resultado:
    origen = Path(ctx.plan["motor"]["origen"])
    if not origen.is_dir():
        return Resultado("fallo", "motor.origen no existe: %s" % origen)
    destino = ctx.rutas.salida_de(slug)
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(origen), str(destino), dirs_exist_ok=True)
    return Resultado("listo")


def _orden(ctx, slug: str, ruta_encargo: Path, texto: str) -> Resultado:
    permitido, motivo = puede_lanzar(ctx)
    if not permitido:
        return Resultado("tope", motivo)
    motor = ctx.plan["motor"]
    trabajo = ctx.rutas.salida_de(slug)
    trabajo.mkdir(parents=True, exist_ok=True)
    orden = sustituir(motor["orden"], {
        "encargo": ruta_encargo, "texto": texto, "trabajo": trabajo, "fabrica": ctx.raiz})
    numero = len(list(ctx.rutas.sesiones.glob(slug + "-*.log"))) + 1 if ctx.rutas.sesiones.is_dir() else 1
    registro = ctx.rutas.sesiones / ("%s-%d.log" % (slug, numero))
    reservado = _coste_sesion_centimos(ctx)
    # Se apunta antes de lanzar: una sesión cortada a mitad también ha costado.
    ctx.libro.anotar(slug, reservado / 100.0, ctx.ahora())
    ctx.apuntar("motor orden: lanzo %s (sesión %d, límite %s min)" % (slug, numero, motor["minutos"]))
    codigo = procesos.lanzar(orden, trabajo, registro, motor["minutos"])
    if motor.get("coste_regex"):
        try:
            salida = registro.read_text(encoding="utf-8", errors="replace")
            encontrado = re.search(motor["coste_regex"], salida)
            if encontrado:
                real = estado.centimos(float(encontrado.group(1).replace(",", ".")))
                if real != reservado:
                    ctx.libro.anotar(slug, (real - reservado) / 100.0, ctx.ahora())
        except (OSError, ValueError, IndexError):
            ctx.apuntar("no pude leer el coste de la sesión en %s" % registro.name)
    if codigo == procesos.TIEMPO_AGOTADO:
        return Resultado("fallo", "el motor se pasó del tiempo (%s min) y se cortó" % motor["minutos"])
    if codigo != 0:
        return Resultado("fallo", "el motor terminó con código %s (ver %s)" % (
            codigo, registro.relative_to(ctx.raiz).as_posix()))
    return Resultado("listo")


def ejecutar(ctx, slug: str, ruta_encargo, texto: str) -> Resultado:
    """Una sesión del motor del plan sobre el encargo `slug`."""
    tipo = ctx.plan["motor"]["tipo"]
    ruta_encargo = Path(ruta_encargo)
    if tipo == "manual":
        return _manual(ctx, slug, ruta_encargo)
    if tipo == "simulado":
        return _simulado(ctx, slug)
    if tipo == "orden":
        return _orden(ctx, slug, ruta_encargo, texto)
    return Resultado("fallo", "motor desconocido: %s" % tipo)
