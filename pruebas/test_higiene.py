"""AIFEC — fábrica: pruebas de higiene del código del motor.

El motor y `fabrica.py` son idénticos en la fábrica de temas y en la de plugins, así que no pueden
saber qué fabrican, ni llevar rutas de esta máquina, ni usar programas que no existan en los tres
sistemas operativos.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import ast
import json
import re
import unittest

from ayudas import PROYECTO
from motor import plan as plan_mod

FICHEROS = sorted((PROYECTO / "motor").glob("*.py")) + [PROYECTO / "fabrica.py"]


def _lineas_con(patron, ignorar_cadenas_de_prueba=False):
    encontradas = []
    expresion = re.compile(patron)
    for ruta in FICHEROS:
        for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
            if expresion.search(linea):
                encontradas.append("%s:%d: %s" % (ruta.name, numero, linea.strip()))
    return encontradas


class PruebasHigiene(unittest.TestCase):
    def test_hay_motor_y_fabrica(self):
        self.assertGreaterEqual(len(FICHEROS), 10)

    def test_el_motor_no_sabe_si_fabrica_temas_o_plugins(self):
        self.assertEqual(_lineas_con(r"(?i)tema|plugin|theme"), [])

    def test_ningun_programa_que_no_exista_en_los_tres_sistemas(self):
        self.assertEqual(_lineas_con(r"(?i)wmic|tasklist|taskkill"), [])

    def test_ninguna_ruta_absoluta_de_esta_maquina_ni_nombre_de_usuario(self):
        patron = r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/Users/|/home/|Usuario|dev-tools|modulos IA"
        self.assertEqual(_lineas_con(patron), [])

    def test_todo_subprocess_lleva_la_entrada_vacia(self):
        # El único sitio donde se lanzan procesos es procesos.lanzar.
        fuentes = [l for l in _lineas_con(r"subprocess\.(Popen|run|call|check_output)")]
        self.assertTrue(all(l.startswith("procesos.py:") for l in fuentes), fuentes)
        self.assertIn("stdin", (PROYECTO / "motor" / "procesos.py").read_text(encoding="utf-8"))

    def test_ninguna_dependencia_de_fuera_de_la_biblioteca_estandar(self):
        permitidos = set(__import__("sys").stdlib_module_names) | {"motor", "ctypes"}
        for ruta in FICHEROS:
            arbol = ast.parse(ruta.read_text(encoding="utf-8"))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    modulos = [a.name.split(".")[0] for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0 and nodo.module:
                    modulos = [nodo.module.split(".")[0]]
                else:
                    continue
                for modulo in modulos:
                    self.assertIn(modulo, permitidos, "%s importa %s" % (ruta.name, modulo))

    def test_cada_fichero_empieza_por_su_cabecera(self):
        for ruta in FICHEROS:
            texto = ruta.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith('"""AIFEC — '), ruta.name)
            self.assertIn("@author  Ecom Experts <ecomyseo@gmail.com>", texto, ruta.name)
            self.assertIn("@license Ver LICENSE.md", texto, ruta.name)

    def test_los_ficheros_son_utf8_sin_bom_y_con_saltos_lf(self):
        for ruta in FICHEROS:
            crudo = ruta.read_bytes()
            self.assertFalse(crudo.startswith(b"\xef\xbb\xbf"), ruta.name)
            self.assertNotIn(b"\r\n", crudo, ruta.name)

    def test_la_fabrica_de_temas_trae_su_configuracion_completa(self):
        config = plan_mod.cargar_config(PROYECTO)
        self.assertEqual(config["clase"], "temas")
        self.assertEqual(config["carpeta_destino"], "themes")
        self.assertEqual(config["manifiesto"], "theme.json")
        self.assertEqual(config["orden_esqueleto"], ["theme:create", "{slug}", "--parent=base", "--name={nombre}"])
        self.assertEqual(config["puertas"], ["validador", "estructura", "peso", "movil", "traducciones",
                                              "limpieza", "capturas"])

    def test_los_ejemplos_son_json_validos_y_el_plan_de_ejemplo_no_lleva_rutas_de_esta_maquina(self):
        for nombre in ("plan.ejemplo.json", "cola.ejemplo.json", "fabrica.json"):
            json.loads((PROYECTO / nombre).read_text(encoding="utf-8"))
        ejemplo = (PROYECTO / "plan.ejemplo.json").read_text(encoding="utf-8")
        self.assertNotRegex(ejemplo, r"[A-Za-z]:[\\/]")
        cola = json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cola), 3)

    def test_gitignore_deja_fuera_lo_que_no_se_publica(self):
        lineas = (PROYECTO / ".gitignore").read_text(encoding="utf-8").split()
        for esperado in ("plan.json", "cola.json", "estado/", "salida/", "escaparate/", "__pycache__/"):
            self.assertIn(esperado, lineas)


if __name__ == "__main__":
    unittest.main()
