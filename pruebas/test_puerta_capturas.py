"""AIFEC — fábrica de temas: pruebas de la puerta «capturas» (opcional).

Sin Playwright, o con `capturas.activas` a falso, sale con 2 («no aplica»). Lo que arranca (un servidor) se para y
deja el puerto libre. La captura de verdad solo se prueba si hay Playwright, hay sistema y la variable
`AIFEC_CAPTURAS=1`: abre un navegador y deja la máquina cargada, así que no se lanza por iniciativa propia.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
import unittest

from ayudas_puertas import BaseTemas, FabricaReal, sistema_disponible

import capturas  # noqa: E402


def _hay_playwright() -> bool:
    return capturas.playwright_disponible()


class PruebasPuertaCapturas(BaseTemas):
    def test_con_las_capturas_apagadas_sale_con_dos_y_lo_dice(self):
        tema = self.tema()
        codigo, informe, texto = self.lanzar("capturas", tema, plan={"capturas": {"activas": False}})
        self.aceptar(codigo, informe, texto, 2)
        self.assertIn("capturas.activas", informe["resumen"])
        self.assertTrue(informe["ok"])

    def test_sin_el_bloque_de_capturas_en_el_plan_tambien_sale_con_dos(self):
        tema = self.tema()
        self.plan.write_text('{"php": "php"}', encoding="utf-8")
        informe = self.tmp / "informe.json"
        proceso = subprocess.run([sys.executable, str(capturas.__file__), "--slug", tema.name, "--candidato", str(tema), "--banco", str(self.banco),
                                  "--plan", str(self.plan), "--informe", str(informe)], stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        self.assertEqual(proceso.returncode, 2)

    def test_sin_playwright_sale_con_dos_aunque_esten_activas(self):
        tema = self.tema()
        falso = self.tmp / "falso" / "playwright"
        falso.mkdir(parents=True)
        (falso / "__init__.py").write_text("raise ImportError('Playwright no está instalado (prueba)')\n", encoding="utf-8")
        entorno = {"PYTHONPATH": str(falso.parent)}
        codigo, informe, texto = self.lanzar("capturas", tema, plan={"capturas": {"activas": True}}, entorno=entorno)
        self.aceptar(codigo, informe, texto, 2)
        self.assertIn("Playwright no está instalado", informe["resumen"])

    def test_playwright_solo_se_importa_dentro_de_la_puerta_y_no_al_cargarla(self):
        antes = "playwright" in sys.modules
        import importlib
        importlib.reload(capturas)
        self.assertEqual("playwright" in sys.modules, antes)

    def test_un_puerto_libre_se_pide_al_sistema_y_no_esta_abierto(self):
        puerto = capturas.puerto_libre()
        self.assertGreater(puerto, 1023)
        self.assertFalse(capturas.puerto_abierto(puerto))

    def test_parar_el_servidor_lo_mata_y_deja_el_puerto_libre(self):
        puerto = capturas.puerto_libre()
        registro = open(self.tmp / "servidor.log", "wb")
        proceso = subprocess.Popen([sys.executable, "-m", "http.server", str(puerto), "--bind", "127.0.0.1"], stdin=subprocess.DEVNULL,
                                   stdout=registro, stderr=subprocess.STDOUT, cwd=str(self.tmp))
        self.addCleanup(lambda: proceso.poll() is None and proceso.kill())
        limite = time.time() + 20
        while time.time() < limite and not capturas.puerto_abierto(puerto):
            time.sleep(0.1)
        self.assertTrue(capturas.puerto_abierto(puerto), "el servidor de pega no arrancó")
        self.assertTrue(capturas.parar_servidor(proceso, registro, puerto))
        self.assertIsNotNone(proceso.poll(), "el proceso sigue vivo")
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", puerto), timeout=0.5)

    def test_parar_un_servidor_que_nunca_arranco_no_falla(self):
        self.assertTrue(capturas.parar_servidor(None, None, capturas.puerto_libre()))


@unittest.skipUnless(os.environ.get("AIFEC_CAPTURAS") == "1" and _hay_playwright() and sistema_disponible(),
                     "captura de verdad: hace falta AIFEC_CAPTURAS=1, Playwright y el sistema")
class PruebaCapturaDeVerdad(unittest.TestCase):
    def test_captura_las_paginas_y_deja_el_puerto_libre(self):
        fab = FabricaReal()
        self.addCleanup(fab.borrar)
        fab.preparar_banco()
        import json
        from ayudas_puertas import esqueleto_mod
        destino = fab.raiz / "salida" / "esq-capturas"
        esqueleto_mod.crear("esq-capturas", "Esqueleto de capturas", destino)
        fab.escribir_plan({"capturas": {"activas": True}})
        informe = fab.raiz / "informe.json"
        proceso = subprocess.run([sys.executable, str(fab.raiz / "puertas" / "capturas.py"), "--slug", "esq-capturas", "--candidato", str(destino),
                                  "--banco", str(fab.banco), "--plan", str(fab.raiz / "plan.json"), "--informe", str(informe)],
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=900, encoding="utf-8", errors="replace")
        datos = json.loads(informe.read_text(encoding="utf-8"))
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        self.assertTrue(datos["medidas"]["puerto_libre"])
        self.assertFalse(capturas.puerto_abierto(datos["medidas"]["puerto"]))
        self.assertFalse(datos["medidas"]["servidor_vivo"])
        from motor import procesos
        self.assertFalse(procesos.vivo(datos["medidas"]["servidor_pid"]), "el servidor sigue vivo")
        self.assertGreaterEqual(len(list((fab.raiz / "escaparate" / "esq-capturas").glob("*.png"))), 8)


if __name__ == "__main__":
    unittest.main()
