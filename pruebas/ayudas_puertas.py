"""AIFEC — fábrica de temas: ayudas de las pruebas de las puertas.

Monta, en una carpeta temporal, temas hechos con el esqueleto, páginas de mentira con las cinco superficies en
varias composiciones (para probar el comparador y la puerta de móvil sin sistema), una hoja de estilos buena, un
«sistema» de mentira cuyo `aifec` es un guion de Python, y —para las pruebas «con sistema»— un banco real hecho
con la fábrica a partir de la instalación que diga `AIFEC_RUTA`. Nada sale a Internet.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from functools import lru_cache
from pathlib import Path

PROYECTO = Path(__file__).resolve().parent.parent
PUERTAS = PROYECTO / "puertas"
if str(PROYECTO / "skill") not in sys.path:
    sys.path.insert(0, str(PROYECTO / "skill"))
if str(PUERTAS) not in sys.path:
    sys.path.insert(0, str(PUERTAS))

import esqueleto as esqueleto_mod  # noqa: E402  (skill/esqueleto.py)

AIFEC_RUTA = os.environ.get("AIFEC_RUTA", "")

HOJA_BUENA = """
:root{--bar-h:3.5rem;--header-h:3.5rem}
.af-header{position:sticky;top:0;z-index:40}
.af-mobile-bar{display:flex;position:fixed;left:0;right:0;bottom:0;padding-bottom:env(safe-area-inset-bottom)}
.af-mobile-bar-item{display:flex;flex:1 1 0;min-width:44px;min-height:var(--bar-h)}
.af-has-bar{padding-bottom:calc(var(--bar-h) + env(safe-area-inset-bottom))}
:focus-visible{outline:2px solid currentColor}
"""

BARRA_BUENA = (
    '<nav class="af-mobile-bar af-show-sm" aria-label="Acciones">'
    '<a class="af-mobile-bar-item" href="/buscar" data-af-drawer-open="af-search"><span class="af-mobile-bar-label">Buscar</span></a>'
    '{filtros}'
    '<a class="af-mobile-bar-item" href="/carrito" data-af-drawer-open="af-cart"><span class="af-cart-count" data-af-cart-count hidden></span>'
    '<span class="af-mobile-bar-label">Carrito</span></a></nav>')
FILTROS_BOTON = ('<button type="button" class="af-mobile-bar-item" data-af-drawer-open="af-filters" aria-controls="af-filters">'
                 '<span class="af-mobile-bar-label">Filtros</span></button>')
PANELES = '<aside class="af-drawer" id="af-search"></aside><aside class="af-drawer" id="af-cart"></aside>'


# ------------------------------------------------------------------ superficies en varias composiciones


def cabecera(variante: int, estilo: str = "a") -> str:
    x = "x%s" % estilo
    if variante == 0:
        return ('<header class="af-header %s-h"><div class="af-container %s-i"><a class="af-logo" href="/">Tienda %s</a>'
                '<nav class="af-nav"><ul class="af-nav-list"><li class="af-nav-item"><a class="af-nav-link" href="/a">Uno %s</a></li>'
                '<li class="af-nav-item"><a class="af-nav-link" href="/b">Dos</a></li><li class="af-nav-item"><a class="af-nav-link" href="/c">Tres</a></li></ul></nav>'
                '<form class="af-search" role="search"><label class="af-sr">Buscar</label><input class="af-input" type="search" name="q">'
                '<button class="af-icon-btn" type="submit"><svg><path d="M0 0"/></svg></button></form>'
                '<div class="af-header-actions"><a class="af-icon-btn" href="/cuenta"><img src="x.png"></a></div></div></header>') % (x, x, estilo, estilo)
    if variante == 1:
        return ('<header class="af-header"><div class="%s-banda"><div class="af-container"><ul><li><a href="/cuenta">Cuenta</a></li>'
                '<li><a href="/ayuda">Ayuda</a></li></ul></div></div><div class="af-container"><section><a class="af-logo" href="/">T</a>'
                '<form class="af-search"><input class="af-input" name="q"><button class="af-btn">Buscar</button></form>'
                '<a class="af-icon-btn" href="/carrito">Cesta</a></section></div><nav class="af-nav"><div class="af-container">'
                '<ul class="af-nav-list"><li class="af-nav-item"><a class="af-nav-link" href="/a">Uno</a></li></ul></div></nav></header>') % x
    return ('<header class="af-header"><aside><p>Aviso</p></aside><div class="af-container"><nav class="af-nav"><ol><li><a href="/a">Uno</a></li>'
            '<li><a href="/b">Dos</a></li></ol></nav><h2><a class="af-logo" href="/">T</a></h2><ul><li><a href="/cuenta">Cuenta</a></li>'
            '<li><a href="/carrito">Cesta</a></li></ul></div></header>')


def tarjeta(variante: int, estilo: str = "a", numero: int = 8) -> str:
    x = "x%s" % estilo
    if variante == 0:
        una = ('<article class="af-product-card %s-t"><a class="af-product-card-link" href="/p/1"><span class="af-product-card-media"><img src="p.png">'
               '<span class="af-badges"><span class="af-badge af-badge-sale">-10 %%</span></span></span><span class="af-product-card-body">'
               '<h3 class="af-product-card-name">Producto %s</h3><span class="af-price af-price-sm"><span class="af-price-now">10 €</span></span></span></a></article>') % (x, estilo)
    else:
        una = ('<article class="af-product-card"><figure><img src="p.png"><ul class="af-badges"><li class="af-badge af-badge-new">Nuevo</li></ul></figure>'
               '<div><p>Marca</p><h3><a href="/p/1">Producto</a></h3><p class="af-stars"></p><span class="af-price"><s class="af-price-old">12 €</s></span></div></article>')
    return una * numero


def listado(variante: int, estilo: str = "a", numero: int = 8, filtros: bool = True) -> str:
    panel = ('<aside class="af-listing-filters af-drawer" id="af-filters"><form class="af-drawer-body"><div class="af-filter"><p class="af-filter-title">Marca</p>'
             '<label class="af-check"><input type="checkbox"><span>Una</span></label></div><button class="af-btn">Aplicar</button></form></aside>') if filtros else ""
    if variante == 0:
        return ('<div class="af-listing">%s<div class="af-listing-results"><div class="af-row"><p class="af-muted">8 productos</p>'
                '<select class="af-select"><option>Nombre</option></select></div><div class="af-grid af-cols-4">%s</div></div></div>') % (panel, tarjeta(0, estilo, numero))
    return ('<section class="af-listing"><div class="af-listing-results"><header><h1 class="af-title">Cat</h1><ul><li><a href="/c1">C1</a></li></ul></header>'
            '<ul class="af-grid af-cols-3"><li>%s</li></ul><nav class="af-pagination"><a href="?p=2">2</a></nav></div>%s</section>') % (tarjeta(1, estilo, numero), panel)


def ficha(variante: int, estilo: str = "a") -> str:
    if variante == 0:
        return ('<div class="af-product"><div class="af-product-gallery"><div class="af-gallery"><div class="af-gallery-main"><img src="g.png"></div></div></div>'
                '<div class="af-product-buy"><h1 class="af-title">Producto %s</h1><p class="af-row"><a href="/m">Marca</a></p><span class="af-price af-price-lg">'
                '<span class="af-price-now">10 €</span></span><p class="af-availability">En stock</p><form data-af-cart-add><input type="hidden" name="product_id" value="1">'
                '<div class="af-row"><div class="af-qty"><button class="af-qty-btn">-</button><input class="af-qty-input"><button class="af-qty-btn">+</button></div>'
                '<button class="af-btn af-btn-primary" data-af-add>Añadir</button></div></form><dl class="af-facts"><div><dt>A</dt><dd>1</dd></div></dl></div></div>') % estilo
    return ('<article class="af-product"><header><h1 class="af-title">P</h1><ul><li>Marca</li></ul></header><div class="af-product-gallery"><figure class="af-gallery-main">'
            '<img src="g.png"></figure><ul class="af-gallery-thumbs"><li><a href="g2.png">2</a></li></ul></div><div class="af-product-buy"><section><span class="af-price">'
            '<span class="af-price-now">10 €</span></span></section><form data-af-cart-add><button class="af-btn" data-af-add>Añadir</button></form>'
            '<ul class="af-facts"><li>A</li></ul></div></article>')


def pie(variante: int, estilo: str = "a") -> str:
    if variante == 0:
        return ('<footer class="af-footer"><div class="af-container"><div class="af-footer-grid"><div class="af-footer-col af-footer-about"><p class="af-footer-title">Tienda %s</p>'
                '<p><a href="mailto:x@ejemplo.test">x</a></p></div></div><div class="af-footer-bottom"><p class="af-small">&copy; 2026</p></div></div></footer>') % estilo
    return ('<footer class="af-footer"><section><div class="af-container"><h2>Tienda</h2><address>Calle Mayor 1</address></div></section>'
            '<div><div class="af-container"><nav><h3>Info</h3><ul><li><a href="/a">A</a></li></ul></nav></div></div><div><small>&copy; 2026</small></div></footer>')


def pagina(cuerpo: str, cab: str, pi: str, barra: str = None, paneles: str = PANELES, filtros_boton: bool = False) -> str:
    barra = BARRA_BUENA.format(filtros=FILTROS_BOTON if filtros_boton else "") if barra is None else barra
    return '<!doctype html><html lang="es"><head><meta charset="utf-8"></head><body class="af-has-bar">%s<main id="main">%s</main>%s%s%s</body></html>' % (
        cab, cuerpo, pi, barra, paneles)


def escribir_paginas(carpeta: Path, tema: str, variante: int, estilo: str = "a", numero: int = 8, **opciones) -> Path:
    """Las cuatro páginas de un tema de mentira en `<carpeta>/<tema>/`. `variante` elige la composición de las cinco
    superficies; `estilo` cambia clases propias y textos; `numero` es el número de tarjetas."""
    destino = Path(carpeta) / tema
    destino.mkdir(parents=True, exist_ok=True)
    cab = opciones.get("cabecera", cabecera(variante, estilo))
    pi = opciones.get("pie", pie(variante, estilo))
    barra = opciones.get("barra")
    conjuntas = {
        "portada": pagina(tarjeta(variante, estilo, 4), cab, pi, barra),
        "listado": pagina(listado(variante, estilo, numero), cab, pi, barra, filtros_boton=opciones.get("filtros_boton", True)),
        "ficha": pagina(ficha(variante, estilo), cab, pi, barra),
        "carrito": pagina('<div class="af-cart"></div>', cab, pi, barra),
    }
    for nombre, html in conjuntas.items():
        (destino / (nombre + ".html")).write_text(html, encoding="utf-8")
    return destino


# ------------------------------------------------------------------ temas y puertas


def _borrar(ruta: Path) -> None:
    for _ in range(10):
        shutil.rmtree(str(ruta), ignore_errors=True)
        if not ruta.exists():
            return
        time.sleep(0.2)


@lru_cache(maxsize=1)
def php_con_sqlite():
    """Un PHP que sirva para el banco real (con `pdo_sqlite`): `AIFEC_PHP`, el del PATH o los de una instalación de
    herramientas conocida. None si no se encuentra ninguno."""
    candidatos = [os.environ.get("AIFEC_PHP", ""), shutil.which("php") or ""]
    for raiz in ("C:/dev-tools/php",):
        carpeta = Path(raiz)
        if carpeta.is_dir():
            candidatos += [str(p / "php.exe") for p in sorted(carpeta.glob("php-8.*"), reverse=True)]
    for candidato in candidatos:
        if not candidato or not Path(candidato).exists():
            continue
        try:
            salida = subprocess.run([candidato, "-m"], stdin=subprocess.DEVNULL, capture_output=True, timeout=30, text=True).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        if "pdo_sqlite" in salida.lower():
            return candidato
    return None


@lru_cache(maxsize=1)
def php_cualquiera():
    return shutil.which("php") or php_con_sqlite()


class BaseTemas(unittest.TestCase):
    """Carpeta temporal por prueba, temas hechos con el esqueleto y una forma de lanzar una puerta."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="puertas-prueba-")).resolve()
        self.addCleanup(_borrar, self.tmp)
        self.banco = self.tmp / "estado" / "banco"
        self.plan = self.tmp / "plan.json"
        self.salida = self.tmp / "salida"

    # ---- temas ------------------------------------------------------------------------------

    def tema(self, slug: str = "tema-uno", nombre: str = "Tema uno", prefijo: str = "") -> Path:
        destino = self.salida / slug
        esqueleto_mod.crear(slug, nombre, destino, prefijo)
        return destino

    def escribir(self, ruta: Path, texto, binario: bool = False) -> Path:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        if binario:
            ruta.write_bytes(texto)
        else:
            ruta.write_bytes(texto.encode("utf-8"))
        return ruta

    def con_hoja_buena(self, tema: Path, extra: str = "") -> Path:
        """Una hoja que cumple el contrato de móvil por sí sola (el esqueleto lo hereda de `base`)."""
        self.escribir(tema / "assets" / "css" / "theme.css", HOJA_BUENA + extra)
        return tema

    # ---- lanzar una puerta ------------------------------------------------------------------

    def escribir_plan(self, **extra) -> Path:
        datos = {"php": php_cualquiera() or "php", "php_versiones": [], "capturas": {"activas": False}, "umbral_estructura": 0.82}
        datos.update(extra)
        self.plan.write_text(json.dumps(datos), encoding="utf-8")
        return self.plan

    def lanzar(self, puerta: str, tema: Path, paginas: Path = None, plan: dict = None, slug: str = None, entorno: dict = None):
        """Lanza `puertas/<puerta>.py`. Devuelve (código, informe, salida de texto)."""
        slug = slug or tema.name
        self.escribir_plan(**(plan or {}))
        informe = self.tmp / ("informe-%s.json" % puerta)
        if informe.exists():
            informe.unlink()
        orden = [sys.executable, str(PUERTAS / (puerta + ".py")), "--slug", slug, "--candidato", str(tema), "--banco", str(self.banco),
                 "--plan", str(self.plan), "--informe", str(informe)]
        if paginas is not None:
            orden += ["--paginas", str(paginas)]
        env = dict(os.environ)
        env.update(entorno or {})
        proceso = subprocess.run(orden, stdin=subprocess.DEVNULL, capture_output=True, timeout=300, env=env, encoding="utf-8", errors="replace")
        datos = {}
        if informe.is_file():
            datos = json.loads(informe.read_text(encoding="utf-8"))
        return proceso.returncode, datos, proceso.stdout + proceso.stderr

    def instantanea(self, carpeta: Path) -> dict:
        return {p.relative_to(carpeta).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in sorted(Path(carpeta).rglob("*")) if p.is_file()}

    def aceptar(self, codigo, informe, texto, esperado=0):
        self.assertEqual(codigo, esperado, "%s\n%s" % (texto, json.dumps(informe, ensure_ascii=False)[:600]))

    def texto_del_informe(self, informe: dict) -> str:
        return informe.get("resumen", "") + "\n" + "\n".join(informe.get("detalles", []))


