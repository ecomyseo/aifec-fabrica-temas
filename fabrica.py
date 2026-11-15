"""AIFEC — fábrica: la orden única.

    python fabrica.py estado | calendario | trabajar | parar | reanudar | anadir | encargo |
                      puertas | aprobar | rechazar | instalar | escaparate | banco

Códigos de salida: 0 bien · 1 algo no pasa · 2 uso incorrecto o plan inválido · 3 parada por tope de
gasto · 4 parada por atascos · 5 hay otra fábrica trabajando.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from motor import banco, cola as cola_mod, escaparate, nucleo, plan as plan_mod, puertas  # noqa: E402


def _reloj():
    """Para pruebas: `AIFEC_AHORA=2026-11-13T10:00:00` fija la hora de la fábrica."""
    fijo = os.environ.get("AIFEC_AHORA")
    if not fijo:
        return None
    instante = datetime.fromisoformat(fijo)
    return lambda: instante


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fabrica.py", description="La orden única de la fábrica de AIFEC.")
    sub = parser.add_subparsers(dest="orden", metavar="orden")
    sub.add_parser("estado", help="día, cupo, hechos hoy, en curso, atascados, siguiente, gasto")
    sub.add_parser("calendario", help="qué haría cada día hasta vaciar la cola")
    p = sub.add_parser("trabajar", help="lo de hoy, o un solo encargo")
    p.add_argument("--uno", action="store_true", help="un solo encargo y para")
    p.add_argument("--slug", help="trabaja solo este encargo (sin mirar horario ni cupo)")
    sub.add_parser("parar", help="acaba el encargo en curso y no empieza otro")
    sub.add_parser("reanudar", help="vuelve a trabajar")
    p = sub.add_parser("anadir", help="añade un encargo a la cola")
    p.add_argument("--slug", required=True)
    p.add_argument("--nombre")
    p.add_argument("--sector")
    p.add_argument("--publico")
    p.add_argument("--idea")
    p.add_argument("--referencias")
    p.add_argument("--campo", action="append", default=[], metavar="CLAVE=VALOR",
                   help="otro campo del encargo (se puede repetir)")
    p = sub.add_parser("encargo", help="escribe y enseña el encargo completo que recibe el motor")
    p.add_argument("slug")
    p = sub.add_parser("puertas", help="pasa las puertas a lo que hay en salida/<slug>/")
    p.add_argument("slug")
    p.add_argument("--solo", help="solo estas puertas, separadas por comas")
    p = sub.add_parser("aprobar", help="el visto bueno de una persona")
    p.add_argument("slug")
    p = sub.add_parser("rechazar", help="el no de una persona")
    p.add_argument("slug")
    p.add_argument("--motivo", required=True)
    p = sub.add_parser("instalar", help="copia lo fabricado a una instalación de AIFEC")
    p.add_argument("slug")
    p.add_argument("--en", required=True, metavar="INSTALACION")
    p.add_argument("--forzar", action="store_true", help="sustituye lo que ya haya en el destino")
    sub.add_parser("escaparate", help="rehace escaparate/index.html")
    p = sub.add_parser("banco", help="prepara o rehace el banco de pruebas")
    p.add_argument("--rehacer", action="store_true")
    return parser


# Las órdenes que no necesitan una instalación de AIFEC válida para funcionar.
SIN_PLAN_ESTRICTO = ("anadir", "parar", "reanudar", "aprobar", "rechazar", "escaparate")


def _fallo_plan(error) -> int:
    print("PLAN INVÁLIDO:")
    for linea in error.errores:
        print("  - " + linea)
    return nucleo.CODIGO_USO


def main(argv=None) -> int:
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.orden:
        parser.print_help()
        return nucleo.CODIGO_USO
    try:
        ctx = nucleo.abrir(RAIZ, estricto=args.orden not in SIN_PLAN_ESTRICTO, reloj=_reloj())
    except plan_mod.PlanInvalido as error:
        return _fallo_plan(error)
    try:
        return _ejecutar(ctx, args)
    except cola_mod.ColaInvalida as error:
        print("COLA: %s" % error)
        return nucleo.CODIGO_USO


def _ejecutar(ctx, args) -> int:
    orden = args.orden
    if orden == "estado":
        print("\n".join(nucleo.texto_estado(ctx)))
        return 0
    if orden == "calendario":
        print("\n".join(nucleo.texto_calendario(ctx)))
        return 0
    if orden == "trabajar":
        codigo, linea = nucleo.trabajar(ctx, uno=args.uno, slug=args.slug)
        print(linea)
        return codigo
    if orden == "parar":
        nucleo.parar(ctx)
        print("PARADA: la fábrica acabará el encargo en curso y no empezará otro")
        return 0
    if orden == "reanudar":
        nucleo.reanudar(ctx)
        print("REANUDADA: la fábrica vuelve a trabajar")
        return 0
    if orden == "anadir":
        encargo = {"slug": args.slug}
        for clave in ("nombre", "sector", "publico", "idea", "referencias"):
            if getattr(args, clave):
                encargo[clave] = getattr(args, clave)
        for par in args.campo:
            if "=" not in par:
                print("--campo tiene que ser CLAVE=VALOR (recibí «%s»)" % par)
                return nucleo.CODIGO_USO
            clave, valor = par.split("=", 1)
            encargo[clave.strip()] = valor
        ctx.cola.anadir(encargo)
        print("AÑADIDO: %s" % args.slug)
        return 0
    if orden == "encargo":
        ctx.cola.obtener(args.slug)
        ruta, texto = nucleo.escribir_encargo(ctx, args.slug)
        print(texto)
        print("ENCARGO: escrito en %s" % ruta.relative_to(ctx.raiz).as_posix())
        return 0
    if orden == "puertas":
        ctx.cola.obtener(args.slug)
        if not ctx.rutas.salida_de(args.slug).is_dir():
            print("PUERTAS: no hay nada en salida/%s/" % args.slug)
            return nucleo.CODIGO_ALGO_NO_PASA
        solo = [n.strip() for n in args.solo.split(",")] if args.solo else None
        informe = puertas.lanzar(ctx, args.slug, solo)
        for entrada in informe["puertas"]:
            print("  [%s] %s — %s" % (entrada["estado"], entrada["nombre"], entrada["resumen"]))
        print(informe["linea"])
        return nucleo.CODIGO_BIEN if informe["pasa"] else nucleo.CODIGO_ALGO_NO_PASA
    if orden == "aprobar":
        try:
            nucleo.aprobar(ctx, args.slug)
        except cola_mod.TransicionInvalida as error:
            print("NO SE PUEDE APROBAR: %s" % error)
            return nucleo.CODIGO_ALGO_NO_PASA
        print("APROBADO: %s" % args.slug)
        return 0
    if orden == "rechazar":
        try:
            final = nucleo.rechazar_a_mano(ctx, args.slug, args.motivo)
        except cola_mod.TransicionInvalida as error:
            print("NO SE PUEDE RECHAZAR: %s" % error)
            return nucleo.CODIGO_ALGO_NO_PASA
        print("RECHAZADO: %s queda «%s»" % (args.slug, final))
        return 0
    if orden == "instalar":
        try:
            destino = nucleo.instalar(ctx, args.slug, args.en, args.forzar)
        except ValueError as error:
            print("NO SE INSTALA: %s" % error)
            return nucleo.CODIGO_ALGO_NO_PASA
        print("INSTALADO: %s" % destino)
        return 0
    if orden == "escaparate":
        cuentas = escaparate.escribir_indice(ctx)
        print("ESCAPARATE: %d pasan las puertas, %d aprobados (escaparate/index.html)" % (
            cuentas["pasan"], cuentas["aprobados"]))
        return 0
    if orden == "banco":
        try:
            resultado = banco.preparar(ctx, rehacer=args.rehacer)
        except (OSError, RuntimeError) as error:
            print("BANCO: no se pudo preparar: %s" % error)
            return nucleo.CODIGO_ALGO_NO_PASA
        for mensaje in resultado["mensajes"]:
            print("  " + mensaje)
        print("BANCO: %s" % ("rehecho" if resultado["rehecho"] else "ya estaba al día"))
        return 0
    return nucleo.CODIGO_USO


if __name__ == "__main__":
    sys.exit(main())
