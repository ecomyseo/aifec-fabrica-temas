"""AIFEC — fábrica de temas: pruebas de la puerta «limpieza».

El esqueleto pasa; el mismo tema con una fuente de fonts.googleapis.com, un `@import`, un `.zip`, un mapa de código,
`node_modules`, una captura suelta, una tipografía `.ttf` o un PHP con un error de sintaxis, no.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import unittest

from ayudas_puertas import BaseTemas, php_cualquiera


@unittest.skipUnless(php_cualquiera(), "hace falta PHP para probar la sintaxis")
class PruebasPuertaLimpieza(BaseTemas):
    def _hoja(self, tema, texto):
        ruta = tema / "assets" / "css" / "theme.css"
        ruta.write_bytes((ruta.read_text(encoding="utf-8") + "\n" + texto).encode("utf-8"))

    def test_el_esqueleto_esta_limpio(self):
        tema = self.tema()
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 0)
        self.assertTrue(informe["ok"])
        self.assertEqual(informe["medidas"]["problemas"], 0)
        self.assertGreaterEqual(informe["medidas"]["lint"], 6)

    def test_una_fuente_de_google_fonts_no_pasa_y_dice_en_que_fichero_y_linea(self):
        tema = self.tema()
        self._hoja(tema, "@font-face{font-family:X;src:url(https://fonts.googleapis.com/css2?family=X)}")
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("assets/css/theme.css:", informe["resumen"])
        self.assertIn("otro dominio", informe["resumen"])

    def test_una_direccion_sin_protocolo_tambien_es_de_otro_dominio(self):
        tema = self.tema()
        self._hoja(tema, ".af-x{background:url(//cdn.ejemplo.test/a.png)}")
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 1)

    def test_un_import_no_pasa(self):
        tema = self.tema()
        self._hoja(tema, '@import "otra.css";')
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("@import", informe["resumen"])

    def test_el_espacio_de_nombres_de_svg_no_cuenta_como_direccion_ajena(self):
        tema = self.tema()
        self.escribir(tema / "assets" / "img" / "forma.svg", '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1 1"></svg>')
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 0)

    def test_un_zip_dentro_del_tema_no_pasa(self):
        tema = self.tema()
        self.escribir(tema / "copia.zip", b"PK\x03\x04", binario=True)
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("copia.zip", informe["resumen"])
        self.assertIn("paquete comprimido", informe["resumen"])

    def test_un_mapa_de_codigo_una_tipografia_ttf_y_una_captura_suelta_no_pasan(self):
        for relativa, contenido, motivo in (
                ("assets/js/theme.js.map", b"{}", "trabajo"),
                ("assets/fonts/letra.ttf", b"\x00\x01", "woff2"),
                ("captura-portada.png", b"\x89PNG", "fuera de assets"),
                ("capturas/uno.png", b"\x89PNG", "carpeta que no es de un tema")):
            with self.subTest(relativa=relativa):
                tema = self.tema("tema-" + relativa.split("/")[-1].replace(".", "-"), "Tema")
                self.escribir(tema / relativa, contenido, binario=True)
                codigo, informe, texto = self.lanzar("limpieza", tema)
                self.aceptar(codigo, informe, texto, 1)
                self.assertIn(motivo, self.texto_del_informe(informe))

    def test_preview_png_en_la_raiz_y_las_imagenes_de_assets_si_se_admiten(self):
        tema = self.tema()
        self.escribir(tema / "preview.png", b"\x89PNG", binario=True)
        self.escribir(tema / "assets" / "img" / "foto.webp", b"RIFF", binario=True)
        self.escribir(tema / "assets" / "fonts" / "letra.woff2", b"wOF2", binario=True)
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 0)

    def test_node_modules_no_pasa(self):
        tema = self.tema()
        self.escribir(tema / "node_modules" / "x" / "index.js", "x")
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("node_modules", informe["resumen"])

    def test_un_php_con_un_error_de_sintaxis_no_pasa_y_nombra_el_fichero(self):
        tema = self.tema()
        ruta = tema / "templates" / "partials" / "header.php"
        ruta.write_bytes((ruta.read_text(encoding="utf-8") + "\n<?php if ($x) { ?>\n").encode("utf-8"))
        codigo, informe, texto = self.lanzar("limpieza", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("templates/partials/header.php no es PHP válido", informe["resumen"])

    def test_se_prueba_la_sintaxis_con_cada_version_del_plan_y_una_que_no_existe_no_pasa(self):
        tema = self.tema()
        codigo, informe, texto = self.lanzar("limpieza", tema, plan={"php_versiones": [php_cualquiera(), "no-existe-php-7.4"]})
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no encuentro el PHP", informe["resumen"])
        codigo, informe, texto = self.lanzar("limpieza", tema, plan={"php_versiones": [php_cualquiera()]})
        self.aceptar(codigo, informe, texto, 0)

    def test_la_puerta_no_modifica_el_candidato(self):
        tema = self.tema()
        self.escribir(tema / "copia.zip", b"PK", binario=True)
        antes = self.instantanea(tema)
        self.lanzar("limpieza", tema)
        self.assertEqual(antes, self.instantanea(tema))

    def test_un_candidato_que_no_existe_no_pasa(self):
        codigo, informe, texto = self.lanzar("limpieza", self.salida / "no-existe", slug="no-existe")
        self.aceptar(codigo, informe, texto, 1)


if __name__ == "__main__":
    unittest.main()