# ------------------------------------------------------------------ un «sistema» de mentira, para validador y traducciones

AIFEC_MENTIRA = r'''
import os, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
raiz = Path(__file__).resolve().parent
args = [a for a in sys.argv[1:] if not a.startswith("--data=")]
modo = (raiz / "modo.txt").read_text().strip() if (raiz / "modo.txt").exists() else "ok"
orden = args[0] if args else ""
with open(raiz / "llamadas.log", "a", encoding="utf-8") as f:
    f.write(" ".join(args) + "\n")
if modo == "sin_ordenes":
    print("Unknown command: " + orden)
    sys.exit(2)
if orden == "theme:check":
    if modo == "falla":
        print("[ OK ] manifest (theme.json) theme.json es válido")
        print("[FAIL] wrapper-head (templates/layout.php) El envoltorio tiene que llamar a page_head() en el head")
        print("[WARN] escaping (templates/partials/header.php) imprime una variable sin escaparla")
        print("Score 80 · errors 1 · warnings 1")
        sys.exit(1)
    print("[ OK ] manifest (theme.json) theme.json es válido")
    print("[WARN] escaping (templates/partials/header.php) imprime una variable sin escaparla")
    print("Score 96 · errors 0 · warnings 1")
    sys.exit(0)
if orden == "i18n:check":
    if modo == "falla":
        print("    'Sale' => '',   // themes/x/templates/partials/product-card.php")
        print("I18N themes/x [es]: 41 strings, 3 missing")
        sys.exit(1)
    print("I18N themes/x [es]: 41 strings, 0 missing")
    sys.exit(0)
print("orden: " + orden)
sys.exit(0)
'''


