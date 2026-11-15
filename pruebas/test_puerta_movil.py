"""AIFEC — fábrica de temas: pruebas de la puerta «movil».

Con páginas de mentira (`--paginas`) y hojas escritas a mano: el tema bueno pasa; sin barra inferior, sin acceso a
Buscar o a Carrito, con un acceso que no lleva a ningún sitio, con un botón de Filtros que abre un panel que no
existe, o con una hoja sin cabecera pegajosa, sin `safe-area`, con zonas de 30 px o sin foco visible, no.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import unittest

from ayudas_puertas import BARRA_BUENA, FILTROS_BOTON, HOJA_BUENA, BaseTemas, escribir_paginas

import movil  # noqa: E402


class PruebasPuertaMovil(BaseTemas):
    def _bueno(self, slug="tema-movil", **opciones):
        tema = self.con_hoja_buena(self.tema(slug))
        paginas = self.tmp / "paginas"
        escribir_paginas(paginas, slug, 0, **opciones)
        return tema, paginas

    def _con_hoja(self, hoja, slug="tema-movil"):
        tema, paginas = self._bueno(slug)
        self.escribir(tema / "assets" / "css" / "theme.css", hoja)
        return tema, paginas

    def test_el_tema_bueno_pasa(self):
        tema, paginas = self._bueno()
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 0)
        self.assertEqual(informe["medidas"]["paginas_miradas"], 4)
        self.assertIn("bien: cabecera pegajosa", self.texto_del_informe(informe))

    def test_sin_barra_inferior_no_pasa(self):
        tema, paginas = self._bueno(barra="")
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no hay barra inferior de móvil", self.texto_del_informe(informe))

    def test_sin_acceso_a_carrito_no_pasa(self):
        barra = ('<nav class="af-mobile-bar"><a class="af-mobile-bar-item" href="/buscar" data-af-drawer-open="af-search">'
                 '<span class="af-mobile-bar-label">Buscar</span></a></nav>')
        tema, paginas = self._bueno(barra=barra)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no tiene el acceso a Carrito", self.texto_del_informe(informe))

    def test_sin_acceso_a_buscar_no_pasa(self):
        barra = ('<nav class="af-mobile-bar"><a class="af-mobile-bar-item" href="/carrito" data-af-drawer-open="af-cart">'
                 '<span class="af-cart-count" data-af-cart-count hidden></span><span class="af-mobile-bar-label">Carrito</span></a></nav>')
        tema, paginas = self._bueno(barra=barra)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no tiene el acceso a Buscar", self.texto_del_informe(informe))

    def test_un_acceso_decorativo_que_no_lleva_a_ningun_sitio_no_pasa(self):
        barra = BARRA_BUENA.format(filtros="").replace('href="/buscar" data-af-drawer-open="af-search"', 'href="#"')
        tema, paginas = self._bueno(barra=barra)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("un acceso de la barra no funciona", self.texto_del_informe(informe))

    def test_un_acceso_que_abre_un_panel_que_no_esta_no_pasa(self):
        barra = BARRA_BUENA.format(filtros="").replace('<a class="af-mobile-bar-item" href="/buscar" data-af-drawer-open="af-search">',
                                                       '<button type="button" class="af-mobile-bar-item" data-af-drawer-open="af-search">').replace(
            '<span class="af-mobile-bar-label">Buscar</span></a>', '<span class="af-mobile-bar-label">Buscar</span></button>')
        tema, paginas = self._bueno(barra=barra)
        for nombre in ("portada", "listado", "ficha", "carrito"):
            ruta = paginas / tema.name / (nombre + ".html")
            ruta.write_text(ruta.read_text(encoding="utf-8").replace('<aside class="af-drawer" id="af-search"></aside>', ""), encoding="utf-8")
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("abre el panel «af-search» y la página no lo trae", self.texto_del_informe(informe))

    def test_un_boton_de_filtros_que_abre_un_panel_que_no_esta_no_pasa(self):
        tema, paginas = self._bueno("tema-filtro", filtros_boton=True)
        ruta = paginas / tema.name / "listado.html"
        ruta.write_text(ruta.read_text(encoding="utf-8").replace(' id="af-filters"', ""), encoding="utf-8")
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("abre un panel que no está en la página", self.texto_del_informe(informe))

    def test_el_contador_del_carrito_es_obligatorio(self):
        barra = BARRA_BUENA.format(filtros="").replace('<span class="af-cart-count" data-af-cart-count hidden></span>', "")
        tema, paginas = self._bueno(barra=barra)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no tiene contador", self.texto_del_informe(informe))

    def test_un_acceso_sin_nombre_accesible_no_pasa(self):
        barra = BARRA_BUENA.format(filtros="").replace('<span class="af-mobile-bar-label">Buscar</span>', "")
        tema, paginas = self._bueno(barra=barra)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("nombre accesible", self.texto_del_informe(informe))

    def test_filtros_solo_donde_hay_filtros(self):
        # el botón de Filtros en una página sin filtros no pasa
        tema, paginas = self._bueno(barra=BARRA_BUENA.format(filtros=FILTROS_BOTON))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("la página no tiene filtros", self.texto_del_informe(informe))

    def test_una_pagina_con_filtros_sin_boton_de_filtros_no_pasa(self):
        tema, paginas = self._bueno(filtros_boton=False)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("la barra no enseña el botón Filtros", self.texto_del_informe(informe))

    def test_hoja_sin_cabecera_pegajosa_no_pasa(self):
        tema, paginas = self._con_hoja(HOJA_BUENA.replace(".af-header{position:sticky;", ".af-header{position:static;"))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no es pegajosa", self.texto_del_informe(informe))

    def test_cabecera_pegajosa_solo_en_escritorio_no_vale_para_el_movil(self):
        hoja = HOJA_BUENA.replace(".af-header{position:sticky;top:0;z-index:40}", "@media (min-width:900px){.af-header{position:sticky;top:0}}")
        tema, paginas = self._con_hoja(hoja)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("no es pegajosa", self.texto_del_informe(informe))

    def test_hoja_sin_safe_area_no_pasa(self):
        tema, paginas = self._con_hoja(HOJA_BUENA.replace("env(safe-area-inset-bottom)", "0px"))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("safe-area-inset-bottom", self.texto_del_informe(informe))

    def test_zona_tactil_de_30_px_no_pasa_y_una_de_44_si(self):
        tema, paginas = self._con_hoja(HOJA_BUENA.replace("min-height:var(--bar-h)", "min-height:30px"))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("mide 30 px de alto", self.texto_del_informe(informe))
        tema, paginas = self._con_hoja(HOJA_BUENA.replace("min-height:var(--bar-h)", "min-height:44px"), "tema-movil-44")
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 0)

    def test_la_variable_de_alto_se_lee_de_root_y_una_pequena_no_pasa(self):
        tema, paginas = self._con_hoja(HOJA_BUENA.replace("--bar-h:3.5rem", "--bar-h:2rem"))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("mide 32 px de alto", self.texto_del_informe(informe))

    def test_hoja_sin_foco_visible_no_pasa(self):
        tema, paginas = self._con_hoja(HOJA_BUENA.replace(":focus-visible{outline:2px solid currentColor}", ""))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn(":focus-visible", self.texto_del_informe(informe))

    def test_hoja_sin_espacio_reservado_bajo_el_contenido_no_pasa(self):
        tema, paginas = self._con_hoja(HOJA_BUENA.replace(".af-has-bar{padding-bottom:calc(var(--bar-h) + env(safe-area-inset-bottom))}", ""))
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("reserva el alto de la barra", self.texto_del_informe(informe))

    def test_el_espacio_reservado_solo_en_la_hoja_de_impresion_no_vale(self):
        hoja = HOJA_BUENA.replace(".af-has-bar{padding-bottom:calc(var(--bar-h) + env(safe-area-inset-bottom))}",
                                  "@media print{.af-has-bar{padding-bottom:3rem}}")
        tema, paginas = self._con_hoja(hoja)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)
        self.assertIn("reserva el alto de la barra", self.texto_del_informe(informe))

    def test_un_tema_hijo_hereda_la_hoja_del_padre_salvo_que_diga_replace(self):
        # el esqueleto no trae el contrato en su hoja: lo hereda de base. Con base en el banco, pasa; con «replace», no.
        from ayudas_puertas import montar_sistema_de_mentira
        montar_sistema_de_mentira(self.banco)
        (self.banco / "themes" / "base" / "assets" / "css").mkdir(parents=True)
        (self.banco / "themes" / "base" / "assets" / "css" / "theme.css").write_text(HOJA_BUENA, encoding="utf-8")
        (self.banco / "themes" / "base" / "theme.json").write_text('{"name": "Base", "parent": null}', encoding="utf-8")
        tema = self.tema("hijo")
        paginas = self.tmp / "paginas"
        escribir_paginas(paginas, "hijo", 0)
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 0)
        manifiesto = tema / "theme.json"
        manifiesto.write_text(manifiesto.read_text(encoding="utf-8").replace('"parent": "base",', '"parent": "base", "css": "replace",'), encoding="utf-8")
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 1)

    def test_la_puerta_no_modifica_el_candidato(self):
        tema, paginas = self._bueno()
        antes = self.instantanea(tema)
        self.lanzar("movil", tema, paginas)
        self.assertEqual(antes, self.instantanea(tema))

    def test_la_pagina_de_muestra_se_acepta_cuando_el_banco_no_tiene_productos(self):
        tema = self.con_hoja_buena(self.tema("sin-productos"))
        paginas = self.tmp / "paginas"
        destino = escribir_paginas(paginas, "sin-productos", 0)
        for nombre in ("ficha",):
            (destino / (nombre + ".html")).unlink()
        (destino / "muestra.html").write_text((destino / "portada.html").read_text(encoding="utf-8"), encoding="utf-8")
        codigo, informe, texto = self.lanzar("movil", tema, paginas)
        self.aceptar(codigo, informe, texto, 0)


class PruebasDeLasFunciones(unittest.TestCase):
    def test_mirar_pagina_sin_cabecera(self):
        problemas = movil.mirar_pagina("portada", "<html><body><main>x</main></body></html>")
        self.assertTrue(any("no hay cabecera" in p for p in problemas))

    def test_mirar_hoja_sin_reglas_no_pasa(self):
        problemas, _hechas = movil.mirar_hoja("")
        self.assertTrue(problemas)


if __name__ == "__main__":
    unittest.main()
