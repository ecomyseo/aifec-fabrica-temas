"""AIFEC — fábrica: pruebas de `motor/procesos.py` (lanzar con límite y parar un árbol entero).

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

from ayudas import ARBOL, Base, esperar
from motor import procesos
from test_estado import _proceso_ajeno, _proceso_python


class PruebasProcesos(Base):
    def _script(self, nombre: str, texto: str):
        ruta = self.tmp / nombre
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def test_lanzar_devuelve_el_codigo_de_salida(self):
        for codigo in (0, 3):
            script = self._script("c%d.py" % codigo, "import sys; sys.exit(%d)" % codigo)
            resultado = procesos.lanzar([sys.executable, str(script)], self.tmp, self.tmp / "s.log", 1)
            self.assertEqual(resultado, codigo)

    def test_lanzar_guarda_la_salida_en_el_fichero(self):
        script = self._script("hola.py", "print('hola desde el hijo')")
        procesos.lanzar([sys.executable, str(script)], self.tmp, self.tmp / "dir" / "s.log", 1)
        self.assertIn("hola desde el hijo", (self.tmp / "dir" / "s.log").read_text(encoding="utf-8"))

    def test_la_entrada_del_hijo_es_dev_null(self):
        script = self._script("lee.py", "import sys; sys.exit(0 if sys.stdin.read() == '' else 5)")
        self.assertEqual(procesos.lanzar([sys.executable, str(script)], self.tmp, self.tmp / "s.log", 1), 0)

    def test_un_programa_que_no_existe_da_127_y_lo_apunta(self):
        resultado = procesos.lanzar(["programa-que-no-existe-xyz"], self.tmp, self.tmp / "s.log", 1)
        self.assertEqual(resultado, 127)
        self.assertIn("No se pudo lanzar", (self.tmp / "s.log").read_text(encoding="utf-8"))

    def test_el_tiempo_agotado_mata_el_proceso(self):
        script = self._script("duerme.py", "import os, time\n(open(os.environ['PRUEBA_CONTROL'] + '/d.pid', 'w')"
                                           ".write(str(os.getpid())))\ntime.sleep(60)")
        resultado = procesos.lanzar([sys.executable, str(script)], self.tmp, self.tmp / "s.log", 0.04)
        self.assertEqual(resultado, procesos.TIEMPO_AGOTADO)
        pid = int((self.control / "d.pid").read_text())
        self.assertTrue(esperar(lambda: not procesos.vivo(pid), 5), "el proceso sigue vivo tras el tiempo")

    def _pids_del_arbol(self, carpeta):
        self.assertTrue(esperar(lambda: len(list(carpeta.glob("nivel*.pid"))) == 3, 25),
                        "no arrancaron los tres niveles")
        return [int(carpeta.joinpath("nivel%d.pid" % n).read_text()) for n in (1, 2, 3)]

    def test_un_arbol_de_tres_niveles_muere_entero(self):
        carpeta = self.tmp / "arbol"
        carpeta.mkdir()
        raiz = self._script("arbol.py", ARBOL)
        proceso = subprocess.Popen([sys.executable, str(raiz), str(carpeta), "1"], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: proceso.poll() is None and proceso.kill())
        pids = self._pids_del_arbol(carpeta)
        self.assertTrue(all(procesos.vivo(p) for p in pids))
        procesos.matar_arbol(proceso.pid)
        proceso.wait(timeout=10)
        for pid in pids:
            self.assertTrue(esperar(lambda: not procesos.vivo(pid), 5), "queda vivo el proceso %d" % pid)

    def test_lanzar_con_tiempo_agotado_no_deja_ningun_hijo_vivo(self):
        carpeta = self.tmp / "arbol2"
        carpeta.mkdir()
        raiz = self._script("arbol.py", ARBOL)
        resultado = procesos.lanzar([sys.executable, str(raiz), str(carpeta), "1"], self.tmp,
                                    self.tmp / "s.log", 0.15)
        self.assertEqual(resultado, procesos.TIEMPO_AGOTADO)
        for pid in self._pids_del_arbol(carpeta):
            self.assertTrue(esperar(lambda: not procesos.vivo(pid), 5), "queda vivo el proceso %d" % pid)

    def test_descendientes_encuentra_a_los_hijos(self):
        carpeta = self.tmp / "arbol3"
        carpeta.mkdir()
        raiz = self._script("arbol.py", ARBOL)
        proceso = subprocess.Popen([sys.executable, str(raiz), str(carpeta), "1"], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(lambda: procesos.matar_arbol(proceso.pid))
        pids = self._pids_del_arbol(carpeta)
        self.assertTrue(set(pids[1:]) <= set(procesos.descendientes(proceso.pid)))

    def test_vivo_de_un_pid_que_no_existe_es_falso(self):
        muerto = _proceso_python()
        muerto.kill()
        muerto.wait()
        self.assertFalse(procesos.vivo(muerto.pid))
        self.assertFalse(procesos.vivo(0))
        self.assertFalse(procesos.vivo("no es un pid"))

    def test_vivo_reconoce_a_un_python(self):
        self.assertTrue(procesos.vivo(os.getpid()))
        self.assertTrue(procesos.vivo(os.getpid(), "python"))

    def test_vivo_distingue_un_pid_reutilizado_por_otro_programa(self):
        ajeno = _proceso_ajeno()
        self.addCleanup(lambda: (ajeno.kill(), ajeno.wait()))
        self.assertTrue(esperar(lambda: procesos.vivo(ajeno.pid), 5))
        self.assertFalse(procesos.vivo(ajeno.pid, "python"), "un programa que no es Python no es una fábrica")


if __name__ == "__main__":
    unittest.main()