def montar_sistema_de_mentira(banco: Path, modo: str = "ok") -> None:
    (banco / "core").mkdir(parents=True, exist_ok=True)
    (banco / "core" / "bootstrap.php").write_text("<?php\n", encoding="utf-8")
    (banco / "themes").mkdir(exist_ok=True)
    (banco / "aifec").write_text(AIFEC_MENTIRA, encoding="utf-8")
    (banco / "modo.txt").write_text(modo, encoding="utf-8")


# ------------------------------------------------------------------ el banco real, para las pruebas «con sistema»


def sistema_disponible() -> bool:
    return bool(AIFEC_RUTA) and (Path(AIFEC_RUTA) / "aifec").is_file() and php_con_sqlite() is not None


class FabricaReal:
    """Una copia de la fábrica en una carpeta temporal con su plan apuntando a la instalación real y su banco ya
    hecho. Se monta una sola vez por módulo de pruebas (`FabricaReal.montar()`) y se borra al acabar."""

    def __init__(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="fabrica-real-")).resolve()
        for nombre in ("motor", "puertas", "plantillas", "skill"):
            shutil.copytree(str(PROYECTO / nombre), str(self.raiz / nombre), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(str(PROYECTO / "fabrica.py"), str(self.raiz / "fabrica.py"))
        shutil.copy2(str(PROYECTO / "fabrica.json"), str(self.raiz / "fabrica.json"))
        self.php = php_con_sqlite()
        self.escribir_plan({})
        self.banco = self.raiz / "estado" / "banco"

    def escribir_plan(self, extra: dict) -> None:
        plan = {"aifec": AIFEC_RUTA, "php": self.php, "php_versiones": [], "puertas_minutos": 10, "capturas": {"activas": False}}
        plan.update(extra)
        (self.raiz / "plan.json").write_text(json.dumps(plan), encoding="utf-8")

    def fabrica(self, *args, entorno=None, tiempo=600):
        env = dict(os.environ)
        env.update(entorno or {})
        proceso = subprocess.run([sys.executable, str(self.raiz / "fabrica.py")] + [str(a) for a in args], cwd=str(self.raiz),
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=tiempo, env=env, encoding="utf-8", errors="replace")
        return proceso.returncode, proceso.stdout + proceso.stderr

    def preparar_banco(self) -> None:
        codigo, texto = self.fabrica("banco")
        if codigo != 0 or not (self.banco / "aifec").is_file():
            raise RuntimeError("no se pudo preparar el banco real: %s" % texto[-300:])

    def borrar(self) -> None:
        _borrar(self.raiz)


def arbol(carpeta: Path, ignorar=()) -> dict:
    """Instantánea (tamaño y fecha de cada fichero) de una carpeta, sin las subcarpetas de `ignorar`."""
    carpeta = Path(carpeta)
    resultado = {}
    for ruta, subcarpetas, nombres in os.walk(str(carpeta)):
        relativa = os.path.relpath(ruta, str(carpeta)).replace("\\", "/")
        subcarpetas[:] = [s for s in subcarpetas if (s if relativa == "." else relativa + "/" + s) not in ignorar and s != "__pycache__"]
        for nombre in nombres:
            ficha = os.stat(os.path.join(ruta, nombre))
            clave = nombre if relativa == "." else relativa + "/" + nombre
            resultado[clave] = (ficha.st_size, ficha.st_mtime_ns)
    return resultado
