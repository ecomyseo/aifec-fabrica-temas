"""AIFEC — motor de fábrica: las puertas.

Cada puerta es un programa de `puertas/` que comprueba una cosa de lo fabricado y deja un informe.
Aquí se lanzan en el orden del plan, se juntan sus informes y se decide: pasa si ninguna da 1.
Una puerta que no existe, que revienta o que no deja informe NO pasa (no es «no aplica»).

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import sys

from . import banco, estado, procesos


def _linea(pasan: int, total: int, no_aplican: int, no_pasan: int) -> str:
    texto = "PUERTAS: %d de %d pasan" % (pasan, total)
    if no_aplican:
        texto += ", %d no aplican" % no_aplican
    if no_pasan:
        texto += ", %d no pasan" % no_pasan
    return texto


def _cola_del_registro(ruta, lineas: int = 5) -> list:
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return [l[:300] for l in texto.strip().splitlines()[-lineas:]]


def _una(ctx, slug: str, nombre: str, candidato, plan_json) -> dict:
    """Lanza una puerta y la convierte en una entrada del informe conjunto."""
    entrada = {"nombre": nombre, "estado": "no_pasa", "resumen": "", "detalles": [], "medidas": {}, "codigo": None}
    script = ctx.rutas.puertas / (nombre + ".py")
    if not script.is_file():
        entrada["resumen"] = "la puerta no existe (falta puertas/%s.py)" % nombre
        return entrada
    informe = ctx.rutas.sesiones / ("%s.%s.informe.json" % (slug, nombre))
    registro = ctx.rutas.sesiones / ("%s.%s.log" % (slug, nombre))
    for ruta in (informe, registro):
        if ruta.exists():
            ruta.unlink()
    orden = [sys.executable, str(script), "--slug", slug, "--candidato", str(candidato),
             "--banco", str(ctx.rutas.banco), "--plan", str(plan_json), "--informe", str(informe)]
    codigo = procesos.lanzar(orden, ctx.raiz, registro, ctx.plan["puertas_minutos"])
    entrada["codigo"] = codigo if isinstance(codigo, int) else None
    datos = estado.leer(informe, None)
    if isinstance(datos, dict):
        entrada["resumen"] = str(datos.get("resumen", ""))
        entrada["detalles"] = [str(d) for d in datos.get("detalles", [])] if isinstance(
            datos.get("detalles"), list) else []
        entrada["medidas"] = datos.get("medidas") if isinstance(datos.get("medidas"), dict) else {}
    if codigo == procesos.TIEMPO_AGOTADO:
        entrada["resumen"] = "la puerta se pasó del tiempo (%s min) y se cortó" % ctx.plan["puertas_minutos"]
        return entrada
    if codigo == 0:
        if not isinstance(datos, dict):
            entrada["resumen"] = "la puerta salió con 0 pero no dejó informe"
        elif datos.get("ok") is False:
            entrada["resumen"] = entrada["resumen"] or "el informe dice que no pasa"
        else:
            entrada["estado"] = "pasa"
            entrada["resumen"] = entrada["resumen"] or "pasa"
        return entrada
    if codigo == 1:
        entrada["resumen"] = entrada["resumen"] or "no pasa"
        return entrada
    if codigo == 2:
        entrada["estado"] = "no_aplica"
        entrada["resumen"] = entrada["resumen"] or "no aplica"
        return entrada
    entrada["resumen"] = "la puerta reventó (código %s)" % codigo
    entrada["detalles"] = entrada["detalles"] or _cola_del_registro(registro)
    return entrada


def decidir(entradas: list) -> dict:
    pasan = sum(1 for e in entradas if e["estado"] == "pasa")
    no_aplican = sum(1 for e in entradas if e["estado"] == "no_aplica")
    no_pasan = sum(1 for e in entradas if e["estado"] == "no_pasa")
    return {"pasa": no_pasan == 0, "pasan": pasan, "no_aplican": no_aplican, "no_pasan": no_pasan,
            "total": len(entradas), "linea": _linea(pasan, len(entradas), no_aplican, no_pasan)}


def lanzar(ctx, slug: str, solo: list = None) -> dict:
    """Pasa las puertas a `salida/<slug>/`, guarda `estado/encargos/<slug>.puertas.json` y devuelve
    el informe conjunto. `solo` limita a algunas por nombre."""
    candidato = ctx.rutas.salida_de(slug)
    nombres = list(ctx.plan["puertas"])
    if solo:
        nombres = [n for n in solo if n]
    avisos = []
    if candidato.is_dir():
        try:
            banco.preparar(ctx)
            banco.instalar(ctx, slug)
        except (OSError, RuntimeError) as error:
            avisos.append("el banco no está listo: %s" % error)
            ctx.apuntar("puertas: " + avisos[-1])
    entradas = [_una(ctx, slug, nombre, candidato, ctx.rutas.plan) for nombre in nombres]
    informe = decidir(entradas)
    informe.update({"slug": slug, "fecha": ctx.ahora().isoformat(timespec="seconds"),
                    "puertas": entradas, "avisos": avisos})
    estado.escribir(ctx.rutas.puertas_json(slug), informe)
    return informe
