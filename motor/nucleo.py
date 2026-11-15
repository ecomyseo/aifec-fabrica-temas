"""AIFEC — motor de fábrica: el ciclo de un encargo y el trabajo de cada día.

Un encargo recorre preparar → motor → puertas → hecho (o rechazado, y atascado al agotar los
intentos). Todo el estado vive en disco, así que cualquier corte se reanuda por donde iba, y nada a
medias cuenta como hecho. `trabajar` respeta el plan: activo, horario, cupo, parar, tope de gasto y
atascos seguidos, y termina siempre con el cerrojo suelto y una línea de resumen.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from . import avisos, banco, cola as cola_mod, escaparate, estado, motores, plan as plan_mod, puertas

CODIGO_BIEN = 0
CODIGO_ALGO_NO_PASA = 1
CODIGO_USO = 2
CODIGO_TOPE = 3
CODIGO_ATASCOS = 4
CODIGO_OCUPADA = 5

PLANTILLA_ENCARGO = """# Encargo: {{nombre}} ({{slug}})

Eres el motor de «{{titulo}}» y fabricas {{clase}} de AIFEC. Este encargo es uno de ellos.

## El encargo

{{encargo}}

## Dónde escribir

Solo en `{{trabajo}}`. Tiene que quedar ahí el trabajo completo, con su `{{manifiesto}}`, listo para
copiar a `{{carpeta_destino}}/` de una instalación de AIFEC. Nada fuera de esa carpeta.

## Qué seguir

{{skill}}

## Dónde está AIFEC, para leerlo

La copia de trabajo está en `{{banco}}`. Solo se lee.

## Lo que ya existe y no hay que repetir

{{existentes}}

## Cómo comprobar el trabajo antes de darlo por terminado

`{{comprobar}}`

Sale con 0 si todas las puertas pasan, y con 1 si alguna no pasa; el informe dice cuál y por qué.

## Lo que falló la vez anterior

{{anterior}}

## Prohibido

