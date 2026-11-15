"""AIFEC — fábrica: ayudas de las pruebas.

Monta, en una carpeta temporal, una fábrica completa (el motor y `fabrica.py` copiados tal cual),
un «sistema» de mentira (una carpeta con `core/bootstrap.php` y un `aifec` que es un guion de Python
que contesta lo que la prueba diga), puertas de mentira y un motor de mentira. Nada sale a Internet,
no se lanza ninguna IA y no hace falta AIFEC de verdad.

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
from datetime import datetime, timedelta
from pathlib import Path

PROYECTO = Path(__file__).resolve().parent.parent
if str(PROYECTO) not in sys.path:
    sys.path.insert(0, str(PROYECTO))

from motor import cola as cola_mod, nucleo, procesos  # noqa: E402

CONFIGS = {
    "temas": {
        "clase": "temas", "titulo": "Fábrica de temas de AIFEC", "carpeta_destino": "themes",
        "manifiesto": "theme.json",
        "orden_esqueleto": ["theme:create", "{slug}", "--parent=base", "--name={nombre}"],
    },
    "plugins": {
        "clase": "plugins", "titulo": "Fábrica de plugins de AIFEC", "carpeta_destino": "plugins",
        "manifiesto": "plugin.json",
        "orden_esqueleto": ["plugin:create", "{slug}", "--name={nombre}"],
    },
}

PUERTA = r'''
import json, os, sys, time
from pathlib import Path

args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
nombre = Path(__file__).stem
slug = args["--slug"]
control = Path(os.environ["PRUEBA_CONTROL"])
with open(control / "llamadas.log", "a", encoding="utf-8") as f:
    f.write(nombre + ":" + slug + "\n")
modo = "0"
for candidato in (control / (nombre + "." + slug + ".modo"), control / (nombre + ".modo")):
    if candidato.exists():
        modo = candidato.read_text().strip()
        break


def informe(ok, resumen):
    with open(args["--informe"], "w", encoding="utf-8") as f:
        json.dump({"puerta": nombre, "ok": ok, "resumen": resumen, "detalles": ["detalle de " + nombre],
                   "medidas": {"n": 1}}, f)


if modo == "lenta":
    (control / "puerta.pid").write_text(str(os.getpid()))
    time.sleep(60)
if modo == "contador":
    fichero = control / (nombre + ".fallos")
    restantes = int(fichero.read_text().strip()) if fichero.exists() else 0
    if restantes > 0:
        fichero.write_text(str(restantes - 1))
        informe(False, "no pasa: motivo-de-prueba")
        sys.exit(1)
    modo = "0"
if modo == "0":
    informe(True, "pasa")
    sys.exit(0)
if modo == "1":
    informe(False, "no pasa: motivo-de-prueba")
    sys.exit(1)
if modo == "2":
    informe(True, "falta algo opcional")
    sys.exit(2)
if modo == "sin_informe":
    sys.exit(0)
if modo == "crash":
    os._exit(7)
sys.exit(9)
'''

AIFEC = r'''
import json, os, sys
from pathlib import Path

raiz = Path(__file__).resolve().parent
control = Path(os.environ["PRUEBA_CONTROL"])
with open(raiz / "argv.log", "a", encoding="utf-8") as f:
    f.write(json.dumps(sys.argv[1:]) + "\n")
args = [a for a in sys.argv[1:] if not a.startswith("--data=")]
modo = (control / "aifec.modo").read_text().strip() if (control / "aifec.modo").exists() else "ok"
orden = args[0] if args else ""
if orden == "site:create":
    if modo == "sin_site":
        print("unknown command site:create")
        sys.exit(1)
    (raiz / "sites").mkdir(exist_ok=True)
    (raiz / "sites" / args[1]).mkdir(exist_ok=True)
    print("site created")
    sys.exit(0)
if orden in ("theme:create", "plugin:create"):
    if modo == "sin_esqueleto":
        print("unknown command " + orden)
        sys.exit(1)
    carpeta = raiz / ("themes" if orden == "theme:create" else "plugins") / args[1]
    carpeta.mkdir(parents=True, exist_ok=True)
    manifiesto = "theme.json" if orden == "theme:create" else "plugin.json"
    (carpeta / manifiesto).write_text(json.dumps({"name": "esqueleto de " + args[1]}))
    (carpeta / "esqueleto.txt").write_text("esqueleto")
    sys.exit(0)
print("orden: " + orden)
sys.exit(0)
'''

MOTOR = r'''
import json, os, subprocess, sys, time
from pathlib import Path

trabajo = Path(sys.argv[1])
control = Path(os.environ["PRUEBA_CONTROL"])
if os.environ.get("PRUEBA_HIJO"):
    (control / "hijo.pid").write_text(str(os.getpid()))
    time.sleep(60)
    sys.exit(0)
modo = (control / "motor.modo").read_text().strip() if (control / "motor.modo").exists() else "normal"
manifiesto = (control / "manifiesto.txt").read_text().strip()
with open(trabajo / "ejecuciones.txt", "a", encoding="utf-8") as f:
    f.write(modo + "\n")
if (control / "coste.txt").exists():
    print((control / "coste.txt").read_text())


def terminar():
    (trabajo / manifiesto).write_text(json.dumps({"name": "hecho por el motor de mentira"}))
    sys.exit(0)


if modo == "normal":
    (control / "marcador.txt").write_text("el motor se lanzó")
    (trabajo / "contenido.txt").write_text("trabajo")
    terminar()
if modo == "marcas":
    (control / "argv.json").write_text(json.dumps({"argv": sys.argv[1:], "cwd": os.getcwd()}))
    terminar()
if modo == "lento_corte":
    if not (trabajo / "parte1.txt").exists():
        (trabajo / "parte1.txt").write_text("primera parte")
        (control / "motor.pid").write_text(str(os.getpid()))
        time.sleep(60)
    (trabajo / "parte2.txt").write_text("segunda parte")
    terminar()
if modo == "dos_fabricas":
    (control / "motor.pid").write_text(str(os.getpid()))
    time.sleep(4)
    terminar()
if modo == "dormir":
    (control / "motor.pid").write_text(str(os.getpid()))
    subprocess.Popen([sys.executable, __file__, str(trabajo)], env=dict(os.environ, PRUEBA_HIJO="1"))
    time.sleep(60)
if modo == "intruso":
    Path(os.path.join(str(trabajo), "..", "..", "intruso.txt")).write_text("fuera")
    terminar()
if modo == "parar":
    subprocess.run([sys.executable, str(Path(sys.argv[2]) / "fabrica.py"), "parar"], stdin=subprocess.DEVNULL,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    terminar()
if modo == "falla":
    sys.exit(3)
sys.exit(8)
'''

AVISADOR = r'''
import os, sys
from pathlib import Path
with open(Path(os.environ["PRUEBA_CONTROL"]) / "avisos.txt", "a", encoding="utf-8") as f:
    f.write(sys.argv[1] + "\n")
'''

ARBOL = r'''
import os, subprocess, sys, time
from pathlib import Path

carpeta = Path(sys.argv[1])
nivel = int(sys.argv[2])
(carpeta / ("nivel%d.pid" % nivel)).write_text(str(os.getpid()))
if nivel < 3:
    subprocess.Popen([sys.executable, __file__, str(carpeta), str(nivel + 1)])
time.sleep(60)
'''


class Reloj:
    """Un reloj que se mueve cuando la prueba quiere."""

    def __init__(self, instante: datetime = None):
        self.instante = instante or datetime(2026, 11, 13, 10, 0, 0)

    def __call__(self) -> datetime:
        return self.instante

    def avanzar(self, **kwargs):
        self.instante = self.instante + timedelta(**kwargs)


def esperar(condicion, segundos: float = 25.0, cada: float = 0.1) -> bool:
    limite = time.time() + segundos
    while time.time() < limite:
        if condicion():
            return True
        time.sleep(cada)
    return condicion()


def _borrar(ruta: Path) -> None:
    for _ in range(10):
        shutil.rmtree(str(ruta), ignore_errors=True)
        if not ruta.exists():
            return
        time.sleep(0.2)


class Base(unittest.TestCase):
    """Cada prueba tiene su carpeta temporal y su carpeta de control (fuera de la fábrica, para que lo
    que escriban los programas de mentira no cuente como «escribir fuera de la salida»)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fabrica-prueba-")).resolve()
        self.addCleanup(_borrar, self.tmp)
        self.control = self.tmp / "control"
        self.control.mkdir()
        previo = os.environ.get("PRUEBA_CONTROL")
        os.environ["PRUEBA_CONTROL"] = str(self.control)
        self.addCleanup(lambda: os.environ.pop("PRUEBA_CONTROL", None) if previo is None
                        else os.environ.__setitem__("PRUEBA_CONTROL", previo))
        self.addCleanup(self._matar_huerfanos)
        self.reloj = Reloj()

    def _matar_huerfanos(self):
        for pid in self.control.glob("*.pid"):
            try:
                procesos.matar_arbol(int(pid.read_text().strip()))
            except (OSError, ValueError):
                pass

    # ---- montaje ---------------------------------------------------------------------------

    def montar(self, clase: str = "temas", encargos=("uno",), puertas=("uno", "dos"), plan=None,
               motor="simulado", config=None):
        """Monta la fábrica y devuelve su carpeta. `motor` puede ser `simulado`, `manual` u `orden`."""
        raiz = self.tmp / "fabrica"
        shutil.copytree(str(PROYECTO / "motor"), str(raiz / "motor"), ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(str(PROYECTO / "fabrica.py"), str(raiz / "fabrica.py"))
        shutil.copytree(str(PROYECTO / "plantillas"), str(raiz / "plantillas"))
        datos_config = dict(config or CONFIGS[clase])
        (raiz / "fabrica.json").write_text(json.dumps(datos_config), encoding="utf-8")
        manifiesto = datos_config["manifiesto"]
        (self.control / "manifiesto.txt").write_text(manifiesto)
        # El «sistema» de mentira.
        sistema = self.tmp / "sistema"
        (sistema / "core").mkdir(parents=True)
        (sistema / "core" / "bootstrap.php").write_text("<?php\n")
        (sistema / "aifec").write_text(AIFEC, encoding="utf-8")
        (sistema / "VERSION").write_text("1.0.0")
        # Un trabajo ya hecho, para el motor simulado.
        origen = self.tmp / "origen"
        origen.mkdir()
        (origen / manifiesto).write_text(json.dumps({"name": "Hecho de mentira", "description": "una prueba"}))
        (origen / "contenido.txt").write_text("contenido")
        # Puertas y motor de mentira.
        (raiz / "puertas").mkdir()
        for nombre in puertas:
            (raiz / "puertas" / (nombre + ".py")).write_text(PUERTA, encoding="utf-8")
        (self.control / "motor.py").write_text(MOTOR, encoding="utf-8")
        (self.control / "avisador.py").write_text(AVISADOR, encoding="utf-8")
        if motor == "simulado":
            datos_motor = {"tipo": "simulado", "origen": "../origen"}
        elif motor == "manual":
            datos_motor = {"tipo": "manual"}
        else:
            datos_motor = {"tipo": "orden", "minutos": 1, "orden": [
                sys.executable, str(self.control / "motor.py"), "{trabajo}", "{fabrica}"]}
        datos_plan = {"aifec": "../sistema", "php": sys.executable, "motor": datos_motor,
                      "puertas": list(puertas), "por_dia": 3, "intentos": 3, "puertas_minutos": 1}
        if motor == "orden":
            datos_plan["gasto"] = {"tope_eur": 100, "por_sesion_eur": 0}
        datos_plan.update(plan or {})
        (raiz / "plan.json").write_text(json.dumps(datos_plan), encoding="utf-8")
        (raiz / "cola.json").write_text(json.dumps([
            {"slug": slug, "nombre": "Encargo " + slug, "sector": "pruebas", "idea": "idea de " + slug}
            for slug in encargos]), encoding="utf-8")
        self.raiz = raiz
        return raiz

    def abrir(self, estricto: bool = True):
        return nucleo.abrir(self.raiz, estricto=estricto, reloj=self.reloj)

    def modo(self, nombre: str, valor: str) -> None:
        (self.control / (nombre + ".modo")).write_text(valor)

    def estado_de(self, slug: str) -> str:
        return cola_mod.Cola(nucleo.estado.Rutas(self.raiz)).estado(slug)["estado"]

    # ---- la orden por línea de órdenes ------------------------------------------------------

    def cli(self, *args, entorno=None, tiempo=120):
        env = dict(os.environ)
        env.update(entorno or {})
        proceso = subprocess.run([sys.executable, str(self.raiz / "fabrica.py")] + [str(a) for a in args],
                                 cwd=str(self.tmp), stdin=subprocess.DEVNULL, capture_output=True,
                                 timeout=tiempo, env=env, encoding="utf-8", errors="replace")
        return proceso.returncode, proceso.stdout + proceso.stderr

    def cli_en_segundo_plano(self, *args):
        """Lanza la fábrica sin esperarla. Devuelve el proceso (hay que esperarlo o matarlo)."""
        registro = open(self.tmp / ("segundo-plano-%d.log" % time.time_ns()), "wb")
        self.addCleanup(registro.close)
        proceso = subprocess.Popen([sys.executable, str(self.raiz / "fabrica.py")] + [str(a) for a in args],
                                   cwd=str(self.tmp), stdin=subprocess.DEVNULL, stdout=registro,
                                   stderr=subprocess.STDOUT)
        self.addCleanup(lambda: proceso.poll() is None and procesos.matar_arbol(proceso.pid))
        return proceso
