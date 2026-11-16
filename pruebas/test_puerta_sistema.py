"""AIFEC — fábrica de temas: pruebas de las puertas que preguntan al sistema (`validador` y `traducciones`) y de
las siete puertas contra el sistema real.

Primero con un «sistema» de mentira (un `aifec` escrito en Python que contesta lo que la prueba diga): se prueba
cómo se lee su veredicto sin necesitar nada. Después, «con sistema» (se saltan solas si `AIFEC_RUTA` no apunta a
una instalación o no hay un PHP con SQLite): cada puerta con el esqueleto da 0 y con el mismo tema estropeado para
esa puerta da 1 con su motivo.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

import ayudas_puertas as ap
from ayudas_puertas import BaseTemas, FabricaReal, montar_sistema_de_mentira, sistema_disponible


class PruebasConUnSistemaDeMentira(BaseTemas):
    def lanzar(self, puerta, tema, **kwargs):
        # el `aifec` de mentira es un guion de Python: se lanza con el Python de la prueba en vez de con PHP
        kwargs["plan"] = dict(kwargs.get("plan") or {}, php=sys.executable)
        return super().lanzar(puerta, tema, **kwargs)

    def _montar(self, modo="ok"):
        montar_sistema_de_mentira(self.banco, modo)
        return self.tema()

    def test_el_validador_pasa_cuando_theme_check_sale_sin_errores(self):
        tema = self._montar("ok")
        codigo, informe, texto = self.lanzar("validador", tema)
        self.aceptar(codigo, informe, texto, 0)
        self.assertIn("puntuación 96", informe["resumen"])
        self.assertTrue((self.banco / "themes" / tema.name / "theme.json").is_file(), "el candidato se instala en el banco")
        llamadas = (self.banco / "llamadas.log").read_text(encoding="utf-8")
        self.assertIn("theme:check %s" % tema.name, llamadas)

    def test_el_validador_no_pasa_y_cuenta_el_error_con_su_motivo(self):
        tema = self._montar("falla")
        codigo, informe, texto = self.lanzar("validador", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("page_head()", informe["resumen"])
        self.assertFalse(informe["ok"])
        self.assertEqual(informe["medidas"]["errores"], 1)

    def test_si_el_sistema_no_trae_la_orden_la_puerta_sale_con_dos_y_no_la_imita(self):
        tema = self._montar("sin_ordenes")
        for puerta in ("validador", "traducciones"):
            codigo, informe, texto = self.lanzar(puerta, tema)
            self.aceptar(codigo, informe, texto, 2)
            self.assertIn("no se imita su comprobación", informe["resumen"])
            self.assertTrue(informe["ok"], "un «no aplica» no es un fallo")

    def test_sin_banco_preparado_las_puertas_que_lo_necesitan_salen_con_dos(self):
        tema = self.tema()
        for puerta in ("validador", "traducciones"):
            codigo, informe, texto = self.lanzar(puerta, tema)
            self.aceptar(codigo, informe, texto, 2)
            self.assertIn("banco de pruebas no está preparado", informe["resumen"])

    def test_las_traducciones_pasan_con_cero_cadenas_sin_traducir(self):
        tema = self._montar("ok")
        codigo, informe, texto = self.lanzar("traducciones", tema)
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["faltan"], 0)
        self.assertEqual(informe["medidas"]["cadenas"], 41)
        self.assertIn("i18n:check themes/%s es" % tema.name, (self.banco / "llamadas.log").read_text(encoding="utf-8"))

    def test_las_traducciones_enseñan_las_cadenas_que_faltan(self):
        tema = self._montar("falla")
        codigo, informe, texto = self.lanzar("traducciones", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("3 cadena(s) sin traducir de 41", informe["resumen"])
        self.assertIn("'Sale'", self.texto_del_informe(informe))

    def test_los_datos_del_banco_se_fuerzan_dentro_del_banco(self):
        tema = self._montar("ok")
        (self.banco / "aifec").write_text((self.banco / "aifec").read_text(encoding="utf-8").replace(
            'args = [a for a in sys.argv[1:] if not a.startswith("--data=")]',
            'args = [a for a in sys.argv[1:] if not a.startswith("--data=")]\nopen(raiz / "datos.txt", "w").write(" ".join(a for a in sys.argv[1:] if a.startswith("--data=")))'), encoding="utf-8")
        self.lanzar("validador", tema)
        datos = (self.banco / "datos.txt").read_text(encoding="utf-8")
        self.assertIn(str(self.banco / "sites"), datos)

    def test_las_puertas_no_modifican_el_candidato(self):
        tema = self._montar("ok")
        antes = self.instantanea(tema)
        for puerta in ("validador", "traducciones"):
            self.lanzar(puerta, tema)
        self.assertEqual(antes, self.instantanea(tema))

    def test_el_informe_tiene_la_forma_del_contrato(self):
        tema = self._montar("ok")
        codigo, informe, texto = self.lanzar("validador", tema)
        self.assertEqual(sorted(informe), ["detalles", "medidas", "ok", "puerta", "resumen"])
        self.assertEqual(informe["puerta"], "validador")
        self.assertIsInstance(informe["detalles"], list)
        self.assertIsInstance(informe["medidas"], dict)


@unittest.skipUnless(sistema_disponible(), "hace falta AIFEC_RUTA (una instalación de AIFEC) y un PHP con SQLite")
class PruebasConElSistemaReal(unittest.TestCase):
    """Las puertas contra el sistema real, con el banco que hace la propia fábrica."""

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
        # cada prueba deja el banco y la salida como estaban: los temas de pruebas anteriores serían «temas ya fabricados»
        # con los que comparar, y todos son hijos del mismo esqueleto
        for slug in self.creados:
            for carpeta in (self.salida / slug, self.fab.banco / "themes" / slug, self.fab.raiz / "estado" / "paginas" / slug):
                shutil.rmtree(str(carpeta), ignore_errors=True)

    def tema(self, slug, nombre="Tema de prueba"):
        destino = self.salida / slug
        self.creados.append(slug)
        ap.esqueleto_mod.crear(slug, nombre, destino, "", True)
        return destino

    def lanzar(self, puerta, tema, plan=None):
        self.fab.escribir_plan(plan or {})
        informe = self.fab.raiz / ("informe-%s.json" % puerta)
        if informe.exists():
            informe.unlink()
        proceso = subprocess.run(
            [sys.executable, str(self.fab.raiz / "puertas" / (puerta + ".py")), "--slug", tema.name, "--candidato", str(tema), "--banco", str(self.fab.banco),
             "--plan", str(self.fab.raiz / "plan.json"), "--informe", str(informe)],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=600, encoding="utf-8", errors="replace")
        datos = json.loads(informe.read_text(encoding="utf-8")) if informe.is_file() else {}
        return proceso.returncode, datos, proceso.stdout + proceso.stderr

    def completo(self, informe):
        return informe.get("resumen", "") + "\n" + "\n".join(informe.get("detalles", []))

    def bien(self, puerta, tema, plan=None):
        codigo, informe, texto = self.lanzar(puerta, tema, plan)
        self.assertEqual(codigo, 0, texto)
        self.assertTrue(informe["ok"])
        return informe

    def mal(self, puerta, tema, motivo, plan=None):
        codigo, informe, texto = self.lanzar(puerta, tema, plan)
        self.assertEqual(codigo, 1, texto)
        self.assertFalse(informe["ok"])
        self.assertIn(motivo, self.completo(informe), texto)
        return informe

    def php_versiones(self):
        return {"php_versiones": [self.fab.php]}

    # ---- el esqueleto pasa todas las puertas ----------------------------------------------

    def test_el_esqueleto_tal_cual_con_sus_marcas_pasa_theme_check(self):
        crudo = self.salida / "esqueleto-crudo"
        self.creados.append("esqueleto-crudo")
        shutil.copytree(str(ap.PROYECTO / "plantillas" / "esqueleto"), str(crudo))
        self.assertIn("__Nombre__", (crudo / "theme.json").read_text(encoding="utf-8"))
        self.bien("validador", crudo)

    def test_el_esqueleto_pasa_las_siete_puertas(self):
        tema = self.tema("esq-bueno")
        for puerta in ("validador", "estructura", "peso", "movil", "traducciones", "limpieza", "contrato"):
            with self.subTest(puerta=puerta):
                informe = self.bien(puerta, tema, self.php_versiones())
                self.assertTrue(informe["resumen"])
        codigo, informe, texto = self.lanzar("capturas", tema)
        self.assertEqual(codigo, 2, texto)

    # ---- el mismo tema, estropeado para cada puerta ----------------------------------------

    def test_sin_page_head_el_validador_no_pasa(self):
        tema = self.tema("esq-sin-head")
        layout = (Path(ap.AIFEC_RUTA) / "themes" / "base" / "templates" / "layout.php").read_text(encoding="utf-8")
        self.assertIn("page_head(", layout)
        self.fab_escribir(tema / "templates" / "layout.php", layout.replace("<?= page_head($af_page) ?>", ""))
        self.mal("validador", tema, "page_head()")

    def test_una_cadena_sin_traducir_las_traducciones_no_pasan(self):
        tema = self.tema("esq-sin-traducir")
        ruta = tema / "templates" / "partials" / "footer.php"
        ruta.write_bytes((ruta.read_text(encoding="utf-8") + "\n<p><?= e(t('A string nobody translated')) ?></p>\n").encode("utf-8"))
        self.mal("traducciones", tema, "A string nobody translated")

    def test_una_hoja_de_60_kb_el_peso_no_pasa(self):
        tema = self.tema("esq-pesado")
        self.fab_escribir(tema / "assets" / "css" / "theme.css", ".af-x{color:red}\n" * 4500)
        self.mal("peso", tema, "assets/css/theme.css pesa")

    def test_sin_barra_de_movil_la_puerta_de_movil_no_pasa(self):
        tema = self.tema("esq-sin-barra")
        self.fab_escribir(tema / "templates" / "partials" / "mobile-bar.php", "<?php\n// sin barra\n")
        self.mal("movil", tema, "no hay barra inferior de móvil")

    def test_una_fuente_de_google_la_limpieza_no_pasa(self):
        tema = self.tema("esq-fuente")
        ruta = tema / "assets" / "css" / "theme.css"
        ruta.write_bytes((ruta.read_text(encoding="utf-8") + "\n@font-face{font-family:X;src:url(https://fonts.googleapis.com/css2?family=X)}\n").encode("utf-8"))
        self.mal("limpieza", tema, "fonts.googleapis.com", self.php_versiones())

    def test_un_zip_dentro_la_limpieza_no_pasa(self):
        tema = self.tema("esq-con-zip")
        (tema / "copia.zip").write_bytes(b"PK\x03\x04")
        self.mal("limpieza", tema, "paquete comprimido", self.php_versiones())

    def test_un_clon_del_tema_base_con_otros_colores_la_estructura_lo_rechaza(self):
        clon = self.salida / "clon-base"
        self.creados.append("clon-base")
        (clon / "assets" / "css").mkdir(parents=True)
        (clon / "theme.json").write_text('{"name": "Clon", "version": "1.0.0", "parent": "base", "settings": {}}', encoding="utf-8")
        (clon / "assets" / "css" / "theme.css").write_text(":root{--accent:#005f73;--bg:#f0f8ff}\n.af-btn-primary{background:var(--accent)}\n", encoding="utf-8")
        informe = self.mal("estructura", clon, "«base»")
        completo = self.completo(informe)
        self.assertIn("cabecera", completo)
        self.assertIn("superficie heredada sin rediseñar", completo)

    def test_un_segundo_tema_hecho_desde_el_esqueleto_sin_cambiar_nada_se_rechaza_por_clon(self):
        uno = self.tema("esq-gemelo-uno")
        self.bien("estructura", uno)
        dos = self.tema("esq-gemelo-dos")
        informe = self.mal("estructura", dos, "«esq-gemelo-uno»")
        self.assertIn("se parece al tema", self.completo(informe))

    def fab_escribir(self, ruta, texto):
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(texto.encode("utf-8"))

    def test_las_puertas_no_modifican_el_candidato(self):
        tema = self.tema("esq-intacto")
        antes = ap.arbol(tema)
        for puerta in ("validador", "estructura", "peso", "movil", "traducciones", "limpieza", "contrato"):
            self.lanzar(puerta, tema, self.php_versiones())
        self.assertEqual(antes, ap.arbol(tema))


if __name__ == "__main__":
    unittest.main()
