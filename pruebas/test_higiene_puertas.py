"""AIFEC — fábrica de temas: pruebas de higiene del código de las puertas, del skill y de las pruebas.

Las reglas de las fábricas (contratos/07-fabricas.md § 2) valen también aquí: solo biblioteca estándar, ni rutas de
esta máquina ni programas que no existan en los tres sistemas, todo `subprocess` con la entrada vacía y su tiempo
límite (se hace a través de `motor.procesos`), UTF-8 sin BOM con saltos LF, y cada fichero con su cabecera.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import ast
import re
import sys
import unittest

from ayudas_puertas import PROYECTO

PUERTAS = PROYECTO / "puertas"
SKILL = PROYECTO / "skill"
PYTHON = sorted(PUERTAS.glob("*.py")) + sorted(SKILL.glob("*.py")) + sorted((PROYECTO / "pruebas").glob("*puerta*.py")) \
    + sorted((PROYECTO / "pruebas").glob("test_esqueleto_y_skill.py")) + sorted((PROYECTO / "pruebas").glob("test_de_punta_a_punta.py")) \

PYTHON = sorted(set(PYTHON + [PROYECTO / "pruebas" / "ayudas_puertas.py"]))
PHP = sorted(PUERTAS.glob("*.php")) + sorted((PROYECTO / "plantillas" / "esqueleto").rglob("*.php"))
TODOS = PYTHON + PHP + sorted(SKILL.rglob("*.md")) + sorted((PROYECTO / "plantillas" / "esqueleto").rglob("*"))
LA_FABRICA = [p for p in TODOS if p.is_file()]


class PruebasHigieneDeLasPuertas(unittest.TestCase):
    def test_hay_las_siete_puertas_y_sus_apoyos(self):
        for nombre in ("validador", "estructura", "peso", "movil", "traducciones", "limpieza", "capturas"):
            self.assertTrue((PUERTAS / (nombre + ".py")).is_file(), nombre)
        for apoyo in ("_comun.py", "_html.py", "_css.py", "_pintar.php", "_sembrar.php"):
            self.assertTrue((PUERTAS / apoyo).is_file(), apoyo)

    def test_las_puertas_de_fabrica_json_son_exactamente_las_que_hay(self):
        import json
        puertas = json.loads((PROYECTO / "fabrica.json").read_text(encoding="utf-8"))["puertas"]
        for puerta in puertas:
            self.assertTrue((PUERTAS / (puerta + ".py")).is_file(), puerta)

    def test_cada_fichero_python_empieza_por_su_cabecera(self):
        for ruta in PYTHON:
            texto = ruta.read_text(encoding="utf-8")
            self.assertTrue(texto.startswith('"""AIFEC — '), ruta.name)
            self.assertIn("@author  Ecom Experts <ecomyseo@gmail.com>", texto, ruta.name)
            self.assertIn("@license Ver LICENSE.md", texto, ruta.name)

    def test_todos_los_ficheros_son_utf8_sin_bom_y_con_saltos_lf(self):
        for ruta in LA_FABRICA:
            crudo = ruta.read_bytes()
            self.assertFalse(crudo.startswith(b"\xef\xbb\xbf"), ruta.name)
            self.assertNotIn(b"\r\n", crudo, ruta.name)
            crudo.decode("utf-8")

    def test_los_php_empiezan_por_php_y_su_comentario_sin_linea_en_blanco(self):
        for ruta in PHP:
            self.assertTrue(ruta.read_bytes().startswith(b"<?php\n/**"), ruta.name)

    def test_los_php_declaran_su_autor_y_su_licencia(self):
        for ruta in sorted(PUERTAS.glob("*.php")):
            texto = ruta.read_text(encoding="utf-8")
            self.assertIn("@author  Ecom Experts <ecomyseo@gmail.com>", texto, ruta.name)
            self.assertIn("@license Ver LICENSE.md", texto, ruta.name)

    def test_solo_biblioteca_estandar_y_la_unica_excepcion_es_playwright_dentro_de_capturas(self):
        permitidos = set(sys.stdlib_module_names) | {"motor", "_comun", "_html", "_css", "ayudas_puertas", "esqueleto", "estructura", "peso", "movil", "capturas",
                                                      "playwright"}
        for ruta in PUERTAS.glob("*.py"):
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
                    if modulo == "playwright":
                        self.assertEqual(ruta.name, "capturas.py")

    def test_playwright_solo_se_importa_dentro_de_una_funcion(self):
        arbol = ast.parse((PUERTAS / "capturas.py").read_text(encoding="utf-8"))
        for nodo in arbol.body:
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                nombres = [a.name for a in nodo.names] + ([nodo.module] if isinstance(nodo, ast.ImportFrom) and nodo.module else [])
                self.assertFalse(any("playwright" in (n or "") for n in nombres))

    def test_ninguna_ruta_absoluta_de_esta_maquina_ni_nombre_de_usuario(self):
        patron = re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:[\\/]|/Users/|/home/|Usuario|dev-tools|modulos IA")
        excepciones = {"ayudas_puertas.py", "test_higiene_puertas.py"}    # buscan PHP en unas herramientas conocidas / contienen el patrón
        for ruta in PYTHON + PHP:
            if ruta.name in excepciones:
                continue
            for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(patron.search(linea), "%s:%d: %s" % (ruta.name, numero, linea.strip()))

    def test_ningun_programa_que_no_exista_en_los_tres_sistemas(self):
        patron = re.compile(r"\bwmic\b|\btasklist\b|\btaskkill\b|os\.system|shell=True")
        for ruta in PYTHON:
            if ruta.name == "test_higiene_puertas.py":
                continue
            for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                self.assertIsNone(patron.search(linea), "%s:%d: %s" % (ruta.name, numero, linea.strip()))

    def test_los_procesos_de_las_puertas_se_lanzan_con_la_entrada_vacia(self):
        for ruta in PUERTAS.glob("*.py"):
            for numero, linea in enumerate(ruta.read_text(encoding="utf-8").splitlines(), 1):
                if re.search(r"subprocess\.(Popen|run|call|check_output)\(", linea):
                    self.assertEqual(ruta.name, "capturas.py", "%s:%d: usa procesos.lanzar" % (ruta.name, numero))
        capturas = (PUERTAS / "capturas.py").read_text(encoding="utf-8")
        self.assertIn('"stdin": subprocess.DEVNULL', capturas)
        self.assertIn("CREATE_NO_WINDOW", capturas)
        self.assertIn("matar_arbol", capturas)

    def test_cada_fichero_python_compila(self):
        for ruta in PYTHON:
            compile(ruta.read_text(encoding="utf-8"), str(ruta), "exec")

    def test_los_ficheros_de_las_puertas_no_escriben_nunca_en_el_candidato(self):
        # lo que escribe una puerta va a `--informe` o a `estado/`: ninguna abre un fichero del candidato para escribir
        patron = re.compile(r"candidato\s*/[^\n]*\.(write_text|write_bytes|unlink|touch)|\(ctx\.candidato[^\n]*(rmtree|unlink|write)")
        for ruta in PUERTAS.glob("*.py"):
            self.assertIsNone(patron.search(ruta.read_text(encoding="utf-8")), ruta.name)


if __name__ == "__main__":
    unittest.main()