Tocar AIFEC o su copia de trabajo, salir a Internet, escribir fuera de `{{trabajo}}` y dar por bueno lo
que no has comprobado.
"""


class Contexto:
    """Todo lo que necesita el motor: dónde está cada cosa, el plan, la cola, el libro de gasto y el reloj."""

    def __init__(self, raiz, plan: dict, config: dict, reloj=None, errores_plan=None):
        self.raiz = Path(raiz).resolve()
        self.rutas = estado.Rutas(self.raiz)
        self.plan = plan
        self.config = config
        self.errores_plan = list(errores_plan or [])
        self._reloj = reloj or datetime.now
        self.libro = estado.Libro(self.rutas.gasto)
        self.cola = cola_mod.Cola(self.rutas, self.ahora)

    def ahora(self) -> datetime:
        return self._reloj()

    def apuntar(self, mensaje: str) -> None:
        estado.apuntar(self.rutas.log, mensaje, self.ahora())


def abrir(raiz, estricto: bool = True, reloj=None) -> Contexto:
    """Abre la fábrica de `raiz`. Con `estricto`, un plan inválido lanza `PlanInvalido`."""
    config = plan_mod.cargar_config(raiz)
    plan, errores = plan_mod.cargar(raiz, config)
    if errores and estricto:
        raise plan_mod.PlanInvalido(errores)
    return Contexto(raiz, plan, config, reloj, errores)


# ---- el encargo que recibe el motor -----------------------------------------------------------

def _linea_de(carpeta: Path, manifiesto: str) -> str:
    datos = estado.leer(carpeta / manifiesto, {})
    if not isinstance(datos, dict):
        datos = {}
    nombre = datos.get("name") or datos.get("nombre") or ""
    descripcion = datos.get("description") or datos.get("descripcion") or ""
    texto = "- `%s`" % carpeta.name
    if nombre:
        texto += " — %s" % nombre
    if descripcion:
        texto += ": %s" % descripcion
    return texto


def _existentes(ctx, slug: str) -> str:
    vistos = {}
    for base in (ctx.rutas.banco / ctx.config["carpeta_destino"], ctx.rutas.salida):
        if base.is_dir():
            for carpeta in sorted(p for p in base.iterdir() if p.is_dir() and p.name != slug):
                vistos.setdefault(carpeta.name, _linea_de(carpeta, ctx.config["manifiesto"]))
    lineas = [vistos[k] for k in sorted(vistos)][:80]
    return "\n".join(lineas) if lineas else "(todavía no hay nada)"


def _lo_anterior(ctx, slug: str) -> str:
    datos = ctx.cola.estado(slug)
    intentos = int(datos.get("intentos") or 0)
    if intentos <= 1:
        return "Nada: es el primer intento."
    informe = estado.leer(ctx.rutas.puertas_json(slug), {})
    lineas = ["Este es el intento número %d. El anterior se rechazó así:" % intentos, ""]
    if datos.get("motivo"):
        lineas.append("Motivo: %s" % datos["motivo"])
    if isinstance(informe, dict):
        for puerta in informe.get("puertas", []):
            if puerta.get("estado") == "no_pasa":
                lineas.append("- puerta `%s`: %s" % (puerta.get("nombre"), puerta.get("resumen")))
                for detalle in (puerta.get("detalles") or [])[:10]:
                    lineas.append("    - %s" % detalle)
    lineas.append("")
    lineas.append("Lo que ya hay en la carpeta de salida sigue ahí: continúa desde eso, no empieces de cero.")
    return "\n".join(lineas)


def _campos(encargo: dict) -> str:
    lineas = []
    for clave, valor in encargo.items():
        if isinstance(valor, (list, dict)):
            valor = json.dumps(valor, ensure_ascii=False)
        lineas.append("- **%s**: %s" % (clave, valor))
    return "\n".join(lineas)


def construir_encargo(ctx, slug: str) -> str:
    """El texto completo del encargo, rellenando `plantillas/encargo.md`."""
    encargo = ctx.cola.obtener(slug)
    try:
        plantilla = (ctx.rutas.plantillas / "encargo.md").read_text(encoding="utf-8")
    except OSError:
        plantilla = PLANTILLA_ENCARGO
    skill = ctx.raiz / "skill" / "SKILL.md"
    return escaparate.rellenar(plantilla, {
        "titulo": ctx.config["titulo"], "clase": ctx.config["clase"], "slug": slug,
        "nombre": encargo.get("nombre") or slug, "encargo": _campos(encargo),
        "trabajo": "salida/%s/" % slug, "manifiesto": ctx.config["manifiesto"],
        "carpeta_destino": ctx.config["carpeta_destino"],
        "skill": ("Sigue `skill/SKILL.md` (con sus plantillas y referencias)." if skill.is_file()
                  else "(esta fábrica no trae skill: sigue las reglas del propio encargo)"),
        "banco": "estado/banco/", "existentes": _existentes(ctx, slug),
        "comprobar": "python fabrica.py puertas %s" % slug, "anterior": _lo_anterior(ctx, slug)})


def escribir_encargo(ctx, slug: str):
    """Escribe `estado/encargos/<slug>.encargo.md` y devuelve `(ruta, texto)`."""
    texto = construir_encargo(ctx, slug)
    ruta = ctx.rutas.encargo_md(slug)
    estado.escribir_texto(ruta, texto)
    return ruta, texto


# ---- el ciclo de un encargo -------------------------------------------------------------------

def _racha(ctx) -> int:
    datos = estado.leer(ctx.rutas.racha, {})
    valor = datos.get("atascados_seguidos") if isinstance(datos, dict) else 0
    return valor if isinstance(valor, int) else 0


def _fijar_racha(ctx, valor: int) -> None:
    estado.escribir(ctx.rutas.racha, {"atascados_seguidos": valor})


def _rechazar(ctx, slug: str, motivo: str):
    final = ctx.cola.rechazar(slug, motivo, ctx.plan["intentos"])
    ctx.apuntar("%s: %s — %s" % (slug, final, motivo))
    if final == "atascado":
        plan_mod.registrar_cierre(ctx.rutas.dias, slug, ctx.ahora())
        _fijar_racha(ctx, _racha(ctx) + 1)
        avisos.avisar(ctx, "%s: el encargo «%s» se ha atascado tras %d intentos. %s" % (
            ctx.config["titulo"], slug, ctx.plan["intentos"], motivo))
    return final, motivo


def _hay_algo(carpeta: Path) -> bool:
    return carpeta.is_dir() and any(p.is_file() for p in carpeta.rglob("*"))


def _preparar_esqueleto(ctx, slug: str, encargo: dict) -> None:
    try:
        banco.preparar(ctx)
        hecho, mensaje = banco.esqueleto(ctx, slug, encargo.get("nombre") or slug)
    except (OSError, RuntimeError) as error:
        hecho, mensaje = False, "no pude preparar el esqueleto: %s" % error
    ctx.apuntar("%s: %s" % (slug, mensaje))


def _fase_puertas(ctx, slug: str):
    candidato = ctx.rutas.salida_de(slug)
    manifiesto = candidato / ctx.config["manifiesto"]
    if not manifiesto.is_file():
        motivo = "falta %s en salida/%s/" % (ctx.config["manifiesto"], slug)
        informe = {"slug": slug, "pasa": False, "puertas": [
            {"nombre": "manifiesto", "estado": "no_pasa", "resumen": motivo, "detalles": [], "medidas": {}}],
            "linea": "PUERTAS: 0 de 1 pasan, 1 no pasan", "fecha": ctx.ahora().isoformat(timespec="seconds")}
        estado.escribir(ctx.rutas.puertas_json(slug), informe)
        return _rechazar(ctx, slug, motivo)
    informe = puertas.lanzar(ctx, slug)
    if informe["pasa"]:
        ctx.cola.transicionar(slug, "hecho", informe["linea"], motivo="")
        escaparate.escribir_ficha(ctx, slug, "hecho", informe)
        plan_mod.registrar_cierre(ctx.rutas.dias, slug, ctx.ahora())
        _fijar_racha(ctx, 0)
        ctx.apuntar("%s: hecho — %s" % (slug, informe["linea"]))
        return "hecho", informe["linea"]
    fallan = ["%s: %s" % (p["nombre"], p["resumen"]) for p in informe["puertas"] if p["estado"] == "no_pasa"]
    return _rechazar(ctx, slug, "; ".join(fallan) or "alguna puerta no pasa")


def ciclo(ctx, slug: str):
    """Un intento de un encargo. Devuelve `(resultado, mensaje)`; el resultado es `hecho`,
    `rechazado`, `atascado`, `espera` (una persona tiene que hacer algo), `tope` (el gasto no lo
    permite) o `nada` (ya estaba terminado)."""
    cola = ctx.cola
    actual = cola.estado(slug)["estado"]
    if actual in ("hecho", "aprobado", "atascado"):
        return "nada", "ya está %s" % actual
    encargo = cola.obtener(slug)
    carpeta = ctx.rutas.salida_de(slug)

    if actual in ("pendiente", "rechazado"):
        permitido, motivo = motores.puede_lanzar(ctx)
        if not permitido:
            ctx.apuntar("%s: %s" % (slug, motivo))
            return "tope", motivo
        era_nuevo = actual == "pendiente"
        cola.comenzar_intento(slug)
        ctx.apuntar("%s: empiezo el intento %d" % (slug, cola.estado(slug)["intentos"]))
        carpeta.mkdir(parents=True, exist_ok=True)
        if era_nuevo and not _hay_algo(carpeta):
            _preparar_esqueleto(ctx, slug, encargo)
        actual = "en_curso"

    if actual == "en_curso":
        permitido, motivo = motores.puede_lanzar(ctx)
        if not permitido:
            ctx.apuntar("%s: %s" % (slug, motivo))
            return "tope", motivo
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta, texto = escribir_encargo(ctx, slug)
        antes = motores.instantanea(ctx, slug)
        resultado = motores.ejecutar(ctx, slug, ruta, texto)
        cambios = motores.diferencias(antes, motores.instantanea(ctx, slug))
        if cambios:
            motivo = "el motor escribió fuera de salida/%s/: %s" % (slug, "; ".join(cambios[:10]))
            cola.transicionar(slug, "en_puertas", "el motor terminó")
            return _rechazar(ctx, slug, motivo)
        if resultado.estado == "tope":
            return "tope", resultado.motivo
        if resultado.estado == "espera":
            ctx.apuntar("%s: %s" % (slug, resultado.motivo))
            return "espera", resultado.motivo
        cola.transicionar(slug, "en_puertas", "el motor terminó" if resultado.estado == "listo"
                          else "el motor falló: " + resultado.motivo)
        if resultado.estado == "fallo":
            return _rechazar(ctx, slug, resultado.motivo)
        actual = "en_puertas"

    return _fase_puertas(ctx, slug)


# ---- el trabajo de cada día -------------------------------------------------------------------

def _encargo_entero(ctx, slug: str):
    """Un encargo hasta que se cierra: los reintentos de un rechazado van seguidos, salvo que alguien
    haya pedido parar."""
    while True:
        resultado, mensaje = ciclo(ctx, slug)
        if resultado == "rechazado" and not ctx.rutas.parar.exists():
            continue
        return resultado, mensaje


def _trabajar(ctx, uno: bool, slug_forzado):
    plan = ctx.plan
    hechos = atascados = esperas = 0
    parada = ""
    codigo = CODIGO_BIEN
    if ctx.rutas.parar.exists():
        return CODIGO_BIEN, "FÁBRICA: en pausa (`parar`); `python fabrica.py reanudar` para seguir"
    if slug_forzado is None and _racha(ctx) >= plan["atascados_seguidos_que_paran"]:
        return CODIGO_ATASCOS, ("FÁBRICA: parada por %d atascos seguidos; mira los encargos atascados y "
                                "`python fabrica.py reanudar`" % _racha(ctx))
    if slug_forzado is not None:
        ctx.cola.obtener(slug_forzado)
    while True:
        if ctx.rutas.parar.exists():
            parada = "parar"
            break
        if slug_forzado is None:
            if not plan_mod.en_horario(plan, ctx.ahora()):
                parada = "fuera de horario"
                break
            dias = estado.leer(ctx.rutas.dias, {})
            if plan_mod.cupo_de_hoy(plan, dias, ctx.ahora()) <= 0:
                parada = "cupo de hoy cubierto"
                break
        slug = slug_forzado or ctx.cola.siguiente(plan["intentos"])
        if slug is None:
            parada = "cola vacía"
            break
        resultado, mensaje = _encargo_entero(ctx, slug)
        if resultado == "tope":
            codigo, parada = CODIGO_TOPE, mensaje
            avisos.avisar(ctx, "%s: parada por gasto. %s" % (ctx.config["titulo"], mensaje))
            break
        if resultado == "espera":
            esperas += 1
            parada = "esperando a una persona"
            break
        if resultado == "hecho":
            hechos += 1
        elif resultado == "atascado":
            atascados += 1
            if _racha(ctx) >= plan["atascados_seguidos_que_paran"]:
                codigo, parada = CODIGO_ATASCOS, "atascos seguidos"
                break
        elif resultado in ("nada", "rechazado"):
            parada = "el encargo %s ya está terminado" % slug if resultado == "nada" else "parar"
            break
        if uno or slug_forzado is not None:
            parada = "un solo encargo"
            break
    if codigo == CODIGO_BIEN and atascados:
        codigo = CODIGO_ALGO_NO_PASA
    if hechos + atascados and parada in ("cupo de hoy cubierto", "cola vacía"):
        avisos.avisar(ctx, "%s: día terminado, %d hechos y %d atascados" % (ctx.config["titulo"], hechos, atascados))
    if hechos:
        escaparate.escribir_indice(ctx)
    linea = "FÁBRICA: %d hechos, %d atascados, %d en espera; paro: %s" % (hechos, atascados, esperas, parada)
    ctx.apuntar(linea)
    return codigo, linea


def trabajar(ctx, uno: bool = False, slug: str = None):
    """Lo de hoy (o un solo encargo). Devuelve `(código de salida, línea de resumen)`."""
    if not ctx.plan["activo"]:
        return CODIGO_BIEN, "FÁBRICA: inactiva (activo=false en el plan); no hago nada"
    cerrojo = estado.Cerrojo(ctx.rutas.lock)
    try:
        cerrojo.adquirir()
        if not cerrojo.tomado:
            return CODIGO_OCUPADA, "FÁBRICA: hay otra fábrica trabajando en esta carpeta; salgo sin tocar nada"
        return _trabajar(ctx, uno, slug)
    finally:
        cerrojo.soltar()


# ---- las demás órdenes ------------------------------------------------------------------------

def parar(ctx) -> None:
    estado.escribir_texto(ctx.rutas.parar, ctx.ahora().isoformat(timespec="seconds") + "\n")
    ctx.apuntar("parar: no se empezará otro encargo")


def reanudar(ctx) -> None:
    try:
        ctx.rutas.parar.unlink()
    except OSError:
        pass
    _fijar_racha(ctx, 0)
    ctx.apuntar("reanudar")


def aprobar(ctx, slug: str) -> None:
    ctx.cola.obtener(slug)
    ctx.cola.transicionar(slug, "aprobado", "visto bueno de una persona")
    escaparate.cambiar_estado_ficha(ctx, slug, "aprobado")
    escaparate.escribir_indice(ctx)
    ctx.apuntar("%s: aprobado" % slug)


def rechazar_a_mano(ctx, slug: str, motivo: str) -> str:
    ctx.cola.obtener(slug)
    final = ctx.cola.rechazar(slug, "una persona lo rechaza: " + motivo, ctx.plan["intentos"])
    escaparate.quitar_ficha(ctx, slug)
    escaparate.escribir_indice(ctx)
    ctx.apuntar("%s: %s por una persona — %s" % (slug, final, motivo))
    return final


def instalar(ctx, slug: str, instalacion, forzar: bool = False) -> Path:
    """Copia lo fabricado a `<instalación>/<carpeta_destino>/<slug>/`, solo si está hecho o aprobado."""
    ctx.cola.obtener(slug)
    actual = ctx.cola.estado(slug)["estado"]
    if actual not in ("hecho", "aprobado"):
        raise ValueError("«%s» está «%s»: solo se instala lo que está hecho o aprobado" % (slug, actual))
    instalacion = Path(instalacion).resolve()
    if not (instalacion / "core" / "bootstrap.php").is_file() or not (instalacion / "aifec").is_file():
        raise ValueError("no parece una instalación de AIFEC: %s" % instalacion)
    destino = instalacion / ctx.config["carpeta_destino"] / slug
    if destino.exists() and not forzar:
        raise ValueError("ya existe %s (usa --forzar para sustituirlo)" % destino)
    if destino.exists():
        shutil.rmtree(str(destino))
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(str(ctx.rutas.salida_de(slug)), str(destino))
    ctx.apuntar("%s: instalado en %s" % (slug, destino))
    return destino


def texto_estado(ctx) -> list:
    """Las líneas de `estado`: día, cupo, hechos hoy, en curso, atascados, siguiente y gasto."""
    plan = ctx.plan
    ahora = ctx.ahora()
    dias = estado.leer(ctx.rutas.dias, {})
    cuentas = ctx.cola.cuentas()
    hechos_hoy = plan_mod.cerrados_hoy(dias, ahora)
    en_curso = [e["slug"] for e in ctx.cola.encargos() if ctx.cola.estado(e["slug"])["estado"] in (
        "en_curso", "en_puertas")]
    atascados = [e["slug"] for e in ctx.cola.encargos() if ctx.cola.estado(e["slug"])["estado"] == "atascado"]
    siguiente = ctx.cola.siguiente(plan["intentos"])
    tope = plan["gasto"]["tope_eur"]
    lineas = [
        ctx.config["titulo"],
        "Día: %s · horario %s–%s (%s)" % (ahora.strftime("%Y-%m-%d"), plan["horario"]["inicio"],
                                         plan["horario"]["fin"],
                                         "dentro" if plan_mod.en_horario(plan, ahora) else "fuera"),
        "Cupo de hoy: %d de %d cerrados (quedan %d)" % (hechos_hoy, plan["por_dia"],
                                                        plan_mod.cupo_de_hoy(plan, dias, ahora)),
        "Motor: %s" % plan["motor"]["tipo"],
        "En curso: %s" % (", ".join(en_curso) or "ninguno"),
        "Pasan las puertas, sin mirar por una persona: %d · Aprobados: %d" % (cuentas["hecho"], cuentas["aprobado"]),
        "Atascados: %s" % (", ".join(atascados) or "ninguno"),
        "Pendientes: %d · Rechazados que reintentan: %d" % (cuentas["pendiente"], cuentas["rechazado"]),
        "Siguiente: %s" % (siguiente or "nada por hacer"),
        "Gasto: %.2f € de un tope de %.2f €" % (ctx.libro.gastado(), tope),
        "En pausa: %s · atascos seguidos: %d de %d" % ("sí" if ctx.rutas.parar.exists() else "no", _racha(ctx),
                                                       plan["atascados_seguidos_que_paran"]),
    ]
    total = sum(cuentas.values())
    lineas.append("ESTADO: %d encargos — %d pasan las puertas, %d aprobados, %d atascados, %d pendientes" % (
        total, cuentas["hecho"], cuentas["aprobado"], cuentas["atascado"], cuentas["pendiente"]))
    return lineas


def texto_calendario(ctx) -> list:
    """Qué haría la fábrica cada día de trabajo hasta vaciar la cola, con el plan de ahora."""
    plan = ctx.plan
    ahora = ctx.ahora()
    por_hacer = ctx.cola.en_orden_de_trabajo(plan["intentos"])
    restante_hoy = plan_mod.cupo_de_hoy(plan, estado.leer(ctx.rutas.dias, {}), ahora)
    lineas = []
    dia = ahora
    dia_n = 0
    capacidad = restante_hoy
    while por_hacer:
        if capacidad <= 0:
            dia = dia + timedelta(days=1)
            capacidad = plan["por_dia"]
        dia_n += 1
        tanda, por_hacer = por_hacer[:capacidad], por_hacer[capacidad:]
        lineas.append("Día %d (%s): %s" % (dia_n, dia.strftime("%Y-%m-%d"), ", ".join(tanda)))
        capacidad = 0
    total = len(ctx.cola.en_orden_de_trabajo(plan["intentos"]))
    lineas.append("CALENDARIO: %d encargos en %d días de trabajo" % (total, dia_n))
    return lineas
