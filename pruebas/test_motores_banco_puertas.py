"""AIFEC — fábrica: pruebas de los motores, el banco de pruebas y las puertas.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from ayudas import Base, esperar
from motor import banco, motores, nucleo, procesos, puertas


def _arbol(carpeta: Path) -> dict:
    return {p.relative_to(carpeta).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in carpeta.rglob("*") if p.is_file()}


class PruebasMotores(Base):
    def test_el_motor_manual_deja_el_encargo_escrito_y_espera(self):
        self.montar(motor="manual")
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "espera")
        self.assertIn("estado/encargos/uno.encargo.md", mensaje)
        self.assertEqual(self.estado_de("uno"), "en_curso")
        texto = (self.raiz / "estado" / "encargos" / "uno.encargo.md").read_text(encoding="utf-8")
        self.assertIn("Encargo: Encargo uno (uno)", texto)
        self.assertIn("python fabrica.py puertas uno", texto)
        self.assertIn("**idea**: idea de uno", texto)

    def test_el_motor_manual_al_volver_a_lanzar_le_pasa_las_puertas_a_lo_que_haya(self):
        self.montar(motor="manual")
        ctx = self.abrir()
        nucleo.ciclo(ctx, "uno")
        (self.raiz / "salida" / "uno" / "theme.json").write_text(json.dumps({"name": "A mano"}), encoding="utf-8")
        resultado, _ = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "hecho")
        self.assertEqual(self.estado_de("uno"), "hecho")

    def test_el_motor_simulado_copia_el_trabajo_de_origen(self):
        self.montar()
        ctx = self.abrir()
        resultado = motores.ejecutar(ctx, "uno", self.raiz / "x.md", "")
        self.assertEqual(resultado.estado, "listo")
        self.assertTrue((self.raiz / "salida" / "uno" / "theme.json").is_file())
        self.assertTrue((self.raiz / "salida" / "uno" / "contenido.txt").is_file())

    def test_las_marcas_de_la_orden_se_sustituyen_en_una_sola_pasada(self):
        self.montar(motor="orden")
        crudo = json.loads((self.raiz / "plan.json").read_text(encoding="utf-8"))
        crudo["motor"]["orden"] = crudo["motor"]["orden"][:3] + ["{fabrica}", "{encargo}", "{texto}"]
        (self.raiz / "plan.json").write_text(json.dumps(crudo), encoding="utf-8")
        self.modo("motor", "marcas")
        ctx = self.abrir()
        self.assertEqual(nucleo.ciclo(ctx, "uno")[0], "hecho")
        datos = json.loads((self.control / "argv.json").read_text(encoding="utf-8"))
        trabajo, fabrica, encargo, texto = datos["argv"][0], datos["argv"][1], datos["argv"][2], datos["argv"][3]
        self.assertEqual(Path(trabajo), self.raiz / "salida" / "uno")
        self.assertEqual(Path(datos["cwd"]), self.raiz / "salida" / "uno")
        self.assertEqual(Path(fabrica), self.raiz)
        self.assertTrue(encargo.endswith("uno.encargo.md"))
        self.assertTrue(Path(encargo).is_file())
        self.assertTrue(texto.startswith("# Encargo: Encargo uno"))
        # Una marca dentro del contenido de otra no se vuelve a sustituir.
        self.assertEqual(motores.sustituir(["{texto}"], {"texto": "{trabajo}", "trabajo": "X", "encargo": "",
                                                          "fabrica": ""}), ["{trabajo}"])

    def test_la_orden_que_se_pasa_del_tiempo_se_corta_con_todos_sus_hijos(self):
        self.montar(motor="orden", plan={"intentos": 1})
        crudo = json.loads((self.raiz / "plan.json").read_text(encoding="utf-8"))
        crudo["motor"]["minutos"] = 0.06
        (self.raiz / "plan.json").write_text(json.dumps(crudo), encoding="utf-8")
        self.modo("motor", "dormir")
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "atascado")
        self.assertIn("se pasó del tiempo", mensaje)
        for nombre in ("motor.pid", "hijo.pid"):
            pid = int((self.control / nombre).read_text())
            self.assertTrue(esperar(lambda: not procesos.vivo(pid), 5), "%s sigue vivo" % nombre)

    def test_una_orden_que_escribe_fuera_de_su_carpeta_rechaza_el_encargo(self):
        self.montar(motor="orden", plan={"intentos": 1})
        self.modo("motor", "intruso")
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "atascado")
        self.assertIn("escribió fuera de salida/uno/", mensaje)
        self.assertIn("intruso.txt", mensaje)
        self.assertEqual(self.estado_de("uno"), "atascado")

    def test_una_orden_que_sale_con_error_rechaza_el_intento(self):
        self.montar(motor="orden", plan={"intentos": 3})
        self.modo("motor", "falla")
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "rechazado")
        self.assertIn("código 3", mensaje)

    def test_con_tope_cero_el_motor_de_pago_no_se_lanza(self):
        self.montar(motor="orden", plan={"gasto": {"tope_eur": 0, "por_sesion_eur": 0}})
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "tope")
        self.assertIn("tope de gasto", mensaje)
        self.assertFalse((self.control / "marcador.txt").exists(), "el motor se lanzó con el tope a 0")
        self.assertEqual(self.estado_de("uno"), "pendiente", "el encargo tiene que quedar como estaba")
        self.assertEqual(ctx.cola.estado("uno")["intentos"], 0)
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 3)
        self.assertIn("tope de gasto", linea)

    def test_con_tope_uno_y_sesion_a_sesenta_centimos_la_segunda_no_se_lanza(self):
        self.montar(motor="orden", encargos=("uno", "dos"), plan={"gasto": {"tope_eur": 1, "por_sesion_eur": 0.6}})
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 3, linea)
        self.assertEqual(self.estado_de("uno"), "hecho")
        self.assertEqual(self.estado_de("dos"), "pendiente")
        self.assertEqual(ctx.libro.gastado(), 0.6)
        self.assertEqual(len(ctx.libro.sesiones()), 1)

    def test_el_coste_real_de_la_sesion_puede_salir_de_su_salida(self):
        self.montar(motor="orden", plan={"gasto": {"tope_eur": 5, "por_sesion_eur": 1}})
        crudo = json.loads((self.raiz / "plan.json").read_text(encoding="utf-8"))
        crudo["motor"]["coste_regex"] = r"coste ([0-9,.]+)"
        (self.raiz / "plan.json").write_text(json.dumps(crudo), encoding="utf-8")
        (self.control / "coste.txt").write_text("coste 0,25")
        ctx = self.abrir()
        nucleo.ciclo(ctx, "uno")
        self.assertEqual(ctx.libro.gastado(), 0.25)
        self.assertEqual(len(ctx.libro.sesiones()), 2, "la reserva y su corrección")

    def test_la_instantanea_ignora_lo_permitido_y_ve_lo_demas(self):
        self.montar()
        ctx = self.abrir()
        antes = motores.instantanea(ctx, "uno")
        (self.raiz / "salida" / "uno").mkdir(parents=True)
        (self.raiz / "salida" / "uno" / "a.txt").write_text("a")
        (self.raiz / "estado").mkdir(exist_ok=True)
        (self.raiz / "estado" / "b.txt").write_text("b")
        (self.raiz / "escaparate").mkdir(exist_ok=True)
        (self.raiz / "escaparate" / "c.txt").write_text("c")
        self.assertEqual(motores.diferencias(antes, motores.instantanea(ctx, "uno")), [])
        (self.raiz / "puertas" / "dos.py").write_text("# cambiado")
        (self.raiz / "otro.txt").write_text("nuevo")
        (self.raiz / "salida" / "ajeno").mkdir()
        (self.raiz / "salida" / "ajeno" / "x.txt").write_text("de otro encargo")
        cambios = motores.diferencias(antes, motores.instantanea(ctx, "uno"))
        self.assertEqual(sorted(cambios), ["cambiado: puertas/dos.py", "nuevo: otro.txt", "nuevo: salida/ajeno/x.txt"])


class PruebasBanco(Base):
    def setUp(self):
        super().setUp()
        self.montar()
        sistema = self.tmp / "sistema"
        for carpeta, fichero in (("sites", "dato.txt"), ("storage", "dato.txt"), (".git", "HEAD"),
                                 ("cache", "c.txt"), ("core/src/Cache", "Clase.php"), ("themes/base", "theme.json")):
            (sistema / carpeta).mkdir(parents=True, exist_ok=True)
            (sistema / carpeta / fichero).write_text("x")
        (sistema / "data-path.php").write_text("<?php return 'datos-reales';")
        self.ctx = self.abrir()

    def test_el_banco_copia_el_sistema_sin_sus_datos_ni_cachas_ni_git(self):
        banco.preparar(self.ctx)
        copia = self.raiz / "estado" / "banco"
        self.assertTrue((copia / "core" / "bootstrap.php").is_file())
        self.assertTrue((copia / "themes" / "base" / "theme.json").is_file())
        self.assertTrue((copia / "core" / "src" / "Cache" / "Clase.php").is_file(),
                        "una carpeta Cache dentro del código no es una caché de datos")
        for fuera in ("storage", ".git", "cache", "data-path.php"):
            self.assertFalse((copia / fuera).exists(), fuera)
        self.assertFalse((copia / "sites" / "dato.txt").exists())

    def test_el_banco_crea_su_propio_sitio_con_las_ordenes_del_sistema(self):
        resultado = banco.preparar(self.ctx)
        self.assertTrue(resultado["sitio"])
        llamadas = [json.loads(l) for l in (self.raiz / "estado" / "banco" / "argv.log").read_text().splitlines()]
        sitio = [l for l in llamadas if l[0] == "site:create"][0]
        self.assertIn("--db=sqlite", sitio)
        self.assertEqual(sitio[1], "banco")
        self.assertTrue((self.raiz / "estado" / "banco" / "sites" / "banco").is_dir())

    def test_toda_orden_del_banco_fuerza_los_datos_dentro_del_banco(self):
        banco.preparar(self.ctx)
        banco.orden_php(self.ctx, ["i18n:check", "themes/x"])
        ultima = json.loads((self.raiz / "estado" / "banco" / "argv.log").read_text().splitlines()[-1])
        self.assertEqual(ultima[0], "i18n:check")
        datos = [a for a in ultima if a.startswith("--data=")][0]
        self.assertEqual(Path(datos[len("--data="):]), self.raiz / "estado" / "banco" / "sites")

    def test_la_instalacion_de_origen_no_se_toca(self):
        antes = _arbol(self.tmp / "sistema")
        banco.preparar(self.ctx)
        banco.orden_php(self.ctx, ["theme:check", "x"])
        self.assertEqual(_arbol(self.tmp / "sistema"), antes)

    def test_si_no_cambia_nada_el_banco_no_se_rehace_y_si_cambia_la_version_si(self):
        self.assertTrue(banco.preparar(self.ctx)["rehecho"])
        marca = self.raiz / "estado" / "banco" / "marca.txt"
        marca.write_text("m")
        self.assertFalse(banco.preparar(self.ctx)["rehecho"])
        self.assertTrue(marca.exists())
        (self.tmp / "sistema" / "VERSION").write_text("1.0.1")
        self.assertTrue(banco.preparar(self.ctx)["rehecho"])
        self.assertFalse(marca.exists())

    def test_el_banco_se_rehace_si_cambia_el_core_o_si_se_pide(self):
        banco.preparar(self.ctx)
        marca = self.raiz / "estado" / "banco" / "marca.txt"
        marca.write_text("m")
        nuevo = self.tmp / "sistema" / "core" / "nuevo.php"
        nuevo.write_text("<?php")
        self.assertTrue(banco.preparar(self.ctx)["rehecho"])
        marca.write_text("m")
        self.assertTrue(banco.preparar(self.ctx, rehacer=True)["rehecho"])
        self.assertFalse(marca.exists())

    def test_si_el_sistema_no_trae_la_orden_lo_dice_y_sigue(self):
        self.modo("aifec", "sin_site")
        resultado = banco.preparar(self.ctx)
        self.assertFalse(resultado["sitio"])
        self.assertTrue(any("no creó el sitio" in m for m in resultado["mensajes"]), resultado["mensajes"])
        self.assertTrue((self.raiz / "estado" / "banco" / "aifec").is_file())

    def test_instalar_copia_el_candidato_a_la_carpeta_de_su_clase_del_banco(self):
        banco.preparar(self.ctx)
        candidato = self.raiz / "salida" / "uno"
        candidato.mkdir(parents=True)
        (candidato / "theme.json").write_text("{}")
        destino = banco.instalar(self.ctx, "uno")
        self.assertEqual(destino, self.raiz / "estado" / "banco" / "themes" / "uno")
        self.assertTrue((destino / "theme.json").is_file())
        (candidato / "nuevo.txt").write_text("n")
        banco.instalar(self.ctx, "uno")
        self.assertTrue((destino / "nuevo.txt").is_file())
        with self.assertRaises(RuntimeError):
            banco.instalar(self.ctx, "no-existe")

    def test_el_esqueleto_se_pide_a_aifec_con_la_orden_de_fabrica_json(self):
        banco.preparar(self.ctx)
        hecho, mensaje = banco.esqueleto(self.ctx, "uno", "Mi tema")
        self.assertTrue(hecho, mensaje)
        self.assertTrue((self.raiz / "salida" / "uno" / "esqueleto.txt").is_file())
        llamada = [json.loads(l) for l in (self.raiz / "estado" / "banco" / "argv.log").read_text().splitlines()
                   if l.startswith('["theme:create"')][0]
        self.assertEqual(llamada[:4], ["theme:create", "uno", "--parent=base", "--name=Mi tema"])

    def test_si_aifec_no_sabe_hacer_el_esqueleto_el_motor_empieza_de_cero(self):
        banco.preparar(self.ctx)
        self.modo("aifec", "sin_esqueleto")
        hecho, mensaje = banco.esqueleto(self.ctx, "uno", "Mi tema")
        self.assertFalse(hecho)
        self.assertIn("no creó el esqueleto", mensaje)


class PruebasPuertas(Base):
    def setUp(self):
        super().setUp()
        self.montar(puertas=("uno", "dos", "tres"))
        candidato = self.raiz / "salida" / "x"
        candidato.mkdir(parents=True)
        (candidato / "theme.json").write_text("{}")
        self.ctx = self.abrir()

    def _estados(self, informe):
        return {p["nombre"]: p["estado"] for p in informe["puertas"]}

    def test_todas_pasan(self):
        informe = puertas.lanzar(self.ctx, "x")
        self.assertTrue(informe["pasa"])
        self.assertEqual(informe["linea"], "PUERTAS: 3 de 3 pasan")
        self.assertTrue((self.raiz / "estado" / "encargos" / "x.puertas.json").is_file())

    def test_una_puerta_con_uno_no_pasa(self):
        self.modo("dos", "1")
        informe = puertas.lanzar(self.ctx, "x")
        self.assertFalse(informe["pasa"])
        self.assertEqual(self._estados(informe)["dos"], "no_pasa")
        self.assertEqual(informe["linea"], "PUERTAS: 2 de 3 pasan, 1 no pasan")

    def test_una_puerta_con_dos_no_aplica_y_no_bloquea(self):
        self.modo("tres", "2")
        informe = puertas.lanzar(self.ctx, "x")
        self.assertTrue(informe["pasa"])
        self.assertEqual(self._estados(informe)["tres"], "no_aplica")
        self.assertIn("1 no aplican", informe["linea"])

    def test_una_puerta_que_no_existe_no_pasa(self):
        (self.raiz / "puertas" / "tres.py").unlink()
        informe = puertas.lanzar(self.ctx, "x")
        self.assertFalse(informe["pasa"])
        self.assertEqual(self._estados(informe)["tres"], "no_pasa")
        self.assertIn("no existe", [p for p in informe["puertas"] if p["nombre"] == "tres"][0]["resumen"])

    def test_una_puerta_que_revienta_no_pasa(self):
        self.modo("uno", "crash")
        informe = puertas.lanzar(self.ctx, "x")
        self.assertFalse(informe["pasa"])
        entrada = [p for p in informe["puertas"] if p["nombre"] == "uno"][0]
        self.assertEqual(entrada["estado"], "no_pasa")
        self.assertIn("reventó", entrada["resumen"])

    def test_una_puerta_que_no_deja_informe_no_pasa(self):
        self.modo("uno", "sin_informe")
        informe = puertas.lanzar(self.ctx, "x")
        entrada = [p for p in informe["puertas"] if p["nombre"] == "uno"][0]
        self.assertEqual(entrada["estado"], "no_pasa")
        self.assertIn("no dejó informe", entrada["resumen"])

    def test_solo_lanza_las_puertas_pedidas(self):
        informe = puertas.lanzar(self.ctx, "x", ["dos"])
        self.assertEqual([p["nombre"] for p in informe["puertas"]], ["dos"])

    def test_las_puertas_reciben_la_interfaz_del_contrato(self):
        puertas.lanzar(self.ctx, "x", ["uno"])
        informe = json.loads((self.raiz / "estado" / "sesiones" / "x.uno.informe.json").read_text(encoding="utf-8"))
        self.assertEqual(informe["puerta"], "uno")
        self.assertEqual(informe["medidas"], {"n": 1})
        self.assertTrue((self.raiz / "estado" / "banco" / "themes" / "x" / "theme.json").is_file(),
                        "el candidato tiene que estar instalado en el banco")


if __name__ == "__main__":
    unittest.main()
