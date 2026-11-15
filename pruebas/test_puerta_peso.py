"""AIFEC — fábrica de temas: pruebas de la puerta «peso».

El esqueleto pasa; el mismo tema con una hoja de 60 KB, un guion de 30 KB, una ficha de 200 KB o una imagen sin
medidas, no. La ficha pintada se lee de una carpeta de páginas ya pintadas, así que no hace falta el sistema.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import unittest

from ayudas_puertas import BaseTemas, escribir_paginas

import peso  # noqa: E402


class PruebasPuertaPeso(BaseTemas):
    def test_el_esqueleto_pasa_con_su_hoja_pequena(self):
        tema = self.tema()
        codigo, informe, texto = self.lanzar("peso", tema)
        self.aceptar(codigo, informe, texto, 0)
        self.assertTrue(informe["ok"])
        self.assertLess(informe["medidas"]["css_bytes"], 45000)
        self.assertEqual(informe["medidas"]["js_bytes"], 0)

    def test_una_hoja_de_60_kb_no_pasa_y_dice_cual(self):
        tema = self.tema()
        self.escribir(tema / "assets" / "css" / "theme.css", "/* relleno */\n" + ".af-x{color:red}\n" * 4000)
        self.assertGreater((tema / "assets" / "css" / "theme.css").stat().st_size, 60000)
        codigo, informe, texto = self.lanzar("peso", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertFalse(informe["ok"])
        self.assertIn("assets/css/theme.css pesa", informe["resumen"])
        self.assertIn("45,0 KB", informe["resumen"])

    def test_un_guion_de_30_kb_no_pasa(self):
        tema = self.tema()
        self.escribir(tema / "assets" / "js" / "theme.js", "// relleno\n" + "var a=1;\n" * 4000)
        codigo, informe, texto = self.lanzar("peso", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("assets/js/theme.js pesa", informe["resumen"])

    def test_cualquier_otra_hoja_o_guion_del_tema_tambien_cuenta(self):
        tema = self.tema()
        self.escribir(tema / "assets" / "css" / "extra.css", ".af-x{color:red}\n" * 4000)
        codigo, informe, texto = self.lanzar("peso", tema)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("extra.css", informe["resumen"])

    def test_la_ficha_pintada_de_200_kb_no_pasa(self):
        tema = self.tema()
        paginas = self.tmp / "paginas"
        destino = escribir_paginas(paginas, tema.name, 0)
        ficha = destino / "ficha.html"
        ficha.write_text(ficha.read_text(encoding="utf-8").replace("</main>", "<p>%s</p></main>" % ("texto de relleno " * 12000)), encoding="utf-8")
        codigo, informe, texto = self.lanzar("peso", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("ficha de producto pintada pesa", informe["resumen"])
        self.assertGreater(informe["medidas"]["ficha_bytes"], 150000)

    def test_las_imagenes_incrustadas_no_cuentan_en_el_peso_de_la_ficha(self):
        tema = self.tema()
        paginas = self.tmp / "paginas"
        destino = escribir_paginas(paginas, tema.name, 0)
        ficha = destino / "ficha.html"
        enorme = "data:image/png;base64," + "A" * 400000
        ficha.write_text(ficha.read_text(encoding="utf-8").replace('src="g.png"', 'src="%s" width="10" height="10"' % enorme), encoding="utf-8")
        self.assertGreater(len(ficha.read_text(encoding="utf-8")), 400000)
        codigo, informe, texto = self.lanzar("peso", tema, paginas)
        # las demás imágenes de la página de pega no traen medidas: se miran aparte
        self.assertLess(informe["medidas"]["ficha_bytes"], 150000)

    def test_una_imagen_sin_width_y_height_no_pasa(self):
        tema = self.tema()
        paginas = self.tmp / "paginas"
        destino = escribir_paginas(paginas, tema.name, 0)
        for nombre in ("portada", "listado", "ficha", "carrito"):
            ruta = destino / (nombre + ".html")
            ruta.write_text(ruta.read_text(encoding="utf-8").replace("<img ", '<img width="10" height="10" '), encoding="utf-8")
        codigo, informe, texto = self.lanzar("peso", tema, paginas)
        self.aceptar(codigo, informe, texto, 0)
        ruta = destino / "ficha.html"
        ruta.write_text(ruta.read_text(encoding="utf-8").replace('<img width="10" height="10" src="g.png">', '<img src="g.png">'), encoding="utf-8")
        codigo, informe, texto = self.lanzar("peso", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("sin width y height", informe["resumen"])
        self.assertEqual(informe["medidas"]["imagenes_sin_medidas"], 1)

    def test_la_puerta_no_modifica_el_candidato(self):
        tema = self.tema()
        antes = self.instantanea(tema)
        self.lanzar("peso", tema)
        self.assertEqual(antes, self.instantanea(tema))

    def test_sin_imagenes_quita_las_etiquetas_y_los_data_uri(self):
        html = '<p>a</p><img src="x.png"><picture><source srcset="y.png"><img src="z.png"></picture><i style="background:url(data:image/png;base64,AAAA)"></i>'
        limpio = peso.sin_imagenes(html)
        self.assertNotIn("<img", limpio)
        self.assertNotIn("<picture", limpio)
        self.assertNotIn("base64", limpio)
        self.assertIn("<p>a</p>", limpio)


if __name__ == "__main__":
    unittest.main()
