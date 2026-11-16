"""AIFEC — fábrica de temas: prueba de punta a punta, con el sistema real.

Con el motor `simulado` y el esqueleto convertido en un tema como origen, `python fabrica.py trabajar --uno` tiene que
dejar el encargo en `hecho`, con su ficha, las siete puertas en el informe (la de capturas, «no aplica») y **el banco
intacto fuera de `themes/<slug>`** (y de los datos de su sitio, donde se carga la demostración: `sites/` y `public/media/`): la fábrica no ensucia
nada más. Y la instalación de origen **no ha cambiado**: instantánea de fechas y tamaños de toda su carpeta antes y
después. Se salta sola si `AIFEC_RUTA` no apunta a una instalación o no hay un PHP con SQLite.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import ayudas_puertas as ap
from ayudas_puertas import FabricaReal, arbol, sistema_disponible

SLUG = "floristeria-prueba"


@unittest.skipUnless(sistema_disponible(), "hace falta AIFEC_RUTA (una instalación de AIFEC) y un PHP con SQLite")
class PruebaDePuntaAPunta(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fab = FabricaReal()
        cls.fab.preparar_banco()
        origen = cls.fab.raiz / "origen" / SLUG
        ap.esqueleto_mod.crear(SLUG, "Floristería de prueba", origen)
        cls.fab.escribir_plan({"motor": {"tipo": "simulado", "origen": str(origen)}})
        (cls.fab.raiz / "cola.json").write_text(json.dumps([
            {"slug": SLUG, "nombre": "Floristería de prueba", "sector": "pruebas", "idea": "idea de prueba"}]), encoding="utf-8")
        # instantáneas de antes
        cls.origen_antes = arbol(Path(ap.AIFEC_RUTA))
        cls.ignorar = ("themes/" + SLUG, "sites", "public/media")
        cls.banco_antes = arbol(cls.fab.banco, ignorar=cls.ignorar)
        cls.codigo, cls.texto = cls.fab.fabrica("trabajar", "--uno")
        cls.origen_despues = arbol(Path(ap.AIFEC_RUTA))
        cls.banco_despues = arbol(cls.fab.banco, ignorar=cls.ignorar)

    @classmethod
    def tearDownClass(cls):
        cls.fab.borrar()

    def estado(self):
        return json.loads((self.fab.raiz / "estado" / "encargos" / (SLUG + ".json")).read_text(encoding="utf-8"))

    def test_el_encargo_queda_hecho(self):
        self.assertEqual(self.codigo, 0, self.texto)
        self.assertEqual(self.estado()["estado"], "hecho", self.texto)
        self.assertIn("HECHO", self.texto.upper())

    def test_deja_su_ficha_en_el_escaparate_con_las_puertas_pasadas(self):
        ficha = json.loads((self.fab.raiz / "escaparate" / SLUG / "ficha.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["estado"], "hecho")
        self.assertNotEqual(ficha["estado"], "aprobado", "lo que nadie ha mirado no se llama aprobado")
        self.assertTrue((self.fab.raiz / "escaparate" / "index.html").is_file())

    def test_el_informe_trae_las_siete_puertas_seis_pasan_y_capturas_no_aplica(self):
        informe = json.loads((self.fab.raiz / "estado" / "encargos" / (SLUG + ".puertas.json")).read_text(encoding="utf-8"))
        estados = {p["nombre"]: p["estado"] for p in informe["puertas"]}
        self.assertEqual(sorted(estados), sorted(["validador", "estructura", "peso", "movil", "traducciones", "limpieza", "contrato", "capturas"]))
        self.assertEqual(estados["capturas"], "no_aplica")
        for puerta in ("validador", "estructura", "peso", "movil", "traducciones", "limpieza", "contrato"):
            self.assertEqual(estados[puerta], "pasa", "%s: %s" % (puerta, informe["puertas"]))
        self.assertTrue(informe["pasa"])

    def test_el_tema_esta_en_salida_y_en_el_banco(self):
        self.assertTrue((self.fab.raiz / "salida" / SLUG / "theme.json").is_file())
        self.assertTrue((self.fab.banco / "themes" / SLUG / "theme.json").is_file())

    def test_el_banco_queda_intacto_fuera_de_su_tema_y_de_sus_datos(self):
        # lo único que se escribe fuera de themes/<slug> son los DATOS del sitio del banco: su base de datos y caché
        # (sites/) y los medios de la demostración que se carga para tener productos que pintar (public/media/)
        diferencias = sorted(k for k in set(self.banco_antes) | set(self.banco_despues) if self.banco_antes.get(k) != self.banco_despues.get(k))
        self.assertEqual(diferencias, [])

    def test_la_instalacion_de_origen_no_ha_cambiado(self):
        diferencias = sorted(k for k in set(self.origen_antes) | set(self.origen_despues) if self.origen_antes.get(k) != self.origen_despues.get(k))
        self.assertEqual(diferencias[:10], [], "%d ficheros distintos en la instalación de origen" % len(diferencias))

    def test_los_otros_temas_del_banco_no_se_tocan(self):
        for nombre in ("base", "taller", "atelier", "despensa"):
            self.assertTrue(any(k.startswith("themes/%s/" % nombre) for k in self.banco_despues), nombre)


if __name__ == "__main__":
    unittest.main()
