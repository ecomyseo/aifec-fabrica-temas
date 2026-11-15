"""AIFEC — fábrica: pruebas del estado en disco, el cerrojo y el libro de gasto.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

from ayudas import Base, esperar
from motor import estado, procesos


def _proceso_ajeno():
    """Un programa que no es Python y dura un rato (para un PID «reutilizado»)."""
    if os.name == "nt":
        orden = ["ping", "-n", "40", "127.0.0.1"]
        banderas = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        orden = ["sleep", "40"]
        banderas = 0
    return subprocess.Popen(orden, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, creationflags=banderas)


def _proceso_python():
    return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(40)"], stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


class PruebasEstado(Base):
    def test_leer_devuelve_el_defecto_si_no_existe(self):
        self.assertEqual(estado.leer(self.tmp / "no-existe.json", {"a": 1}), {"a": 1})

    def test_leer_devuelve_el_defecto_si_esta_a_medias(self):
        ruta = self.tmp / "roto.json"
        ruta.write_text('{"a": ', encoding="utf-8")
        self.assertEqual(estado.leer(ruta, []), [])

    def test_escribir_y_leer_conservan_tildes_y_enes(self):
        ruta = self.tmp / "d" / "x.json"
        estado.escribir(ruta, {"nombre": "Ñandú con acción & «comillas»"})
        self.assertEqual(estado.leer(ruta)["nombre"], "Ñandú con acción & «comillas»")

    def test_un_corte_a_mitad_de_escribir_no_deja_un_json_a_medias(self):
        ruta = self.tmp / "estado.json"
        estado.escribir(ruta, {"version": 1})
        with mock.patch.object(estado.os, "replace", side_effect=OSError("corte simulado")):
            with self.assertRaises(OSError):
                estado.escribir(ruta, {"version": 2})
        self.assertEqual(estado.leer(ruta), {"version": 1})
        self.assertEqual([p.name for p in self.tmp.iterdir() if p.name.startswith(".estado")], [])

    def test_apuntar_escribe_una_linea_con_fecha(self):
        ruta = self.tmp / "fabrica.log"
        estado.apuntar(ruta, "hola", datetime(2026, 11, 13, 9, 5, 7))
        self.assertEqual(ruta.read_text(encoding="utf-8"), "2026-11-13 09:05:07 hola\n")

    def test_el_libro_suma_en_centimos_sin_errores_de_coma_flotante(self):
        libro = estado.Libro(self.tmp / "gasto.json")
        libro.anotar("a", 0.1, self.reloj())
        libro.anotar("b", 0.2, self.reloj())
        self.assertEqual(libro.gastado_centimos(), 30)
        self.assertEqual(libro.gastado(), 0.3)
        self.assertEqual(libro.gastado("a"), 0.1)
        self.assertEqual(len(libro.sesiones()), 2)
        self.assertEqual(libro.sesiones()[0]["encargo"], "a")


class PruebasCerrojo(Base):
    def test_se_toma_si_esta_libre_y_apunta_el_pid(self):
        ruta = self.tmp / "estado" / "fabrica.lock"
        cerrojo = estado.Cerrojo(ruta)
        self.assertTrue(cerrojo.adquirir())
        self.assertEqual(estado.leer(ruta)["pid"], os.getpid())
        cerrojo.soltar()
        self.assertFalse(ruta.exists())

    def test_el_cerrojo_de_un_proceso_muerto_se_toma(self):
        ruta = self.tmp / "fabrica.lock"
        muerto = _proceso_python()
        muerto.kill()
        muerto.wait()
        estado.escribir(ruta, {"pid": muerto.pid, "hora": "ayer"})
        cerrojo = estado.Cerrojo(ruta)
        self.assertTrue(cerrojo.adquirir())
        self.assertEqual(estado.leer(ruta)["pid"], os.getpid())
        cerrojo.soltar()

    def test_el_cerrojo_de_un_python_vivo_esta_ocupado(self):
        ruta = self.tmp / "fabrica.lock"
        vivo = _proceso_python()
        self.addCleanup(lambda: (vivo.kill(), vivo.wait()))
        estado.escribir(ruta, {"pid": vivo.pid, "hora": "ahora"})
        cerrojo = estado.Cerrojo(ruta)
        self.assertFalse(cerrojo.adquirir())
        self.assertEqual(estado.leer(ruta)["pid"], vivo.pid, "no se debe tocar el cerrojo de otro")
        cerrojo.soltar()
        self.assertTrue(ruta.exists(), "soltar sin haberlo tomado no debe borrar el de otro")

    def test_un_pid_reutilizado_por_otro_programa_no_cuenta_como_fabrica(self):
        ruta = self.tmp / "fabrica.lock"
        ajeno = _proceso_ajeno()
        self.addCleanup(lambda: (ajeno.kill(), ajeno.wait()))
        self.assertTrue(esperar(lambda: procesos.vivo(ajeno.pid), 5))
        estado.escribir(ruta, {"pid": ajeno.pid, "hora": "ayer"})
        cerrojo = estado.Cerrojo(ruta)
        self.assertTrue(cerrojo.adquirir(), "un PID que ahora es de otro programa no bloquea a la fábrica")
        cerrojo.soltar()

    def test_el_cerrojo_se_suelta_siempre_aunque_haya_una_excepcion(self):
        ruta = self.tmp / "fabrica.lock"
        with self.assertRaises(RuntimeError):
            with estado.Cerrojo(ruta) as cerrojo:
                self.assertTrue(cerrojo.tomado)
                raise RuntimeError("fallo")
        self.assertFalse(ruta.exists())

    def test_un_cerrojo_ilegible_se_trata_como_abandonado(self):
        ruta = self.tmp / "fabrica.lock"
        ruta.write_text("basura", encoding="utf-8")
        cerrojo = estado.Cerrojo(ruta)
        self.assertTrue(cerrojo.adquirir())
        cerrojo.soltar()


if __name__ == "__main__":
    unittest.main()
