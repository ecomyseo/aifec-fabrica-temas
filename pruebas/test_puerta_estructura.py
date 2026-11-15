"""AIFEC — fábrica de temas: pruebas del comparador de estructura y de la puerta «estructura».

El comparador se prueba con páginas escritas a mano (sin sistema): una contra sí misma, con otras clases y otros
textos, con otra composición, con veinte tarjetas en vez de ocho… La puerta, con carpetas de páginas ya pintadas
(`--paginas`), así que nada de esto necesita PHP ni el sistema.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import subprocess
import sys
import unittest

from ayudas_puertas import BaseTemas, PUERTAS, cabecera, ficha, listado, pagina, pie, escribir_paginas  # noqa: E402  (también pone puertas/ en el path)

import _html  # noqa: E402


def _superficies(variante, estilo="a", numero=8):
    cuerpo = '<html><body>%s%s%s%s</body></html>' % (cabecera(variante, estilo), listado(variante, estilo, numero), ficha(variante, estilo), pie(variante, estilo))
    return _html.superficies_de(_html.leer(cuerpo))


class PruebasComparador(unittest.TestCase):
    def test_una_pagina_contra_si_misma_da_uno(self):
        a = _superficies(0)
        valores = _html.comparar(a, a)
        self.assertEqual(sorted(valores), sorted(_html.SUPERFICIES))
        for superficie, valor in valores.items():
            self.assertEqual(valor, 1.0, superficie)

    def test_cambiar_clases_propias_y_textos_no_engana(self):
        valores = _html.comparar(_superficies(0, "a"), _superficies(0, "zeta"))
        for superficie, valor in valores.items():
            self.assertGreaterEqual(valor, 0.95, superficie)

    def test_otra_composicion_de_cabecera_baja_la_cabecera_y_solo_la_cabecera(self):
        base = _superficies(0)
        distinta = _html.superficies_de(_html.leer(
            '<html><body>%s%s%s%s</body></html>' % (cabecera(1), listado(0), ficha(0), pie(0))))
        valores = _html.comparar(base, distinta)
        self.assertLess(valores["cabecera"], 0.82)
        for superficie in ("tarjeta", "listado", "ficha", "pie"):
            self.assertGreaterEqual(valores[superficie], 0.95, superficie)

    def test_veinte_tarjetas_en_vez_de_ocho_no_cambia_la_cifra(self):
        ocho = _superficies(0, numero=8)
        veinte = _superficies(0, numero=20)
        for superficie in _html.SUPERFICIES:
            self.assertEqual(ocho[superficie], veinte[superficie], superficie)
        self.assertEqual(_html.comparar(ocho, veinte)["listado"], 1.0)

    def test_anadir_clases_propias_a_cada_elemento_no_baja_el_parecido(self):
        cuerpo = "".join(f(0) for f in (cabecera, listado, ficha, pie))
        con_clases = re.sub(r"<(div|span|p|ul|li|nav|form|section|article|h3|a)(?![^>]*class=)", r'< class="propia"', cuerpo)
        con_clases = con_clases.replace('class="af-', 'class="propia af-')
        a = _html.superficies_de(_html.leer(cuerpo))
        b = _html.superficies_de(_html.leer(con_clases))
        self.assertNotEqual(cuerpo, con_clases)
        for superficie in _html.SUPERFICIES:
            self.assertEqual(a[superficie], b[superficie], superficie)

    def test_las_imagenes_y_los_iconos_svg_no_cuentan(self):
        a = _html.superficies_de(_html.leer('<footer class="af-footer"><div class="af-container"><p>x</p></div></footer>'))
        b = _html.superficies_de(_html.leer('<footer class="af-footer"><img src="a.png"><svg><path d="M0"/></svg><div class="af-container">'
                                            '<picture><source><img></picture><p>otro texto</p></div></footer>'))
        self.assertEqual(a["pie"], b["pie"])

    def test_tolera_html_mal_cerrado(self):
        arbol = _html.leer('<div class="af-listing"><ul><li>uno<li>dos</ul><p>suelto<div class="af-product-card"></div>')
        superficies = _html.superficies_de(arbol)
        self.assertIn("listado", superficies)
        self.assertIn("tarjeta", superficies)

    def test_solo_se_comparan_las_superficies_que_estan_en_las_dos(self):
        solo_pie = _html.superficies_de(_html.leer('<footer class="af-footer"><p>x</p></footer>'))
        valores = _html.comparar(_superficies(0), solo_pie)
        self.assertEqual(list(valores), ["pie"])

    def test_la_tarjeta_es_la_primera_de_la_pagina(self):
        pagina = ('<div class="af-product-card"><span class="af-badge">a</span></div><div class="af-product-card"><h3>b</h3></div>')
        tarjeta = _html.superficies_de(_html.leer(pagina))["tarjeta"]
        self.assertIn("1:span.af-badge", tarjeta)
        self.assertNotIn("1:h3", tarjeta)


class PruebasComparadorSuelto(BaseTemas):
    def _suelto(self, a, b):
        proceso = subprocess.run([sys.executable, str(PUERTAS / "estructura.py"), "--comparar", str(a), str(b)], stdin=subprocess.DEVNULL,
                                 capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        return proceso.returncode, proceso.stdout + proceso.stderr

    def test_por_linea_de_ordenes_enseña_la_tabla_y_la_cifra_mas_alta(self):
        carpeta = self.tmp / "sueltas"
        carpeta.mkdir()
        (carpeta / "a.html").write_text('<html><body>%s%s%s%s</body></html>' % (cabecera(0), listado(0), ficha(0), pie(0)), encoding="utf-8")
        (carpeta / "b.html").write_text('<html><body>%s%s%s%s</body></html>' % (cabecera(1), listado(0), ficha(0), pie(0)), encoding="utf-8")
        codigo, texto = self._suelto(carpeta / "a.html", carpeta / "b.html")
        self.assertEqual(codigo, 0, texto)
        self.assertIn("cabecera", texto)
        self.assertIn("Más alto:", texto)

    def test_con_un_fichero_que_no_existe_sale_con_dos(self):
        codigo, texto = self._suelto(self.tmp / "no.html", self.tmp / "tampoco.html")
        self.assertEqual(codigo, 2, texto)
        self.assertIn("no existe", texto)


class PruebasPuertaEstructura(BaseTemas):
    def _tema_con_padre(self, slug="nuevo", padre="base"):
        tema = self.tema(slug, "Nuevo")
        manifiesto = tema / "theme.json"
        manifiesto.write_text(manifiesto.read_text(encoding="utf-8").replace('"parent": "base"', '"parent": "%s"' % padre), encoding="utf-8")
        return tema

    def test_un_clon_del_tema_base_con_otros_colores_se_rechaza_nombrando_superficie_y_tema(self):
        paginas = self.tmp / "paginas"
        escribir_paginas(paginas, "base", 0, "a")
        escribir_paginas(paginas, "clon", 0, "zeta")   # otras clases propias y otros textos
        tema = self._tema_con_padre("clon")
        codigo, informe, texto = self.lanzar("estructura", tema, paginas)
        self.assertEqual(codigo, 1, texto)
        completo = self.texto_del_informe(informe)
        self.assertIn("cabecera", completo)
        self.assertIn("«base»", completo)
        self.assertIn("superficie heredada sin rediseñar", completo)
        self.assertFalse(informe["ok"])

    def test_un_tema_que_copia_a_otro_que_no_es_su_padre_se_rechaza_con_el_limite_del_plan(self):
        paginas = self.tmp / "paginas"
        escribir_paginas(paginas, "base", 1)
        escribir_paginas(paginas, "otro", 0, "a")
        escribir_paginas(paginas, "copia", 0, "b")
        tema = self._tema_con_padre("copia")
        codigo, informe, texto = self.lanzar("estructura", tema, paginas)
        self.assertEqual(codigo, 1, texto)
        completo = self.texto_del_informe(informe)
        self.assertIn("se parece al tema «otro»", completo)
        self.assertIn("límite 0,82", completo)

    def _propio_distinto(self, paginas):
        """Un tema cuyas cinco superficies no se parecen a las de `base` ni a las de `otro`."""
        escribir_paginas(paginas, "base", 0)
        escribir_paginas(paginas, "otro", 1)
        propio = paginas / "propio"
        propio.mkdir()
        cab = cabecera(2)
        pi = ('<footer class="af-footer"><nav class="af-nav"><ul class="af-nav-list"><li class="af-nav-item"><a class="af-nav-link" href="/">A</a></li></ul></nav>'
              '<aside><p class="af-small">x</p></aside></footer>')
        tarj = '<article class="af-product-card"><header><h3>P</h3></header><footer><span class="af-price">1</span></footer></article>'
        lis = '<table class="af-listing"><tbody><tr><td class="af-listing-results">%s</td></tr></tbody></table>' % (tarj * 6)
        fic = ('<main class="af-product"><aside class="af-product-gallery"><div class="af-gallery"><figure><img src="a"></figure></div></aside>'
               '<section class="af-product-buy"><h1 class="af-title">P</h1><form data-af-cart-add><button class="af-btn">Añadir</button></form></section></main>')
        for nombre, cuerpo in (("portada", tarj), ("listado", lis), ("ficha", fic), ("carrito", '<div class="af-cart"></div>')):
            (propio / (nombre + ".html")).write_text(pagina(cuerpo, cab, pi), encoding="utf-8")
        return self._tema_con_padre("propio")

    def test_pasa_cuando_cada_superficie_es_distinta_de_la_de_los_demas(self):
        paginas = self.tmp / "paginas"
        tema = self._propio_distinto(paginas)
        codigo, informe, texto = self.lanzar("estructura", tema, paginas)
        self.assertEqual(codigo, 0, texto)
        self.assertTrue(informe["ok"])
        self.assertIn("Más alto:", self.texto_del_informe(informe))
        self.assertEqual(informe["medidas"]["temas_comparados"], 2)
        self.assertLess(informe["medidas"]["maximo"], 0.82)

    def test_sin_otros_temas_con_los_que_comparar_pasa_y_lo_dice(self):
        paginas = self.tmp / "paginas"
        escribir_paginas(paginas, "solo", 0)
        tema = self._tema_con_padre("solo", padre="base")
        codigo, informe, texto = self.lanzar("estructura", tema, paginas)
        self.assertEqual(codigo, 0, texto)
        self.assertIn("no hay otros temas con los que comparar", informe["resumen"])

    def test_si_al_tema_le_falta_una_superficie_del_contrato_no_pasa_y_nombra_la_clase(self):
        paginas = self.tmp / "paginas"
        escribir_paginas(paginas, "base", 1)
        escribir_paginas(paginas, "roto", 0, pie='<div class="pie-sin-clase">x</div>')
        tema = self._tema_con_padre("roto")
        codigo, informe, texto = self.lanzar("estructura", tema, paginas)
        self.assertEqual(codigo, 1, texto)
        self.assertIn("af-footer", informe["resumen"])

    def test_el_umbral_sale_del_plan(self):
        paginas = self.tmp / "paginas"
        tema = self._propio_distinto(paginas)
        codigo, informe, texto = self.lanzar("estructura", tema, paginas)
        self.assertEqual(codigo, 0, texto)
        maximo = informe["medidas"]["maximo"]
        codigo, informe, texto = self.lanzar("estructura", tema, paginas, plan={"umbral_estructura": round(maximo - 0.05, 2)})
        self.assertEqual(codigo, 1, texto)
        self.assertIn("límite", self.texto_del_informe(informe))

    def test_la_puerta_no_modifica_el_candidato(self):
        paginas = self.tmp / "paginas"
        tema = self._propio_distinto(paginas)
        antes = self.instantanea(tema)
        self.lanzar("estructura", tema, paginas)
        self.assertEqual(antes, self.instantanea(tema))


if __name__ == "__main__":
    unittest.main()
