"""AIFEC — motor de fábrica: el escaparate.

Una ficha por encargo terminado (`escaparate/<slug>/ficha.json` y `ficha.md`) y una página estática
(`escaparate/index.html`, sin nada de fuera) que las junta. Separa «pasan las puertas» de
«aprobados»: no se llama terminado a lo que nadie ha mirado.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import html
import re

from . import estado

_MARCA = re.compile(r"\{\{(\w+)\}\}")

PLANTILLA_FICHA = """# {{nombre}}

- Encargo: `{{slug}}` ({{clase}})
- Estado: **{{estado}}**
- Sector o función: {{sector}}
- Idea: {{idea}}
- Fecha: {{fecha}}
- Intentos: {{intentos}}
- Motor: {{motor}}
- Gasto: {{gasto_eur}} €

## Puertas

{{puertas}}
"""


def rellenar(plantilla: str, valores: dict) -> str:
    """Sustituye {{clave}} en una sola pasada (lo que contenga un valor no se vuelve a sustituir)."""
    return _MARCA.sub(lambda m: str(valores.get(m.group(1), "")), plantilla)


def _manifiesto(ctx, slug: str) -> dict:
    datos = estado.leer(ctx.rutas.salida_de(slug) / ctx.config["manifiesto"], {})
    return datos if isinstance(datos, dict) else {}


def _plantilla_ficha(ctx) -> str:
    ruta = ctx.rutas.plantillas / "ficha.md"
    try:
        return ruta.read_text(encoding="utf-8")
    except OSError:
        return PLANTILLA_FICHA


def escribir_ficha(ctx, slug: str, estado_final: str, informe: dict = None) -> dict:
    """Escribe la ficha de un encargo que pasa las puertas (o que una persona aprobó)."""
    encargo = ctx.cola.obtener(slug)
    manifiesto = _manifiesto(ctx, slug)
    datos = ctx.cola.estado(slug)
    if informe is None:
        informe = estado.leer(ctx.rutas.puertas_json(slug), {})
    entradas = informe.get("puertas", []) if isinstance(informe, dict) else []
    ficha = {
        "slug": slug,
        "nombre": encargo.get("nombre") or manifiesto.get("name") or manifiesto.get("nombre") or slug,
        "clase": ctx.config["clase"],
        "sector": str(encargo.get("sector") or manifiesto.get("sector") or ""),
        "idea": str(encargo.get("idea") or ""),
        "fecha": ctx.ahora().isoformat(timespec="seconds"),
        "intentos": int(datos.get("intentos") or 0),
        "puertas": [{"nombre": e.get("nombre"), "estado": e.get("estado"), "resumen": e.get("resumen"),
                     "medidas": e.get("medidas", {})} for e in entradas],
        "resumen_puertas": informe.get("linea", "") if isinstance(informe, dict) else "",
        "estado": estado_final,
        "motor": ctx.plan["motor"]["tipo"],
        "gasto_eur": ctx.libro.gastado(slug),
    }
    carpeta = ctx.rutas.ficha_dir(slug)
    estado.escribir(carpeta / "ficha.json", ficha)
    lineas = ["- **%s**: %s — %s" % (p["nombre"], p["estado"], p["resumen"]) for p in ficha["puertas"]]
    estado.escribir_texto(carpeta / "ficha.md", rellenar(_plantilla_ficha(ctx), dict(
        ficha, puertas="\n".join(lineas) or "(sin puertas)", sector=ficha["sector"] or "—",
        idea=ficha["idea"] or "—")))
    return ficha


def cambiar_estado_ficha(ctx, slug: str, nuevo: str) -> None:
    ruta = ctx.rutas.ficha_dir(slug) / "ficha.json"
    ficha = estado.leer(ruta, None)
    if isinstance(ficha, dict):
        ficha["estado"] = nuevo
        estado.escribir(ruta, ficha)


def quitar_ficha(ctx, slug: str) -> None:
    for nombre in ("ficha.json", "ficha.md"):
        try:
            (ctx.rutas.ficha_dir(slug) / nombre).unlink()
        except OSError:
            pass


def _tarjeta(ctx, ficha: dict) -> str:
    e = html.escape
    miniaturas = sorted(ctx.rutas.ficha_dir(ficha["slug"]).glob("*.png"))
    imagen = ""
    if miniaturas:
        imagen = '<img src="%s/%s" alt="%s" loading="lazy">' % (
            e(ficha["slug"]), e(miniaturas[0].name), e("Captura de " + ficha["nombre"]))
    puertas = "".join("<li>%s: %s</li>" % (e(str(p.get("nombre"))), e(str(p.get("estado")))) for p in ficha["puertas"])
    return (
        '<article class="ficha">%s<h3>%s</h3><p class="slug">%s</p><p>%s</p><p>%s</p>'
        "<p><small>%s · %s intento(s) · %s</small></p><ul>%s</ul></article>" % (
            imagen, e(ficha["nombre"]), e(ficha["slug"]), e(ficha.get("sector") or ""), e(ficha.get("idea") or ""),
            e(ficha.get("fecha", "")), e(str(ficha.get("intentos", 0))), e(ficha.get("resumen_puertas", "")), puertas))


def escribir_indice(ctx) -> dict:
    """Rehace `escaparate/index.html` con las fichas que hay. Devuelve las cuentas."""
    fichas = []
    if ctx.rutas.escaparate.is_dir():
        for carpeta in sorted(p for p in ctx.rutas.escaparate.iterdir() if p.is_dir()):
            ficha = estado.leer(carpeta / "ficha.json", None)
            if isinstance(ficha, dict) and ficha.get("slug"):
                fichas.append(ficha)
    pasan = [f for f in fichas if f.get("estado") == "hecho"]
    aprobados = [f for f in fichas if f.get("estado") == "aprobado"]
    e = html.escape
    cuerpo = [
        "<!doctype html>", '<html lang="es"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>%s</title>" % e(ctx.config["titulo"]),
        "<style>body{font:16px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:72rem;padding:0 1rem;color:#222}"
        "h1{margin-bottom:.2rem}.rejilla{display:grid;grid-template-columns:repeat(auto-fill,minmax(16rem,1fr));gap:1rem}"
        ".ficha{border:1px solid #ccc;border-radius:.5rem;padding:1rem}.ficha img{max-width:100%;height:auto}"
        ".slug{color:#666;font-family:monospace;margin:0}ul{padding-left:1.2rem;font-size:.85rem}</style>",
        "</head><body>", "<h1>%s</h1>" % e(ctx.config["titulo"]),
        "<p>%d pasan las puertas · %d aprobados por una persona</p>" % (len(pasan), len(aprobados)),
        "<h2>Pasan las puertas (a la espera de que una persona los mire)</h2>",
        '<div class="rejilla">' + "".join(_tarjeta(ctx, f) for f in pasan) + "</div>" if pasan
        else "<p>Ninguno todavía.</p>",
        "<h2>Aprobados</h2>",
        '<div class="rejilla">' + "".join(_tarjeta(ctx, f) for f in aprobados) + "</div>" if aprobados
        else "<p>Ninguno todavía.</p>",
        "</body></html>"]
    estado.escribir_texto(ctx.rutas.escaparate / "index.html", "\n".join(cuerpo) + "\n")
    return {"pasan": len(pasan), "aprobados": len(aprobados)}
