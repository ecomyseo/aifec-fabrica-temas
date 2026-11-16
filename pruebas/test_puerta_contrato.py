"""AIFEC — fábrica de temas: pruebas de la puerta «contrato» (las pruebas de temas del propio sistema).

Primero con un «sistema» de mentira: un `tests/run.php` escrito en Python que contesta lo que la prueba diga, para
comprobar cómo lee la puerta el veredicto del lanzador sin necesitar nada. Después, «con sistema» (se saltan solas si
`AIFEC_RUTA` no apunta a una instalación o no hay un PHP con SQLite): el esqueleto pasa, y el mismo tema con una
imagen sin medidas o con el texto estrechado no pasa y dice por qué.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest

import ayudas_puertas as ap
from ayudas_puertas import BaseTemas, FabricaReal, montar_sistema_de_mentira, sistema_disponible

PRUEBAS = ("tests/Themes/AriaTest.php", "tests/Themes/ReadingColumnTest.php", "tests/Themes/InlineCssTest.php")

LANZADOR_DE_MENTIRA = r'''
import sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")
raiz = Path(__file__).resolve().parent.parent
modo = (raiz / "modo.txt").read_text().strip() if (raiz / "modo.txt").exists() else "ok"
with open(raiz / "llamadas.log", "a", encoding="utf-8") as f:
    f.write("run " + " ".join(sys.argv[1:]) + "\n")
temas = sorted(p.name for p in (raiz / "themes").iterdir() if p.is_dir())
tema = temas[0] if temas else "ninguno"
if modo == "ok":
    print("PRUEBAS: 14 OK, 0 FALLAN (561 comprobaciones, 3 ficheros, 90 ms)")
    sys.exit(0)
if modo == "imagen":
    print("FALLA tests/Themes/AriaTest.php · ninguna plantilla de la tienda escribe una imagen sin width y height")
    print("  plantillas con una imagen sin ancho y alto")
    print("  themes/%s/templates/partials/header.php · <img src=\"logo.png\" alt=\"\">" % tema)
    print("PRUEBAS: 13 OK, 1 FALLAN (540 comprobaciones, 3 ficheros, 90 ms)")
    sys.exit(1)
if modo == "ancho":
    print("FALLA tests/Themes/ReadingColumnTest.php · en cada tema el texto no tiene un ancho máximo propio")
    print("  %s: .af-prose a todo el ancho" % tema)
    print("PRUEBAS: 13 OK, 1 FALLAN (540 comprobaciones, 3 ficheros, 90 ms)")
    sys.exit(1)
if modo == "ajeno":
    print("FALLA tests/Themes/ReadingColumnTest.php · en cada tema el texto no tiene un ancho máximo propio")
    print("  otro-tema: .af-prose a todo el ancho")
    print("PRUEBAS: 13 OK, 1 FALLAN (540 comprobaciones, 3 ficheros, 90 ms)")
    sys.exit(1)
if modo == "cortado":
    print("PHP Fatal error:  Uncaught Error: algo se rompió al arrancar")
    sys.exit(255)
if modo == "miente":
    # código 0 con un fallo escrito: no se da por bueno
    print("FALLA tests/Themes/AriaTest.php · una prueba")
    print("  themes/%s/templates/layout.php · algo" % tema)
    print("PRUEBAS: 13 OK, 1 FALLAN (540 comprobaciones, 3 ficheros, 90 ms)")
    sys.exit(0)
sys.exit(0)
'''


class PruebasConUnLanzadorDeMentira(BaseTemas):
    def lanzar(self, puerta, tema, **kwargs):
        # el lanzador de mentira es un guion de Python: se lanza con el Python de la prueba en vez de con PHP
        kwargs["plan"] = dict(kwargs.get("plan") or {}, php=sys.executable)
        return super().lanzar(puerta, tema, **kwargs)

    def _montar(self, modo="ok", pruebas=PRUEBAS, lanzador=True):
        montar_sistema_de_mentira(self.banco, modo)
        if lanzador:
            self.escribir(self.banco / "tests" / "run.php", LANZADOR_DE_MENTIRA)
        for prueba in pruebas:
            self.escribir(self.banco / prueba, "<?php\n")
        return self.tema()

    def test_pasa_cuando_el_lanzador_dice_cero_fallos(self):
        tema = self._montar("ok")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 0)
        self.assertIn("14 pruebas de temas del sistema pasan", informe["resumen"])
        self.assertEqual(informe["medidas"]["comprobaciones"], 561)
        self.assertEqual(informe["medidas"]["fallan"], 0)
        self.assertTrue((self.banco / "themes" / tema.name / "theme.json").is_file(), "el candidato se instala en el banco")

    def test_lanza_las_tres_pruebas_del_sistema_con_su_lanzador(self):
        tema = self._montar("ok")
        self.lanzar("contrato", tema)
        llamadas = (self.banco / "llamadas.log").read_text(encoding="utf-8")
        self.assertIn("run " + " ".join(PRUEBAS), llamadas)

    def test_una_imagen_sin_medidas_no_pasa_y_dice_el_fichero(self):
        tema = self._montar("imagen")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertFalse(informe["ok"])
        self.assertIn("no pasan con este tema", informe["resumen"])
        self.assertIn("themes/%s/templates/partials/header.php" % tema.name, self.texto_del_informe(informe))
        self.assertEqual(informe["medidas"]["del_tema"], 1)
        self.assertEqual(informe["medidas"]["fallan"], 1)

    def test_un_fallo_que_nombra_al_tema_por_su_nombre_tambien_es_suyo(self):
        tema = self._montar("ancho")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no pasan con este tema", informe["resumen"])
        self.assertIn(".af-prose a todo el ancho", informe["resumen"])

    def test_un_fallo_de_otro_tema_no_pasa_y_manda_rehacer_el_banco(self):
        tema = self._montar("ajeno")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("ninguna nombra este tema", informe["resumen"])
        self.assertIn("banco --rehacer", informe["resumen"])
        self.assertEqual(informe["medidas"]["del_tema"], 0)

    def test_si_el_lanzador_revienta_no_pasa_y_enseña_lo_ultimo_que_dijo(self):
        tema = self._montar("cortado")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("sin decir qué falla", informe["resumen"])
        self.assertIn("algo se rompió al arrancar", self.texto_del_informe(informe))

    def test_un_codigo_cero_con_un_fallo_escrito_no_se_da_por_bueno(self):
        tema = self._montar("miente")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertFalse(informe["ok"])

    def test_si_el_sistema_no_trae_el_lanzador_o_las_pruebas_sale_con_dos(self):
        for caso in ({"lanzador": False}, {"pruebas": ()}):
            with self.subTest(caso=caso):
                shutil.rmtree(str(self.banco), ignore_errors=True)
                tema = self.salida / "tema-uno"
                shutil.rmtree(str(tema), ignore_errors=True)
                tema = self._montar("ok", **caso)
                codigo, informe, texto = self.lanzar("contrato", tema)
                self.aceptar(codigo, informe, texto, 2)
                self.assertIn("no se imita su comprobación", informe["resumen"])
                self.assertTrue(informe["ok"], "un «no aplica» no es un fallo")

    def test_con_solo_una_de_las_pruebas_se_lanza_esa(self):
        tema = self._montar("ok", pruebas=PRUEBAS[1:2])
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["ficheros"], 1)
        llamadas = (self.banco / "llamadas.log").read_text(encoding="utf-8")
        self.assertIn("run " + PRUEBAS[1] + "\n", llamadas)

    def test_sin_banco_preparado_sale_con_dos(self):
        tema = self.tema()
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.aceptar(codigo, informe, texto, 2)
        self.assertIn("banco de pruebas no está preparado", informe["resumen"])

    def test_no_modifica_el_candidato(self):
        tema = self._montar("imagen")
        antes = self.instantanea(tema)
        self.lanzar("contrato", tema)
        self.assertEqual(antes, self.instantanea(tema))

    def test_el_informe_tiene_la_forma_del_contrato(self):
        tema = self._montar("ok")
        codigo, informe, texto = self.lanzar("contrato", tema)
        self.assertEqual(sorted(informe), ["detalles", "medidas", "ok", "puerta", "resumen"])
        self.assertEqual(informe["puerta"], "contrato")


@unittest.skipUnless(sistema_disponible(), "hace falta AIFEC_RUTA (una instalación de AIFEC) y un PHP con SQLite")
class PruebasConElSistemaReal(unittest.TestCase):
    """La puerta contra las pruebas de verdad del sistema, con el banco que hace la propia fábrica."""

    @classmethod
    def setUpClass(cls):
        cls.fab = FabricaReal()
        cls.fab.preparar_banco()
        cls.salida = cls.fab.raiz / "salida"

    @classmethod
    def tearDownClass(cls):
        cls.fab.borrar()

    def setUp(self):
        self.creados = []

    def tearDown(self):
        # un tema estropeado que se quedara en el banco rompería las pruebas del sistema para el siguiente
        for slug in self.creados:
            for carpeta in (self.salida / slug, self.fab.banco / "themes" / slug, self.fab.raiz / "estado" / "paginas" / slug):
                shutil.rmtree(str(carpeta), ignore_errors=True)

    def tema(self, slug):
        destino = self.salida / slug
        self.creados.append(slug)
        ap.esqueleto_mod.crear(slug, "Tema de prueba", destino, "", True)
        return destino

    def lanzar(self, tema):
        self.fab.escribir_plan({})
        informe = self.fab.raiz / "informe-contrato.json"
        if informe.exists():
            informe.unlink()
        proceso = subprocess.run(
            [sys.executable, str(self.fab.raiz / "puertas" / "contrato.py"), "--slug", tema.name, "--candidato", str(tema), "--banco", str(self.fab.banco),
             "--plan", str(self.fab.raiz / "plan.json"), "--informe", str(informe)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=600, encoding="utf-8", errors="replace")
        datos = json.loads(informe.read_text(encoding="utf-8")) if informe.is_file() else {}
        return proceso.returncode, datos, proceso.stdout + proceso.stderr

    def completo(self, informe):
        return informe.get("resumen", "") + "\n" + "\n".join(informe.get("detalles", []))

    def test_el_esqueleto_pasa_las_pruebas_de_temas_del_sistema(self):
        tema = self.tema("esq-contrato")
        codigo, informe, texto = self.lanzar(tema)
        self.assertEqual(codigo, 0, texto)
        self.assertGreaterEqual(informe["medidas"]["pruebas_ok"], 3)
        self.assertEqual(informe["medidas"]["ficheros"], 3)

    def test_una_imagen_sin_ancho_ni_alto_en_una_plantilla_no_pasa(self):
        tema = self.tema("esq-imagen")
        ruta = tema / "templates" / "partials" / "footer.php"
        ruta.write_bytes((ruta.read_text(encoding="utf-8") + '\n<img src="sello.png" alt="">\n').encode("utf-8"))
        codigo, informe, texto = self.lanzar(tema)
        self.assertEqual(codigo, 1, texto)
        self.assertIn("themes/esq-imagen/templates/partials/footer.php", self.completo(informe), texto)
        self.assertGreaterEqual(informe["medidas"]["del_tema"], 1)

    def test_estrechar_el_texto_en_la_hoja_no_pasa(self):
        tema = self.tema("esq-estrecho")
        ruta = tema / "assets" / "css" / "theme.css"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        previo = ruta.read_text(encoding="utf-8") if ruta.is_file() else ""
        ruta.write_bytes((previo + "\n.af-prose{max-width:62ch}\n").encode("utf-8"))
        codigo, informe, texto = self.lanzar(tema)
        self.assertEqual(codigo, 1, texto)
        self.assertIn("esq-estrecho: .af-prose a todo el ancho", self.completo(informe), texto)


if __name__ == "__main__":
    unittest.main()
