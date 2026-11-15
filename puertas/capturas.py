"""AIFEC — fábrica de temas: puerta «capturas» (lo que solo se ve en un navegador). OPCIONAL.

Con `capturas.activas` en el plan y Playwright instalado: arranca el servidor de PHP del banco en un puerto
libre como hijo suyo (salida a un fichero, sin ventana), pone el tema candidato en el sitio del banco, lanza UN
navegador sin ventana (con `--disable-gpu`), captura portada, listado, ficha y carrito a 1440 y a 390 px en
`escaparate/<slug>/` y exige cero errores de JavaScript, cero respuestas 5xx y cero desbordamiento horizontal
(medido contra 390 px, no contra `innerWidth`: en móvil el navegador agranda la ventana hasta el contenido).
Al acabar, también si falla, para el servidor y el navegador y comprueba que el puerto ha quedado libre.

Sin Playwright, o con `activas` a falso o sin banco, sale con 2 («no aplica»). Playwright no es dependencia de
la fábrica: es lo único que se importa dentro de esta puerta, y solo si hay que usarlo.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

ANCHOS = (("escritorio", 1440, 900), ("movil", 390, 844))
PAGINAS = ("portada", "listado", "ficha", "carrito")
MARGEN_DESBORDE = 1


def playwright_disponible() -> bool:
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as zocalo:
        zocalo.bind(("127.0.0.1", 0))
        return zocalo.getsockname()[1]


def puerto_abierto(puerto: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.5):
            return True
    except OSError:
        return False


def arrancar_servidor(ctx, puerto: int):
    """`php -S` del banco como hijo nuestro. Devuelve (proceso, fichero de registro abierto)."""
    php = _comun.php_principal(ctx)
    registro = ctx.sesiones / ("%s.capturas.servidor.log" % ctx.slug)
    registro.parent.mkdir(parents=True, exist_ok=True)
    salida = open(registro, "wb")
    opciones = {"cwd": str(ctx.banco / "public"), "stdin": subprocess.DEVNULL, "stdout": salida, "stderr": subprocess.STDOUT}
    if os.name == "nt":
        opciones["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        opciones["start_new_session"] = True
    proceso = subprocess.Popen([php, "-S", "127.0.0.1:%d" % puerto, "-t", str(ctx.banco / "public"), str(ctx.banco / "public" / "index.php")], **opciones)
    limite = time.time() + 20
    while time.time() < limite:
        if proceso.poll() is not None:
            break
        if puerto_abierto(puerto):
            return proceso, salida
        time.sleep(0.2)
    return proceso, salida


def parar_servidor(proceso, salida, puerto: int) -> bool:
    """Para el servidor y comprueba que el puerto queda libre."""
    if proceso is not None and proceso.poll() is None:
        _comun.procesos.matar_arbol(proceso.pid)
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    if salida is not None:
        salida.close()
    limite = time.time() + 5
    while time.time() < limite:
        if not puerto_abierto(puerto):
            return True
        time.sleep(0.2)
    return not puerto_abierto(puerto)


def direcciones_de_paginas(ctx) -> dict:
    """Las direcciones de las cuatro páginas, sacadas de lo que pintó `_pintar.php` (si ya lo hizo)."""
    resultado = _comun.leer_json(ctx.estado / "paginas" / ctx.slug / "_resultado.json", {})
    paginas = resultado.get("paginas") if isinstance(resultado, dict) else None
    direcciones = {nombre: "/" for nombre in ("portada",)}
    for nombre in PAGINAS:
        datos = (paginas or {}).get(nombre)
        if isinstance(datos, dict) and datos.get("url"):
            direcciones[nombre] = datos["url"]
    direcciones.setdefault("carrito", "/carrito")
    return direcciones


def capturar(ctx, puerto: int, direcciones: dict, destino: Path) -> tuple:
    """Pasa por Playwright las páginas. Devuelve (problemas, detalles)."""
    from playwright.sync_api import sync_playwright  # solo aquí, y solo si hay que capturar

    problemas = []
    detalles = []
    destino.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True, args=["--disable-gpu"])
        try:
            for variante, ancho, alto in ANCHOS:
                contexto = navegador.new_context(viewport={"width": ancho, "height": alto}, is_mobile=(variante == "movil"),
                                                 device_scale_factor=1)
                try:
                    for nombre, ruta in direcciones.items():
                        pagina = contexto.new_page()
                        errores_js = []
                        malas = []
                        pagina.on("pageerror", lambda e, lista=errores_js: lista.append(str(e)[:160]))
                        pagina.on("response", lambda r, lista=malas: lista.append("%s %s" % (r.status, r.url[-80:])) if r.status >= 500 else None)
                        try:
                            pagina.goto("http://127.0.0.1:%d%s" % (puerto, ruta), wait_until="load", timeout=30000)
                            pagina.wait_for_timeout(300)
                            desborde = pagina.evaluate("Math.max(document.documentElement.scrollWidth, window.innerWidth) - %d" % ancho)
                            pagina.screenshot(path=str(destino / ("%s-%s.png" % (nombre, variante))), full_page=True)
                        except Exception as error:  # el navegador no pudo abrir la página
                            problemas.append("%s (%s): no se pudo abrir: %s" % (nombre, variante, str(error)[:120]))
                            continue
                        finally:
                            pagina.close()
                        if errores_js:
                            problemas.append("%s (%s): %d error(es) de JavaScript: %s" % (nombre, variante, len(errores_js), errores_js[0]))
                        if malas:
                            problemas.append("%s (%s): respuesta 5xx: %s" % (nombre, variante, malas[0]))
                        if desborde > MARGEN_DESBORDE:
                            problemas.append("%s (%s): desborde horizontal de %d px" % (nombre, variante, desborde))
                        detalles.append("%s (%s): capturada" % (nombre, variante))
                finally:
                    contexto.close()
        finally:
            navegador.close()
    return problemas, detalles


def puerta(ctx) -> int:
    activas = ctx.opcion("capturas", {})
    if not isinstance(activas, dict) or not activas.get("activas"):
        raise _comun.NoAplica("las capturas están apagadas (plan.json, capturas.activas)")
    if not playwright_disponible():
        raise _comun.NoAplica("Playwright no está instalado: la puerta de capturas es opcional y no se imita")
    _comun.exigir_banco(ctx)
    _comun.php_principal(ctx)
    # Pintar antes deja a mano las direcciones reales (listado y ficha del banco) y deja el tema instalado.
    _comun.paginas_de(ctx, ctx.slug)
    direcciones = direcciones_de_paginas(ctx)

    anterior = ""
    codigo, texto = _comun.orden_aifec(ctx, ["setting:get", "theme.active"], minutos=2, nombre="activo-antes")
    for linea in texto.splitlines():
        if "theme.active" in linea and "=" in linea:
            anterior = linea.split("=", 1)[1].strip().strip('"')
    puerto = puerto_libre()
    proceso = salida = None
    problemas = []
    detalles = []
    liberado = True
    try:
        codigo, texto = _comun.orden_aifec(ctx, ["setting:set", "theme.active", ctx.slug, "--text"], minutos=2, nombre="activar")
        if codigo != 0:
            raise _comun.NoAplica("no se pudo activar el tema en el banco (código %s)" % codigo)
        proceso, salida = arrancar_servidor(ctx, puerto)
        if not puerto_abierto(puerto):
            raise _comun.NoPasa("el servidor del banco no abrió el puerto %d" % puerto)
        destino = ctx.fabrica / "escaparate" / ctx.slug
        problemas, detalles = capturar(ctx, puerto, direcciones, destino)
        detalles.append("capturas en %s" % destino)
    finally:
        liberado = parar_servidor(proceso, salida, puerto)
        if anterior:
            try:
                _comun.orden_aifec(ctx, ["setting:set", "theme.active", anterior, "--text"], minutos=2, nombre="activar-antes")
            except _comun.NoAplica:
                pass
    medidas = {"paginas": len(direcciones), "variantes": len(ANCHOS), "puerto": puerto, "servidor_pid": proceso.pid if proceso is not None else None, "servidor_vivo": proceso is not None and proceso.poll() is None, "puerto_libre": liberado, "problemas": len(problemas)}
    if not liberado:
        problemas.append("el puerto %d sigue abierto: el servidor no se paró" % puerto)
    if problemas:
        return ctx.terminar(_comun.NO_PASA, problemas[0], problemas + detalles, medidas)
    return ctx.terminar(_comun.PASA, "%d páginas capturadas a 1440 y a 390 px sin errores de JavaScript, sin 5xx y sin desborde" % len(direcciones), detalles, medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("capturas", puerta))
