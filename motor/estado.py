"""AIFEC — motor de fábrica: el estado en disco.

Lectura y escritura atómica de JSON, el cerrojo que impide dos fábricas a la vez, el registro y el
libro de gasto. Nada depende de la memoria de un proceso: si se corta, al volver se sigue.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

from . import procesos


class Rutas:
    """Dónde vive cada cosa, siempre relativa a la carpeta de la fábrica."""

    def __init__(self, raiz):
        self.raiz = Path(raiz).resolve()
        self.estado = self.raiz / "estado"
        self.encargos = self.estado / "encargos"
        self.sesiones = self.estado / "sesiones"
        self.banco = self.estado / "banco"
        self.banco_json = self.estado / "banco.json"
        self.lock = self.estado / "fabrica.lock"
        self.log = self.estado / "fabrica.log"
        self.gasto = self.estado / "gasto.json"
        self.dias = self.estado / "dias.json"
        self.racha = self.estado / "racha.json"
        self.parar = self.estado / "parar"
        self.avisos = self.estado / "avisos.log"
        self.salida = self.raiz / "salida"
        self.escaparate = self.raiz / "escaparate"
        self.plan = self.raiz / "plan.json"
        self.cola = self.raiz / "cola.json"
        self.config = self.raiz / "fabrica.json"
        self.plantillas = self.raiz / "plantillas"
        self.puertas = self.raiz / "puertas"

    def salida_de(self, slug):
        return self.salida / slug

    def estado_de(self, slug):
        return self.encargos / (slug + ".json")

    def encargo_md(self, slug):
        return self.encargos / (slug + ".encargo.md")

    def puertas_json(self, slug):
        return self.encargos / (slug + ".puertas.json")

    def ficha_dir(self, slug):
        return self.escaparate / slug


def leer(ruta, defecto=None):
    """Lee un JSON. Si no existe o está a medias, devuelve `defecto`."""
    try:
        with open(ruta, "r", encoding="utf-8-sig") as fichero:
            return json.load(fichero)
    except (OSError, ValueError):
        return defecto


def escribir_texto(ruta, texto: str) -> None:
    """Escribe un fichero de forma atómica: temporal en la misma carpeta y `os.replace`."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name("." + ruta.name + "." + str(os.getpid()) + ".tmp")
    try:
        with open(temporal, "w", encoding="utf-8", newline="\n") as fichero:
            fichero.write(texto)
            fichero.flush()
            os.fsync(fichero.fileno())
        os.replace(temporal, ruta)
    except BaseException:
        try:
            temporal.unlink()
        except OSError:
            pass
        raise


def escribir(ruta, datos) -> None:
    """Escribe un JSON de forma atómica: un corte a mitad no deja un fichero a medias."""
    escribir_texto(ruta, json.dumps(datos, ensure_ascii=False, indent=2) + "\n")


def apuntar(ruta, mensaje: str, ahora: datetime = None) -> None:
    """Añade una línea con fecha al registro."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ahora = ahora or datetime.now()
    with open(ruta, "a", encoding="utf-8", newline="\n") as fichero:
        fichero.write("%s %s\n" % (ahora.strftime("%Y-%m-%d %H:%M:%S"), mensaje))


class Cerrojo:
    """`estado/fabrica.lock` con el PID y la hora. Si ya existe y su PID sigue vivo y es un Python,
    está ocupado; si no, el cerrojo es de un proceso muerto (o de otro programa) y se toma."""

    def __init__(self, ruta, nombre_proceso: str = "python"):
        self.ruta = Path(ruta)
        self.nombre_proceso = nombre_proceso
        self.tomado = False

    def _dueno(self):
        """PID anotado en el cerrojo, o None si está vacío o ilegible (aún se está escribiendo)."""
        for _ in range(6):
            datos = leer(self.ruta, None)
            if isinstance(datos, dict) and isinstance(datos.get("pid"), int):
                return datos["pid"]
            time.sleep(0.05)
        return None

    def adquirir(self) -> bool:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(4):
            try:
                descriptor = os.open(str(self.ruta), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError:
                dueno = self._dueno()
                if dueno is not None and procesos.vivo(dueno, self.nombre_proceso):
                    return False
                self._apartar(dueno)
                continue
            with os.fdopen(descriptor, "w", encoding="utf-8") as fichero:
                json.dump({"pid": os.getpid(), "hora": datetime.now().isoformat(timespec="seconds")}, fichero)
            self.tomado = True
            return True
        return False

    def _apartar(self, dueno_visto) -> None:
        """Retira el cerrojo viejo con un cambio de nombre (solo uno de dos que compitan lo logra).
        Si lo que se retiró era de otro dueño distinto del que se vio, se devuelve a su sitio."""
        viejo = self.ruta.with_name(self.ruta.name + ".viejo." + str(os.getpid()))
        try:
            os.rename(str(self.ruta), str(viejo))
        except OSError:
            return
        datos = leer(viejo, None)
        pid_retirado = datos.get("pid") if isinstance(datos, dict) else None
        if dueno_visto is not None and pid_retirado != dueno_visto:
            try:
                os.link(str(viejo), str(self.ruta))
            except OSError:
                pass
        try:
            viejo.unlink()
        except OSError:
            pass

    def soltar(self) -> None:
        if not self.tomado:
            return
        self.tomado = False
        datos = leer(self.ruta, None)
        if isinstance(datos, dict) and datos.get("pid") == os.getpid():
            try:
                self.ruta.unlink()
            except OSError:
                pass

    def __enter__(self):
        self.adquirir()
        return self

    def __exit__(self, tipo, valor, traza):
        self.soltar()
        return False


def centimos(eur) -> int:
    """Euros a céntimos enteros (el dinero nunca se suma en coma flotante)."""
    return int(round(float(eur) * 100))


class Libro:
    """`estado/gasto.json`: una línea por sesión con fecha, encargo e importe (en céntimos)."""

    def __init__(self, ruta):
        self.ruta = Path(ruta)

    def sesiones(self) -> list:
        datos = leer(self.ruta, {})
        lista = datos.get("sesiones") if isinstance(datos, dict) else None
        return lista if isinstance(lista, list) else []

    def anotar(self, encargo: str, eur, ahora: datetime = None) -> None:
        ahora = ahora or datetime.now()
        lista = self.sesiones()
        lista.append({"fecha": ahora.isoformat(timespec="seconds"), "encargo": encargo,
                      "centimos": centimos(eur)})
        escribir(self.ruta, {"sesiones": lista})

    def gastado_centimos(self, encargo: str = None) -> int:
        total = 0
        for sesion in self.sesiones():
            if not isinstance(sesion, dict):
                continue
            if encargo is not None and sesion.get("encargo") != encargo:
                continue
            valor = sesion.get("centimos")
            total += valor if isinstance(valor, int) else 0
        return total

    def gastado(self, encargo: str = None) -> float:
        return self.gastado_centimos(encargo) / 100.0
