"""AIFEC — fábrica de temas: pruebas del esqueleto, del skill y de los ejemplos que lo acompañan.

El esqueleto se convierte en un tema con sus marcas sustituidas; el skill tiene menos de 250 líneas, sus ocho
fases, las siete puertas y todos los ficheros que nombra; la cola de ejemplo trae tres encargos completos.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest

import ayudas_puertas as ap
from ayudas_puertas import BaseTemas, PROYECTO

SKILL = PROYECTO / "skill"


class PruebasEsqueleto(BaseTemas):
    def test_las_marcas_se_sustituyen_y_no_queda_ninguna(self):
        tema = self.tema("floristeria-petalo", "Floristería Pétalo")
        for ruta in tema.rglob("*"):
            if ruta.is_file():
                texto = ruta.read_text(encoding="utf-8")
                self.assertNotIn("__slug__", texto, ruta.name)
                self.assertNotIn("__Nombre__", texto, ruta.name)
                self.assertNotIn("{{", texto, ruta.name)
        manifiesto = json.loads((tema / "theme.json").read_text(encoding="utf-8"))
        self.assertEqual(manifiesto["name"], "Floristería Pétalo")
        self.assertEqual(manifiesto["parent"], "base")
        self.assertIn("floristeria-petalo", (tema / "assets" / "css" / "theme.css").read_text(encoding="utf-8"))

    def test_el_prefijo_de_clases_propias_sale_del_slug_y_el_esqueleto_no_deja_sk(self):
        tema = self.tema("bicicletas-rueda")
        hoja = (tema / "assets" / "css" / "theme.css").read_text(encoding="utf-8")
        self.assertIn(".br-header", hoja)
        self.assertNotRegex(hoja, r"(?<![A-Za-z0-9_-])sk-")
        self.assertNotRegex((tema / "templates" / "partials" / "header.php").read_text(encoding="utf-8"), r"(?<![A-Za-z0-9_-])sk-")

    def test_dos_temas_con_distinto_slug_no_comparten_prefijo(self):
        uno = self.tema("libreria-lectora")
        dos = self.tema("floristeria-petalo")
        prefijo_uno = set(re.findall(r"\.([a-z0-9]+)-header\b", (uno / "assets" / "css" / "theme.css").read_text(encoding="utf-8")))
        prefijo_dos = set(re.findall(r"\.([a-z0-9]+)-header\b", (dos / "assets" / "css" / "theme.css").read_text(encoding="utf-8")))
        self.assertTrue(prefijo_uno and prefijo_dos)
        self.assertTrue(prefijo_uno.isdisjoint(prefijo_dos), (prefijo_uno, prefijo_dos))

    def test_deja_la_tabla_de_descomposicion_como_notas_md_con_el_nombre_puesto(self):
        tema = self.tema("floristeria-petalo", "Floristería Pétalo")
        notas = (tema / "NOTAS.md").read_text(encoding="utf-8")
        self.assertIn("«Floristería Pétalo» (floristeria-petalo)", notas)
        for clase in ("af-header", "af-product-card", "af-listing", "af-product", "af-footer"):
            self.assertIn("`%s`" % clase, notas)

    def test_el_nombre_con_comillas_deja_un_json_valido(self):
        tema = self.tema("tema-comillas", 'Taller "Pepe" & hijos')
        manifiesto = json.loads((tema / "theme.json").read_text(encoding="utf-8"))
        self.assertEqual(manifiesto["name"], 'Taller "Pepe" & hijos')

    def test_rechaza_un_slug_mal_escrito_un_nombre_vacio_y_un_prefijo_que_choca(self):
        for slug, nombre, prefijo in (("Mala Idea", "x", ""), ("bien", "  ", ""), ("bien", "x", "af"), ("bien", "x", "sk"), ("bien", "x", "A!")):
            with self.subTest(slug=slug, nombre=nombre, prefijo=prefijo):
                with self.assertRaises(ValueError):
                    ap.esqueleto_mod.crear(slug, nombre, self.salida / "x", prefijo)

    def test_no_pisa_una_carpeta_que_ya_tiene_cosas_salvo_con_forzar(self):
        tema = self.tema("tema-existe")
        with self.assertRaises(ValueError):
            ap.esqueleto_mod.crear("tema-existe", "Otro", tema)
        ap.esqueleto_mod.crear("tema-existe", "Otro", tema, "", True)
        self.assertEqual(json.loads((tema / "theme.json").read_text(encoding="utf-8"))["name"], "Otro")

    def test_por_linea_de_ordenes_crea_el_tema_y_sale_con_cero(self):
        destino = self.tmp / "salida-linea" / "tema-linea"
        proceso = subprocess.run([sys.executable, str(SKILL / "esqueleto.py"), "tema-linea", "Tema línea", "--salida", str(destino)],
                                 stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(proceso.returncode, 0, proceso.stdout + proceso.stderr)
        self.assertTrue((destino / "theme.json").is_file())
        otra = subprocess.run([sys.executable, str(SKILL / "esqueleto.py"), "tema-linea", "Tema línea", "--salida", str(destino)],
                              stdin=subprocess.DEVNULL, capture_output=True, encoding="utf-8", errors="replace", timeout=60)
        self.assertEqual(otra.returncode, 2)

    def test_el_esqueleto_trae_las_cinco_superficies_las_clases_de_contrato_y_la_barra_de_movil_heredada(self):
        tema = self.tema("tema-superficies")
        for relativa, clase in (("templates/partials/header.php", "af-header"), ("templates/partials/product-card.php", "af-product-card"),
                                ("templates/modules/catalog/front/listing.php", "af-listing"), ("templates/modules/catalog/front/product.php", "af-product"),
                                ("templates/partials/footer.php", "af-footer")):
            texto = (tema / relativa).read_text(encoding="utf-8")
            self.assertRegex(texto, r'class="[^"]*\b%s\b' % clase, relativa)
        ficha = (tema / "templates/modules/catalog/front/product.php").read_text(encoding="utf-8")
        self.assertLess(ficha.index("af-product-gallery"), ficha.index("af-product-buy"), "galería antes que compra")
        for hueco in ("product.summary.before", "product.gallery.after", "product.price.after", "product.buy.after",
                      "product.summary.after", "product.tabs", "product.bottom"):
            self.assertIn("hook('%s'" % hueco, ficha, hueco)
        self.assertIn("data-af-cart-add", ficha)
        self.assertIn("data-af-variants-data", ficha)

    def test_el_esqueleto_no_trae_direcciones_ajenas_ni_bytes_raros(self):
        origen = PROYECTO / "plantillas" / "esqueleto"
        for ruta in origen.rglob("*"):
            if not ruta.is_file():
                continue
            crudo = ruta.read_bytes()
            self.assertFalse(crudo.startswith(b"\xef\xbb\xbf"), ruta.name)
            self.assertNotIn(b"\r\n", crudo, ruta.name)
            self.assertNotRegex(crudo.decode("utf-8"), r"https?://(?!www\.w3\.org)", ruta.name)
            if ruta.suffix == ".php":
                self.assertTrue(crudo.startswith(b"<?php\n/**"), ruta.name)


class PruebasSkill(unittest.TestCase):
    def setUp(self):
        self.texto = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_tiene_menos_de_250_lineas_y_cabecera_de_skill(self):
        self.assertLess(len(self.texto.splitlines()), 250)
        self.assertTrue(self.texto.startswith("---\nname: fabrica-temas-aifec\ndescription:"))

    def test_tiene_las_ocho_fases_en_orden(self):
        posiciones = []
        for numero in range(1, 9):
            encontrado = re.search(r"^### %d\. " % numero, self.texto, re.M)
            self.assertIsNotNone(encontrado, "falta la fase %d" % numero)
            posiciones.append(encontrado.start())
        self.assertEqual(posiciones, sorted(posiciones))

    def test_nombra_las_siete_puertas_con_su_medida(self):
        for puerta in ("validador", "estructura", "peso", "movil", "traducciones", "limpieza", "contrato", "capturas"):
            self.assertRegex(self.texto, r"\| `%s` \|" % puerta, puerta)
        for medida in ("0,82", "0,90", "45 000", "25 000", "150 000", "safe-area", "44 px"):
            self.assertIn(medida, self.texto, medida)

    def test_dice_lo_prohibido(self):
        for prohibido in ("Cambiar solo colores", "Invertir galería y compra", "Quitar huecos", "otro dominio", "Tocar el sistema"):
            self.assertIn(prohibido, self.texto, prohibido)

    def test_todos_los_ficheros_que_nombra_existen(self):
        nombrados = set(re.findall(r"`((?:skill|plantillas|docs|puertas)/[A-Za-z0-9_./-]+\.(?:md|py|php|json))`", self.texto))
        self.assertTrue(nombrados)
        for relativa in nombrados:
            self.assertTrue((PROYECTO / relativa).is_file(), relativa)

    def test_las_referencias_y_la_plantilla_de_descomposicion_existen_y_no_estan_vacias(self):
        for relativa in ("referencias/funciones.md", "referencias/clases.md", "referencias/huecos-y-datos.md", "referencias/fallos-frecuentes.md",
                         "plantillas/descomposicion.md"):
            ruta = SKILL / relativa
            self.assertTrue(ruta.is_file(), relativa)
            self.assertGreater(len(ruta.read_text(encoding="utf-8")), 500, relativa)

    def test_las_ordenes_que_cita_existen(self):
        fabrica = (PROYECTO / "fabrica.py").read_text(encoding="utf-8")
        for orden in ("encargo", "puertas", "banco"):
            self.assertIn('"%s"' % orden, fabrica)
        self.assertIn("--solo", fabrica)

    def test_la_tabla_de_descomposicion_trae_las_cinco_superficies(self):
        plantilla = (SKILL / "plantillas" / "descomposicion.md").read_text(encoding="utf-8")
        for clase in ("af-header", "af-product-card", "af-listing", "af-product", "af-footer"):
            self.assertIn("`%s`" % clase, plantilla)

    def test_los_tropiezos_del_skill_estan_apuntados_en_fallos_frecuentes(self):
        fallos = (SKILL / "referencias" / "fallos-frecuentes.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(len(re.findall(r"^## ", fallos, re.M)), 6)
        self.assertIn("Al seguir el skill con un encargo de ejemplo", fallos)


class PruebasColaDeEjemplo(unittest.TestCase):
    def test_trae_tres_encargos_distintos_y_completos(self):
        cola = json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))
        self.assertEqual(len(cola), 3)
        self.assertEqual(len({e["slug"] for e in cola}), 3)
        for encargo in cola:
            for campo in ("slug", "nombre", "sector", "publico", "idea", "referencias", "paleta", "tipografia", "superficies", "no_hacer"):
                self.assertTrue(encargo.get(campo), "%s: falta %s" % (encargo.get("slug"), campo))
            self.assertEqual(sorted(encargo["superficies"]), ["cabecera", "ficha", "listado", "pie", "tarjeta"])
            self.assertRegex(encargo["slug"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
            self.assertTrue(all(url.startswith("https://ejemplo.test/") for url in encargo["referencias"]))

    def test_la_cola_de_ejemplo_la_acepta_la_fabrica(self):
        sys.path.insert(0, str(PROYECTO))
        from motor import cola
        self.assertEqual(cola.validar(json.loads((PROYECTO / "cola.ejemplo.json").read_text(encoding="utf-8"))), [])


if __name__ == "__main__":
    unittest.main()
