"""AIFEC — motor de fábrica: el plan y la configuración de la fábrica.

`fabrica.json` dice qué fabrica esta fábrica (lo único que la distingue de otra) y `plan.json` dice
cómo trabaja (horario, cupo, motor, gasto, puertas). Aquí se leen, se completan con sus valores por
defecto y se validan, con errores claros.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import copy
import re
from datetime import datetime
from pathlib import Path

from . import estado

MOTORES = ("manual", "simulado", "orden")

DEFECTOS = {
    "activo": True,
    "php": "php",
    "php_versiones": [],
    "horario": {"inicio": "00:00", "fin": "23:59"},
    "por_dia": 3,
    "intentos": 3,
    "atascados_seguidos_que_paran": 2,
    "motor": {"tipo": "manual", "minutos": 45},
    "gasto": {"tope_eur": 0, "por_sesion_eur": 0},
    "puertas": None,
    "puertas_minutos": 15,
    "umbral_estructura": 0.82,
    "capturas": {"activas": False},
    "aviso": {"orden": []},
    "banco": {"sitio": "banco", "orden_sitio": None},
}

CLAVES_CONFIG = ("clase", "titulo", "carpeta_destino", "manifiesto", "orden_esqueleto")

_HORA = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_NOMBRE = re.compile(r"^[a-z0-9_]+$")


class PlanInvalido(Exception):
    """El plan o la configuración de la fábrica no valen; `errores` dice por qué, uno por línea."""

    def __init__(self, errores):
        self.errores = list(errores)
        super().__init__("; ".join(self.errores))


def _es_numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _es_entero(valor) -> bool:
    return isinstance(valor, int) and not isinstance(valor, bool)


def _ruta(valor, raiz: Path) -> Path:
    ruta = Path(str(valor)).expanduser()
    if not ruta.is_absolute():
        ruta = raiz / ruta
    return ruta.resolve()


def cargar_config(raiz) -> dict:
    """Lee `fabrica.json`. Sin él, o con claves que faltan, la fábrica no puede saber qué fabrica."""
    raiz = Path(raiz)
    datos = estado.leer(raiz / "fabrica.json", None)
    if not isinstance(datos, dict):
        raise PlanInvalido(["fabrica.json no existe o no es un JSON válido"])
    errores = []
    for clave in CLAVES_CONFIG:
        if clave not in datos:
            errores.append("fabrica.json: falta la clave «%s»" % clave)
    for clave in ("clase", "titulo", "carpeta_destino", "manifiesto"):
        if clave in datos and (not isinstance(datos[clave], str) or not datos[clave].strip()):
            errores.append("fabrica.json: «%s» tiene que ser un texto no vacío" % clave)
    esqueleto = datos.get("orden_esqueleto")
    if "orden_esqueleto" in datos and (
            not isinstance(esqueleto, list) or not esqueleto or not all(isinstance(a, str) for a in esqueleto)):
        errores.append("fabrica.json: «orden_esqueleto» tiene que ser una lista de textos")
    carpeta = datos.get("carpeta_destino")
    if isinstance(carpeta, str) and (".." in carpeta or carpeta.startswith(("/", "\\")) or ":" in carpeta):
        errores.append("fabrica.json: «carpeta_destino» tiene que ser una carpeta relativa simple")
    puertas = datos.get("puertas")
    if puertas is not None and (not isinstance(puertas, list) or not all(
            isinstance(p, str) and _NOMBRE.match(p) for p in puertas)):
        errores.append("fabrica.json: «puertas» tiene que ser una lista de nombres")
    if errores:
        raise PlanInvalido(errores)
    return datos


def _fusionar(defecto, dado):
    resultado = copy.deepcopy(defecto)
    for clave, valor in dado.items():
        if isinstance(resultado.get(clave), dict) and isinstance(valor, dict):
            resultado[clave].update(copy.deepcopy(valor))
        else:
            resultado[clave] = copy.deepcopy(valor)
    return resultado


def puertas_por_defecto(raiz, config: dict) -> list:
    """Las puertas de la fábrica: las que diga `fabrica.json` o, si no dice, las de `puertas/`."""
    if isinstance(config.get("puertas"), list):
        return list(config["puertas"])
    carpeta = Path(raiz) / "puertas"
    if not carpeta.is_dir():
        return []
    return sorted(f.stem for f in carpeta.glob("*.py") if not f.name.startswith("_"))


def minutos_de(texto: str):
    """«HH:MM» a minutos desde medianoche; None si está mal escrita."""
    encontrado = _HORA.match(texto) if isinstance(texto, str) else None
    if not encontrado:
        return None
    return int(encontrado.group(1)) * 60 + int(encontrado.group(2))


def cargar(raiz, config: dict):
    """Devuelve `(plan, errores)`: el plan con sus valores por defecto y la lista de errores."""
    raiz = Path(raiz).resolve()
    crudo = estado.leer(raiz / "plan.json", None)
    errores = []
    if not isinstance(crudo, dict):
        crudo = {}
        errores.append("plan.json no existe o no es un JSON válido")
    crudo = {k: v for k, v in crudo.items() if not str(k).startswith("_")}
    desconocidas = sorted(k for k in crudo if k not in DEFECTOS and k != "aifec")
    for clave in desconocidas:
        errores.append("plan.json: clave desconocida «%s»" % clave)
    plan = _fusionar(DEFECTOS, crudo)
    if plan.get("puertas") is None:
        plan["puertas"] = puertas_por_defecto(raiz, config)

    # aifec: la instalación de AIFEC, que solo se lee.
    if not isinstance(crudo.get("aifec"), str) or not crudo.get("aifec", "").strip():
        errores.append("plan.json: falta «aifec» (ruta de una instalación de AIFEC)")
        plan["aifec"] = None
    else:
        ruta = _ruta(crudo["aifec"], raiz)
        plan["aifec"] = str(ruta)
        if not ruta.is_dir():
            errores.append("plan.json: «aifec» no existe: %s" % ruta)
        elif not (ruta / "core" / "bootstrap.php").is_file() or not (ruta / "aifec").is_file():
            errores.append("plan.json: «aifec» no parece una instalación de AIFEC "
                           "(faltan core/bootstrap.php o el fichero aifec): %s" % ruta)

    if not isinstance(plan["activo"], bool):
        errores.append("plan.json: «activo» tiene que ser true o false")
    if not isinstance(plan["php"], str) or not plan["php"].strip():
        errores.append("plan.json: «php» tiene que ser un texto")
    if not isinstance(plan["php_versiones"], list) or not all(isinstance(p, str) for p in plan["php_versiones"]):
        errores.append("plan.json: «php_versiones» tiene que ser una lista de textos")
    for clave in ("por_dia", "intentos", "atascados_seguidos_que_paran"):
        if not _es_entero(plan[clave]) or plan[clave] < 1:
            errores.append("plan.json: «%s» tiene que ser un entero de 1 o más" % clave)
    if not _es_numero(plan["puertas_minutos"]) or plan["puertas_minutos"] <= 0:
        errores.append("plan.json: «puertas_minutos» tiene que ser un número positivo")
    if not _es_numero(plan["umbral_estructura"]) or not 0 < plan["umbral_estructura"] <= 1:
        errores.append("plan.json: «umbral_estructura» tiene que estar entre 0 y 1")

    horario = plan["horario"]
    if not isinstance(horario, dict):
        errores.append("plan.json: «horario» tiene que ser {\"inicio\": \"HH:MM\", \"fin\": \"HH:MM\"}")
    else:
        for clave in ("inicio", "fin"):
            if minutos_de(horario.get(clave)) is None:
                errores.append("plan.json: horario.%s tiene que ser una hora «HH:MM» (00:00 a 23:59)" % clave)

    motor = plan["motor"]
    if not isinstance(motor, dict):
        errores.append("plan.json: «motor» tiene que ser un objeto con «tipo»")
    else:
        tipo = motor.get("tipo")
        if tipo not in MOTORES:
            errores.append("plan.json: motor.tipo desconocido «%s» (valen: %s)" % (tipo, ", ".join(MOTORES)))
        if not _es_numero(motor.get("minutos")) or motor["minutos"] <= 0:
            errores.append("plan.json: motor.minutos tiene que ser un número positivo")
        if tipo == "orden":
            orden = motor.get("orden")
            if not isinstance(orden, list) or not orden or not all(isinstance(a, str) for a in orden):
                errores.append("plan.json: motor.orden tiene que ser una lista (programa y argumentos)")
            if motor.get("coste_regex") is not None:
                try:
                    re.compile(motor["coste_regex"])
                except (re.error, TypeError):
                    errores.append("plan.json: motor.coste_regex no es una expresión regular válida")
        if tipo == "simulado":
            if not isinstance(motor.get("origen"), str) or not motor.get("origen"):
                errores.append("plan.json: el motor simulado necesita motor.origen (carpeta a copiar)")
            else:
                origen = _ruta(motor["origen"], raiz)
                motor["origen"] = str(origen)
                if not origen.is_dir():
                    errores.append("plan.json: motor.origen no existe: %s" % origen)

    gasto = plan["gasto"]
    if not isinstance(gasto, dict):
        errores.append("plan.json: «gasto» tiene que ser {\"tope_eur\": n, \"por_sesion_eur\": n}")
    else:
        for clave in ("tope_eur", "por_sesion_eur"):
            if not _es_numero(gasto.get(clave)) or gasto[clave] < 0:
                errores.append("plan.json: gasto.%s tiene que ser un número de 0 o más" % clave)

    if not isinstance(plan["puertas"], list) or not all(
            isinstance(p, str) and _NOMBRE.match(p) for p in plan["puertas"]):
        errores.append("plan.json: «puertas» tiene que ser una lista de nombres (letras, cifras y _)")
    elif not plan["puertas"]:
        errores.append("plan.json: no hay ninguna puerta: sin ellas nada podría darse por hecho")

    if not isinstance(plan["capturas"], dict) or not isinstance(plan["capturas"].get("activas"), bool):
        errores.append("plan.json: capturas.activas tiene que ser true o false")
    aviso = plan["aviso"]
    if not isinstance(aviso, dict) or not isinstance(aviso.get("orden"), list) or not all(
            isinstance(a, str) for a in aviso["orden"]):
        errores.append("plan.json: aviso.orden tiene que ser una lista de textos (vacía = no avisa)")
    banco = plan["banco"]
    if not isinstance(banco, dict) or not isinstance(banco.get("sitio"), str) or not banco["sitio"]:
        errores.append("plan.json: banco.sitio tiene que ser un identificador")
    elif banco.get("orden_sitio") is not None and (
            not isinstance(banco["orden_sitio"], list) or not all(isinstance(a, str) for a in banco["orden_sitio"])):
        errores.append("plan.json: banco.orden_sitio tiene que ser una lista de textos")
    return plan, errores


def cargar_estricto(raiz, config: dict) -> dict:
    plan, errores = cargar(raiz, config)
    if errores:
        raise PlanInvalido(errores)
    return plan


def en_horario(plan: dict, ahora: datetime) -> bool:
    """¿Está `ahora` dentro del tramo de trabajo? (un tramo que cruza la medianoche también vale)."""
    inicio = minutos_de(plan["horario"]["inicio"])
    fin = minutos_de(plan["horario"]["fin"])
    actual = ahora.hour * 60 + ahora.minute
    if inicio <= fin:
        return inicio <= actual <= fin
    return actual >= inicio or actual <= fin


def cerrados_hoy(dias: dict, ahora: datetime) -> int:
    dia = dias.get(ahora.strftime("%Y-%m-%d")) if isinstance(dias, dict) else None
    return len(dia.get("slugs", [])) if isinstance(dia, dict) else 0


def cupo_de_hoy(plan: dict, dias: dict, ahora: datetime) -> int:
    """Encargos que aún se pueden cerrar hoy. Los días cuentan cuando la fábrica trabaja: un día
    sin lanzarla no gasta plan ni lo acumula."""
    return max(0, int(plan["por_dia"]) - cerrados_hoy(dias, ahora))


def registrar_cierre(ruta_dias, slug: str, ahora: datetime) -> None:
    dias = estado.leer(ruta_dias, {})
    if not isinstance(dias, dict):
        dias = {}
    dia = dias.setdefault(ahora.strftime("%Y-%m-%d"), {"slugs": []})
    if not isinstance(dia.get("slugs"), list):
        dia["slugs"] = []
    if slug not in dia["slugs"]:
        dia["slugs"].append(slug)
    estado.escribir(ruta_dias, dias)
