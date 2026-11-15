"""AIFEC — motor de fábrica: el banco de pruebas.

Una copia de trabajo de la instalación de AIFEC dentro de `estado/banco/` (sin sus datos, cachés ni
`.git`), con un sitio propio creado con las órdenes del propio AIFEC. Las puertas validan ahí lo
fabricado; la instalación de origen solo se lee.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

from . import estado, motores, procesos

# Nombres (de carpeta o de fichero) que no se copian al banco. `data-path.php` apunta a los datos
# reales de quien desarrolla: copiarlo haría que el banco escribiera en ellos.
IGNORAR_RAIZ = ("sites", "storage", "cache", ".cache", "data-path.php")
IGNORAR_SIEMPRE = (".git", "node_modules", "__pycache__")

FICHEROS_VERSION = ("VERSION", "version.txt", "core/VERSION")


def firma_aifec(aifec) -> dict:
    """Lo que cambia cuando cambia la versión de AIFEC: su fichero de versión y la fecha de `core/`."""
    aifec = Path(aifec)
    version = ""
    for nombre in FICHEROS_VERSION:
        ruta = aifec / nombre
        if ruta.is_file():
            version = ruta.read_text(encoding="utf-8", errors="replace").strip()
            break
    mas_reciente = 0
    ficheros = 0
    for carpeta, subcarpetas, nombres in os.walk(str(aifec / "core")):
        subcarpetas[:] = [s for s in subcarpetas if s not in IGNORAR_SIEMPRE]
        for nombre in nombres:
            try:
                mas_reciente = max(mas_reciente, (Path(carpeta) / nombre).stat().st_mtime_ns)
                ficheros += 1
            except OSError:
                continue
    return {"version": version, "core_mtime_ns": mas_reciente, "core_ficheros": ficheros}


def _ignorar(raiz_origen: str):
    """Qué no se copia: en la raíz, los datos y cachés; en cualquier sitio, `.git` y compañía."""
    raiz_origen = os.path.normcase(os.path.abspath(raiz_origen))

    def filtro(carpeta, nombres):
        saltar = [n for n in nombres if n in IGNORAR_SIEMPRE]
        if os.path.normcase(os.path.abspath(carpeta)) == raiz_origen:
            saltar += [n for n in nombres if n in IGNORAR_RAIZ]
        return saltar
    return filtro


def _borrar(ruta: Path) -> None:
    def _forzar(funcion, camino, _info):
        try:
            os.chmod(camino, stat.S_IWRITE)
            funcion(camino)
        except OSError:
            pass
    if ruta.exists():
        shutil.rmtree(str(ruta), onerror=_forzar)


def _seguro_borrar_banco(ctx) -> None:
    banco = ctx.rutas.banco.resolve()
    if banco.name != "banco" or ctx.rutas.estado.resolve() not in banco.parents:
        raise RuntimeError("negado: el banco no está donde debe: %s" % banco)
    _borrar(banco)


def orden_php(ctx, args: list, minutos: float = 5, nombre: str = "orden"):
    """Lanza `php aifec <args>` dentro del banco. Devuelve `(código, texto de la salida)`.
    Los datos del sitio se fuerzan a `banco/sites`, nunca a otro sitio."""
    banco = ctx.rutas.banco
    if not (banco / "aifec").is_file():
        raise RuntimeError("el banco no está preparado (ejecuta `python fabrica.py banco`)")
    registro = ctx.rutas.sesiones / ("banco-%s.log" % nombre)
    if registro.exists():
        registro.unlink()
    orden = [ctx.plan["php"], "aifec"] + [str(a) for a in args] + ["--data=" + str(banco / "sites")]
    codigo = procesos.lanzar(orden, banco, registro, minutos)
    try:
        texto = registro.read_text(encoding="utf-8", errors="replace")
    except OSError:
        texto = ""
    return codigo, texto


def _orden_sitio(ctx) -> list:
    configurada = ctx.plan["banco"].get("orden_sitio")
    if configurada:
        return list(configurada)
    orden = ["site:create", ctx.plan["banco"]["sitio"], "--url=http://banco.test",
             "--admin-email=banco@ejemplo.test", "--admin-name=Banco",
             "--admin-password=clave-de-mentira", "--db=sqlite"]
    if (ctx.rutas.banco / "demos" / "minimo").is_dir():
        orden.append("--demo")
    return orden


def preparar(ctx, rehacer: bool = False) -> dict:
    """Deja listo `estado/banco/`. Se rehace si no existe, si pide `rehacer` o si cambió la versión
    de AIFEC. Si AIFEC no trae una orden que hace falta, lo dice y sigue: las puertas que la
    necesiten saldrán con 2."""
    aifec = Path(ctx.plan["aifec"])
    firma = firma_aifec(aifec)
    guardada = estado.leer(ctx.rutas.banco_json, {})
    hecho = (ctx.rutas.banco / "aifec").is_file() and isinstance(guardada, dict) and guardada.get("firma") == firma
    if hecho and not rehacer:
        return {"rehecho": False, "mensajes": ["el banco ya está al día"]}
    mensajes = []
    _seguro_borrar_banco(ctx)
    shutil.copytree(str(aifec), str(ctx.rutas.banco), ignore=_ignorar(str(aifec)))
    mensajes.append("copia de trabajo hecha en estado/banco/")
    codigo, texto = orden_php(ctx, _orden_sitio(ctx), minutos=10, nombre="sitio")
    sitio = codigo == 0
    if sitio:
        mensajes.append("sitio «%s» creado en el banco" % ctx.plan["banco"]["sitio"])
    else:
        ultima = (texto.strip().splitlines() or [""])[-1][:200]
        mensajes.append("AIFEC no creó el sitio del banco (código %s: %s); sigo: las puertas que lo "
                        "necesiten saldrán con 2" % (codigo, ultima))
    estado.escribir(ctx.rutas.banco_json, {"firma": firma, "fecha": ctx.ahora().isoformat(timespec="seconds"),
                                           "sitio": sitio})
    for mensaje in mensajes:
        ctx.apuntar("banco: " + mensaje)
    return {"rehecho": True, "sitio": sitio, "mensajes": mensajes}


def instalar(ctx, slug: str, tipo: str = None) -> Path:
    """Copia el candidato `salida/<slug>/` a la carpeta de su clase dentro del banco."""
    origen = ctx.rutas.salida_de(slug)
    if not origen.is_dir():
        raise RuntimeError("no hay nada en salida/%s/" % slug)
    destino = ctx.rutas.banco / (tipo or ctx.config["carpeta_destino"]) / slug
    _borrar(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(origen), str(destino))
    return destino


def esqueleto(ctx, slug: str, nombre: str):
    """Pide a AIFEC el esqueleto del encargo (la orden sale de `fabrica.json`) y lo copia a
    `salida/<slug>/`. Devuelve `(hecho, mensaje)`; si AIFEC no lo sabe hacer, el motor empieza de cero."""
    orden = motores.sustituir_marcas(ctx.config["orden_esqueleto"], {"slug": slug, "nombre": nombre})
    codigo, texto = orden_php(ctx, orden, minutos=5, nombre="esqueleto")
    creado = ctx.rutas.banco / ctx.config["carpeta_destino"] / slug
    if codigo != 0 or not creado.is_dir():
        ultima = (texto.strip().splitlines() or [""])[-1][:200]
        return False, "AIFEC no creó el esqueleto (código %s: %s)" % (codigo, ultima)
    destino = ctx.rutas.salida_de(slug)
    destino.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(creado), str(destino), dirs_exist_ok=True)
    return True, "esqueleto copiado a salida/%s/" % slug
