"""AIFEC — fábrica de temas: apoyos comunes de las puertas.

Leer los argumentos del contrato (`--slug --candidato --banco --plan --informe`), escribir el informe y salir
con 0, 1 o 2, localizar PHP, preparar el banco (instalar el candidato, cargar la demostración) y conseguir las
páginas pintadas de un tema: o las pinta `_pintar.php` dentro del banco, o se leen de una carpeta ya pintada
(`--paginas`, para pruebas y para usar una puerta suelta sin banco).

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

# En Windows la consola habla en la página de códigos de la máquina: el informe saldría con «?» donde van las tildes.
for _salida in (sys.stdout, sys.stderr):
    try:
        _salida.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

CARPETA = Path(__file__).resolve().parent
RAIZ = CARPETA.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from motor import estado as estado_mod, procesos  # noqa: E402

PASA = "pasa"
NO_PASA = "no_pasa"
NO_APLICA = "no_aplica"
CODIGOS = {PASA: 0, NO_PASA: 1, NO_APLICA: 2}

IGNORAR = ("__pycache__", ".git", "node_modules")


class NoAplica(Exception):
    """Falta algo opcional (PHP, el banco, una orden de AIFEC): la puerta sale con 2 y lo dice."""


class NoPasa(Exception):
    """Lo fabricado impide seguir (por ejemplo, una página que revienta): la puerta sale con 1 y lo dice."""


# ------------------------------------------------------------------ contexto e informe


class Contexto:
    """Lo que recibe una puerta y cómo termina."""

    def __init__(self, nombre: str, args):
        self.nombre = nombre
        self.slug = args.slug
        self.candidato = Path(args.candidato)
        self.banco = Path(args.banco)
        self.plan_ruta = Path(args.plan)
        self.informe_ruta = Path(args.informe)
        self.paginas_dir = Path(args.paginas) if getattr(args, "paginas", None) else None
        self.plan = leer_json(self.plan_ruta, {})
        if not isinstance(self.plan, dict):
            self.plan = {}
        self.args = args

    # donde viven las cosas de la fábrica, contando desde el banco (`<fábrica>/estado/banco`)
    @property
    def estado(self) -> Path:
        return self.banco.parent

    @property
    def fabrica(self) -> Path:
        return self.estado.parent

    @property
    def sesiones(self) -> Path:
        return self.estado / "sesiones"

    def opcion(self, clave: str, defecto=None):
        valor = self.plan.get(clave, defecto)
        return defecto if valor is None else valor

    def terminar(self, veredicto: str, resumen: str, detalles=None, medidas=None) -> int:
        """Escribe el informe, enseña el resumen y devuelve el código de salida."""
        informe = {"puerta": self.nombre, "ok": veredicto != NO_PASA, "resumen": resumen,
                   "detalles": [str(d) for d in (detalles or [])], "medidas": medidas or {}}
        self.informe_ruta.parent.mkdir(parents=True, exist_ok=True)
        estado_mod.escribir(self.informe_ruta, informe)
        etiqueta = {PASA: "PASA", NO_PASA: "NO PASA", NO_APLICA: "NO APLICA"}[veredicto]
        print("%s %s: %s" % (self.nombre, etiqueta, resumen))
        for detalle in informe["detalles"][:40]:
            print("  - " + detalle)
        return CODIGOS[veredicto]


def leer_json(ruta, defecto=None):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def contexto(nombre: str, argv=None, extra=None) -> Contexto:
    """Lee la línea de órdenes de una puerta. `extra(parser)` añade argumentos propios."""
    analizador = argparse.ArgumentParser(prog=nombre, description="Puerta «%s» de la fábrica de temas de AIFEC" % nombre)
    analizador.add_argument("--slug", required=True)
    analizador.add_argument("--candidato", required=True)
    analizador.add_argument("--banco", required=True)
    analizador.add_argument("--plan", required=True)
    analizador.add_argument("--informe", required=True)
    analizador.add_argument("--paginas", default=None,
                            help="carpeta con páginas ya pintadas (<tema>/<página>.html): no se pinta nada")
    if extra:
        extra(analizador)
    return Contexto(nombre, analizador.parse_args(argv))


def ejecutar(nombre: str, funcion, argv=None, extra=None) -> int:
    """Ciclo común: lee argumentos, llama a `funcion(ctx)` (que devuelve el código de `ctx.terminar`) y
    convierte `NoAplica`, `NoPasa` y cualquier excepción inesperada en un informe con su código."""
    ctx = contexto(nombre, argv, extra)
    try:
        return funcion(ctx)
    except NoAplica as error:
        return ctx.terminar(NO_APLICA, str(error))
    except NoPasa as error:
        return ctx.terminar(NO_PASA, str(error))
    except Exception as error:  # una puerta que revienta tiene que decirlo en su informe, no solo en el registro
        return ctx.terminar(NO_PASA, "la puerta falló por dentro: %s: %s" % (type(error).__name__, error))


# ------------------------------------------------------------------ ficheros del tema


def firma_arbol(carpeta) -> str:
    """Una huella del contenido de una carpeta: cambia si cambia un nombre, un fichero o un byte."""
    carpeta = Path(carpeta)
    resumen = hashlib.sha1()
    if not carpeta.is_dir():
        return ""
    for ruta in sorted(carpeta.rglob("*")):
        relativa = ruta.relative_to(carpeta).as_posix()
        if any(parte in IGNORAR for parte in ruta.relative_to(carpeta).parts) or not ruta.is_file():
            continue
        resumen.update(relativa.encode("utf-8"))
        try:
            resumen.update(ruta.read_bytes())
        except OSError:
            resumen.update(b"?")
    return resumen.hexdigest()


def ficheros(carpeta, extensiones=None):
    """Ficheros de una carpeta (rutas relativas con `/`), sin carpetas de trabajo."""
    carpeta = Path(carpeta)
    if not carpeta.is_dir():
        return []
    salida = []
    for ruta in sorted(carpeta.rglob("*")):
        partes = ruta.relative_to(carpeta).parts
        if not ruta.is_file() or any(p in IGNORAR for p in partes):
            continue
        if extensiones is None or ruta.suffix.lower() in extensiones:
            salida.append(ruta.relative_to(carpeta).as_posix())
    return salida


def leer_texto(ruta) -> str:
    try:
        return Path(ruta).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def manifiesto(carpeta) -> dict:
    datos = leer_json(Path(carpeta) / "theme.json", {})
    return datos if isinstance(datos, dict) else {}


def carpeta_de_tema(ctx: Contexto, slug: str) -> Path:
    """Dónde está un tema: el candidato, o su carpeta dentro del banco."""
    return ctx.candidato if slug == ctx.slug else ctx.banco / "themes" / slug


def cadena_de_herencia(ctx: Contexto) -> list:
    """Los temas del candidato hacia arriba: [candidato, padre, abuelo…] (solo los que se encuentran)."""
    cadena = []
    slug = ctx.slug
    vistos = set()
    while slug and slug not in vistos:
        vistos.add(slug)
        carpeta = carpeta_de_tema(ctx, slug)
        if not (carpeta / "theme.json").is_file():
            break
        cadena.append((slug, carpeta))
        padre = manifiesto(carpeta).get("parent")
        slug = padre if isinstance(padre, str) else ""
    return cadena


def padre_del_candidato(ctx: Contexto):
    padre = manifiesto(ctx.candidato).get("parent")
    return padre if isinstance(padre, str) and padre else None


def hoja_efectiva(ctx: Contexto, activo: str = "css") -> str:
    """El CSS (o el JS con `activo="js"`) que carga el tema tal como lo hace `theme_styles()`: del tema base al
    candidato, y un tema con `"css": "replace"` empieza de cero."""
    fichero = "assets/css/theme.css" if activo == "css" else "assets/js/theme.js"
    texto = []
    for slug, carpeta in reversed(cadena_de_herencia(ctx)):
        if manifiesto(carpeta).get(activo) == "replace":
            texto = []
        propio = carpeta / fichero
        if propio.is_file():
            texto.append(leer_texto(propio))
    return "\n".join(texto)


# ------------------------------------------------------------------ PHP y el banco


def ejecutable(texto):
    """La ruta de un programa si existe (ruta o nombre en el PATH); si no, None."""
    if not isinstance(texto, str) or not texto.strip():
        return None
    if Path(texto).is_file():
        return str(Path(texto))
    return shutil.which(texto)


def php_principal(ctx: Contexto) -> str:
    php = ejecutable(ctx.opcion("php", "php"))
    if php is None:
        raise NoAplica("no encuentro PHP (plan.json → «php»: %s)" % ctx.opcion("php", "php"))
    return php


def banco_listo(ctx: Contexto) -> bool:
    return (ctx.banco / "aifec").is_file() and (ctx.banco / "core" / "bootstrap.php").is_file()


def exigir_banco(ctx: Contexto) -> None:
    if not banco_listo(ctx):
        raise NoAplica("el banco de pruebas no está preparado (ejecuta `python fabrica.py banco`)")


def sincronizar(origen: Path, destino: Path) -> bool:
    """Deja `destino` igual que `origen`. Devuelve True si hubo que copiar."""
    if firma_arbol(origen) == firma_arbol(destino) and destino.is_dir():
        return False
    if destino.exists():
        shutil.rmtree(str(destino), ignore_errors=True)
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(origen), str(destino), ignore=shutil.ignore_patterns(*IGNORAR))
    return True


def instalar_candidato(ctx: Contexto) -> None:
    """El candidato, en `themes/` del banco (si ya está igual, no se toca)."""
    exigir_banco(ctx)
    sincronizar(ctx.candidato, ctx.banco / "themes" / ctx.slug)


def orden_aifec(ctx: Contexto, args: list, minutos: float = 5, nombre: str = "orden"):
    """Lanza `php aifec <args>` en el banco con los datos forzados a `banco/sites`. Devuelve (código, texto)."""
    exigir_banco(ctx)
    registro = ctx.sesiones / ("%s.%s.%s.log" % (ctx.slug, ctx.nombre, nombre))
    if registro.exists():
        registro.unlink()
    orden = [php_principal(ctx), "aifec"] + [str(a) for a in args] + ["--data=" + str(ctx.banco / "sites")]
    codigo = procesos.lanzar(orden, ctx.banco, registro, minutos)
    return codigo, leer_texto(registro)


def lanzar_php(ctx: Contexto, guion: str, args: list, minutos: float, nombre: str):
    """Lanza un guion de PHP de `puertas/` (`_pintar.php`, `_sembrar.php`). Devuelve (código, texto de la salida)."""
    registro = ctx.sesiones / ("%s.%s.%s.log" % (ctx.slug, ctx.nombre, nombre))
    if registro.exists():
        registro.unlink()
    orden = [php_principal(ctx), str(CARPETA / guion)] + [str(a) for a in args]
    codigo = procesos.lanzar(orden, ctx.banco, registro, minutos)
    return codigo, leer_texto(registro)


def asegurar_demo(ctx: Contexto) -> str:
    """Carga la demostración mínima en el sitio del banco (una sola vez por banco). Devuelve una nota."""
    codigo, texto = lanzar_php(ctx, "_sembrar.php", ["--banco", ctx.banco], 5, "demo")
    ultima = (texto.strip().splitlines() or [""])[-1][:160]
    if codigo == 0:
        return ""
    return "no se pudo cargar la demostración (código %s: %s)" % (codigo, ultima)


# ------------------------------------------------------------------ páginas pintadas


class Paginas:
    """Las páginas de un tema: `html` (nombre -> texto), si son de la página de muestra y los fallos."""

    def __init__(self, slug: str):
        self.slug = slug
        self.html = {}
        self.muestra = False
        self.fallos = []
        self.notas = []

    def __bool__(self) -> bool:
        return bool(self.html)


def _leer_carpeta(carpeta: Path, paginas: Paginas) -> None:
    for fichero in sorted(carpeta.glob("*.html")):
        paginas.html[fichero.stem] = leer_texto(fichero)
    resultado = leer_json(carpeta / "_resultado.json", {})
    if isinstance(resultado, dict):
        paginas.muestra = bool(resultado.get("muestra")) or ("muestra" in paginas.html and "portada" not in paginas.html)
        for nombre, datos in (resultado.get("paginas") or {}).items():
            if isinstance(datos, dict) and int(datos.get("status", 200)) >= 400:
                paginas.fallos.append("%s: respuesta %s%s" % (nombre, datos.get("status"),
                                                              (" (" + datos["nota"] + ")") if datos.get("nota") else ""))
    if "portada" not in paginas.html and "muestra" in paginas.html:
        paginas.muestra = True
        paginas.html["portada"] = paginas.html["muestra"]
        if "muestra-filtros" in paginas.html and "listado" not in paginas.html:
            paginas.html["listado"] = paginas.html["muestra-filtros"]


def paginas_de(ctx: Contexto, slug: str, tema: Path = None) -> Paginas:
    """Las páginas pintadas de un tema.

    Con `--paginas <carpeta>` se leen de `<carpeta>/<slug>/`. Si no, se pintan dentro del banco con
    `_pintar.php` (y se guardan en `estado/paginas/<slug>/`, con la huella del tema para no repetir el trabajo).
    """
    paginas = Paginas(slug)
    if ctx.paginas_dir is not None:
        carpeta = ctx.paginas_dir / slug
        if carpeta.is_dir():
            _leer_carpeta(carpeta, paginas)
        return paginas

    exigir_banco(ctx)
    php_principal(ctx)
    if tema is not None:
        origen = tema
    elif slug == ctx.slug:
        origen = ctx.candidato
    else:
        origen = origen_de_tema(ctx, slug)
    sincronizar(origen, ctx.banco / "themes" / slug)
    nota_demo = asegurar_demo(ctx)
    huella = firma_arbol(ctx.banco / "themes" / slug) + ("|" + nota_demo if nota_demo else "")
    guardadas = ctx.estado / "paginas" / slug
    if (guardadas / "_huella.txt").is_file() and leer_texto(guardadas / "_huella.txt") == huella \
            and (guardadas / "_resultado.json").is_file():
        _leer_carpeta(guardadas, paginas)
        return paginas
    if guardadas.exists():
        shutil.rmtree(str(guardadas), ignore_errors=True)
    guardadas.mkdir(parents=True, exist_ok=True)
    comun = ["--banco", ctx.banco, "--tema", slug, "--salida", guardadas]
    codigo, texto = lanzar_php(ctx, "_pintar.php", comun, 5, "pintar-" + slug)
    if codigo == 2:
        raise NoAplica("no se pueden pintar páginas con el banco: %s" % (texto.strip().splitlines() or ["sin mensaje"])[-1][:160])
    if codigo != 0 or not (guardadas / "_resultado.json").is_file():
        raise NoPasa("no se pudo pintar el tema «%s» (código %s): %s" % (slug, codigo, (texto.strip().splitlines() or ["sin mensaje"])[-1][:200]))
    resultado = leer_json(guardadas / "_resultado.json", {})
    if isinstance(resultado, dict) and resultado.get("necesita_muestra"):
        paginas.notas.append("el banco no tiene productos: se usó la página de muestra del tema base")
        codigo, texto = lanzar_php(ctx, "_pintar.php", comun + ["--muestra"], 5, "muestra-" + slug)
        if codigo != 0:
            paginas.notas.append("tampoco se pudo pintar la página de muestra (código %s)" % codigo)
    if nota_demo:
        paginas.notas.append(nota_demo)
    estado_mod.escribir_texto(guardadas / "_huella.txt", huella)
    _leer_carpeta(guardadas, paginas)
    return paginas


def temas_ajenos(ctx: Contexto) -> list:
    """Los demás temas con los que comparar: los del banco y los ya fabricados en `salida/` (el candidato no)."""
    if ctx.paginas_dir is not None:
        if not ctx.paginas_dir.is_dir():
            return []
        return sorted(p.name for p in ctx.paginas_dir.iterdir() if p.is_dir() and p.name != ctx.slug)
    nombres = set()
    for carpeta in (ctx.banco / "themes", ctx.fabrica / "salida"):
        if carpeta.is_dir():
            nombres.update(p.name for p in carpeta.iterdir() if (p / "theme.json").is_file())
    nombres.discard(ctx.slug)
    return sorted(nombres)


def origen_de_tema(ctx: Contexto, slug: str) -> Path:
    """Dónde leer un tema ajeno: su carpeta en `salida/` si está allí (es lo último fabricado) o la del banco."""
    en_salida = ctx.fabrica / "salida" / slug
    if (en_salida / "theme.json").is_file():
        return en_salida
    return ctx.banco / "themes" / slug


def kb(bytes_: int) -> str:
    return ("%.1f" % (bytes_ / 1000.0)).replace(".", ",") + " KB"
