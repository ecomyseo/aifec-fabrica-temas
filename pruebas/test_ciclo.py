"""AIFEC — fábrica: pruebas del ciclo de un encargo, el trabajo de cada día y la orden única.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from ayudas import Base, esperar
from motor import estado, nucleo, procesos


class PruebasCicloFeliz(Base):
    def _feliz(self, clase):
        self.montar(clase=clase)
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 0, linea)
        datos = ctx.cola.estado("uno")
        self.assertEqual(datos["estado"], "hecho")
        self.assertEqual([h["a"] for h in datos["historial"]], ["en_curso", "en_puertas", "hecho"])
        manifiesto = ctx.config["manifiesto"]
        self.assertTrue((self.raiz / "salida" / "uno" / manifiesto).is_file())
        ficha = json.loads((self.raiz / "escaparate" / "uno" / "ficha.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["estado"], "hecho")
        self.assertEqual(ficha["clase"], clase)
        self.assertEqual(ficha["intentos"], 1)
        self.assertEqual(ficha["motor"], "simulado")
        self.assertEqual([p["nombre"] for p in ficha["puertas"]], ["uno", "dos"])
        self.assertEqual(ficha["puertas"][0]["medidas"], {"n": 1})
        indice = (self.raiz / "escaparate" / "index.html").read_text(encoding="utf-8")
        self.assertIn("uno", indice)
        self.assertIn("1 pasan las puertas · 0 aprobados", indice)
        self.assertFalse((self.raiz / "estado" / "fabrica.lock").exists(), "el cerrojo tiene que quedar suelto")
        self.assertIn("1 hechos", linea)

    def test_encargo_feliz_de_una_fabrica_de_temas(self):
        self._feliz("temas")

    def test_la_misma_bateria_con_la_configuracion_de_una_fabrica_de_plugins(self):
        self._feliz("plugins")

    def test_el_esqueleto_sale_de_la_orden_de_fabrica_json(self):
        self.montar(clase="plugins", motor="manual")
        ctx = self.abrir()
        nucleo.ciclo(ctx, "uno")
        self.assertTrue((self.raiz / "salida" / "uno" / "plugin.json").is_file())
        llamadas = (self.raiz / "estado" / "banco" / "argv.log").read_text(encoding="utf-8")
        self.assertIn('"plugin:create", "uno", "--name=Encargo uno"', llamadas)

    def test_aprobar_y_rechazar_a_mano(self):
        self.montar(encargos=("uno", "dos"))
        ctx = self.abrir()
        nucleo.trabajar(ctx)
        nucleo.aprobar(ctx, "uno")
        self.assertEqual(self.estado_de("uno"), "aprobado")
        ficha = json.loads((self.raiz / "escaparate" / "uno" / "ficha.json").read_text(encoding="utf-8"))
        self.assertEqual(ficha["estado"], "aprobado")
        final = nucleo.rechazar_a_mano(ctx, "dos", "no me gusta la cabecera")
        self.assertEqual(final, "rechazado")
        self.assertIn("no me gusta la cabecera", ctx.cola.estado("dos")["motivo"])
        self.assertFalse((self.raiz / "escaparate" / "dos" / "ficha.json").exists())
        self.assertEqual(ctx.cola.siguiente(3), "dos", "el rechazado vuelve a la cola")

    def test_el_escaparate_separa_los_que_pasan_de_los_aprobados(self):
        self.montar(encargos=("uno", "dos"))
        ctx = self.abrir()
        nucleo.trabajar(ctx)
        nucleo.aprobar(ctx, "dos")
        indice = (self.raiz / "escaparate" / "index.html").read_text(encoding="utf-8")
        pasan = indice.index("Pasan las puertas")
        aprobados = indice.index("<h2>Aprobados</h2>")
        self.assertIn("1 pasan las puertas · 1 aprobados", indice)
        self.assertTrue(pasan < indice.index("<h3>Encargo uno</h3>") < aprobados)
        self.assertTrue(aprobados < indice.index("<h3>Encargo dos</h3>"))
        self.assertNotIn("http", indice, "la página no depende de nada de fuera")

    def test_un_candidato_sin_manifiesto_se_rechaza(self):
        self.montar(plan={"intentos": 1})
        for fichero in (self.tmp / "origen").glob("theme.json"):
            fichero.unlink()
        self.modo("aifec", "sin_esqueleto")
        ctx = self.abrir()
        resultado, mensaje = nucleo.ciclo(ctx, "uno")
        self.assertEqual(resultado, "atascado")
        self.assertIn("falta theme.json", mensaje)


class PruebasReintentos(Base):
    def test_las_puertas_que_fallan_rechazan_y_el_reintento_lleva_el_motivo(self):
        self.montar(plan={"puertas": ["uno"]}, puertas=("uno",))
        self.modo("uno", "contador")
        (self.control / "uno.fallos").write_text("2")
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 0, linea)
        datos = ctx.cola.estado("uno")
        self.assertEqual(datos["estado"], "hecho")
        self.assertEqual(datos["intentos"], 3)
        self.assertEqual([h["a"] for h in datos["historial"]].count("rechazado"), 2)
        texto = (self.raiz / "estado" / "encargos" / "uno.encargo.md").read_text(encoding="utf-8")
        self.assertIn("intento número 3", texto)
        self.assertIn("motivo-de-prueba", texto, "el nuevo encargo tiene que llevar lo que falló")
        self.assertIn("puerta `uno`", texto)

    def test_el_primer_encargo_dice_que_no_hay_nada_anterior(self):
        self.montar()
        ctx = self.abrir()
        ctx.cola.comenzar_intento("uno")
        self.assertIn("Nada: es el primer intento.", nucleo.construir_encargo(ctx, "uno"))

    def test_al_tercer_intento_queda_atascado(self):
        self.montar(plan={"puertas": ["uno"]}, puertas=("uno",))
        self.modo("uno", "1")
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        datos = ctx.cola.estado("uno")
        self.assertEqual(datos["estado"], "atascado")
        self.assertEqual(datos["intentos"], 3)
        self.assertEqual(codigo, 1, "un atascado es «algo no pasa»")
        self.assertIn("1 atascados", linea)
        self.assertEqual((self.control / "llamadas.log").read_text().count("uno:uno"), 3)

    def test_dos_atascados_seguidos_paran_con_codigo_4_y_la_cola_sigue_intacta(self):
        self.montar(encargos=("a", "b", "c"), puertas=("uno",), plan={"puertas": ["uno"], "intentos": 1})
        self.modo("uno", "1")
        cola_antes = (self.raiz / "cola.json").read_text(encoding="utf-8")
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 4, linea)
        self.assertEqual((self.estado_de("a"), self.estado_de("b"), self.estado_de("c")),
                         ("atascado", "atascado", "pendiente"))
        self.assertEqual((self.raiz / "cola.json").read_text(encoding="utf-8"), cola_antes)
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 4, "sigue parada hasta que alguien la reanude")
        self.assertEqual(self.estado_de("c"), "pendiente")
        nucleo.reanudar(ctx)
        self.modo("uno", "0")
        codigo, _ = nucleo.trabajar(ctx)
        self.assertEqual(self.estado_de("c"), "hecho")
        self.assertEqual(codigo, 0)

    def test_un_hecho_entre_dos_atascados_reinicia_la_racha(self):
        self.montar(encargos=("a", "b", "c"), puertas=("uno",), plan={"puertas": ["uno"], "intentos": 1})
        self.modo("uno.a", "1")
        self.modo("uno.c", "1")
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual((self.estado_de("a"), self.estado_de("b"), self.estado_de("c")),
                         ("atascado", "hecho", "atascado"))
        self.assertEqual(codigo, 1, linea)

    def test_al_atascarse_se_lanza_el_aviso_del_plan(self):
        orden = [sys.executable, str(self.control / "avisador.py"), "{mensaje}"]
        self.montar(puertas=("uno",), plan={"puertas": ["uno"], "intentos": 1, "aviso": {"orden": orden}})
        self.modo("uno", "1")
        ctx = self.abrir()
        nucleo.trabajar(ctx)
        avisos = (self.control / "avisos.txt").read_text(encoding="utf-8")
        self.assertIn("se ha atascado", avisos)
        self.assertIn("uno", avisos)

    def test_sin_orden_de_aviso_no_se_avisa_a_nadie(self):
        self.montar(puertas=("uno",), plan={"puertas": ["uno"], "intentos": 1})
        self.modo("uno", "1")
        nucleo.trabajar(self.abrir())
        self.assertFalse((self.control / "avisos.txt").exists())


class PruebasCupoYHorario(Base):
    def test_con_dos_por_dia_y_cinco_encargos_hoy_hace_dos(self):
        self.montar(encargos=("a", "b", "c", "d", "e"), plan={"por_dia": 2})
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 0, linea)
        self.assertEqual([self.estado_de(s) for s in "abcde"], ["hecho", "hecho", "pendiente", "pendiente", "pendiente"])
        self.assertIn("cupo de hoy cubierto", linea)
        codigo, linea = nucleo.trabajar(ctx)
        self.assertIn("cupo de hoy cubierto", linea)
        self.assertEqual(self.estado_de("c"), "pendiente", "una segunda vuelta el mismo día no hace más")

    def test_al_dia_siguiente_hace_otros_dos_y_un_dia_sin_lanzar_no_gasta_plan(self):
        self.montar(encargos=("a", "b", "c", "d", "e"), plan={"por_dia": 2})
        ctx = self.abrir()
        nucleo.trabajar(ctx)
        self.reloj.avanzar(days=9)  # nueve días sin lanzar la fábrica
        nucleo.trabajar(ctx)
        self.assertEqual([self.estado_de(s) for s in "abcde"], ["hecho", "hecho", "hecho", "hecho", "pendiente"])

    def test_fuera_de_horario_no_empieza_ninguno(self):
        self.montar(plan={"horario": {"inicio": "11:00", "fin": "12:00"}})
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 0)
        self.assertIn("fuera de horario", linea)
        self.assertEqual(self.estado_de("uno"), "pendiente")
        self.reloj.avanzar(hours=1, minutes=30)
        nucleo.trabajar(ctx)
        self.assertEqual(self.estado_de("uno"), "hecho")

    def test_parar_no_empieza_otro_y_reanudar_sigue(self):
        self.montar(encargos=("a", "b"))
        ctx = self.abrir()
        nucleo.parar(ctx)
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual((self.estado_de("a"), self.estado_de("b")), ("pendiente", "pendiente"))
        self.assertIn("en pausa", linea)
        nucleo.reanudar(ctx)
        nucleo.trabajar(ctx)
        self.assertEqual((self.estado_de("a"), self.estado_de("b")), ("hecho", "hecho"))

    def test_parar_deja_terminar_el_que_esta_y_no_empieza_otro(self):
        self.montar(encargos=("a", "b"), motor="orden")
        self.modo("motor", "parar")  # el motor pide parar mientras trabaja
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual((self.estado_de("a"), self.estado_de("b")), ("hecho", "pendiente"), linea)
        self.assertIn("paro: parar", linea)

    def test_con_activo_false_sale_sin_hacer_nada(self):
        self.montar(plan={"activo": False})
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx)
        self.assertEqual(codigo, 0)
        self.assertIn("inactiva", linea)
        self.assertEqual(self.estado_de("uno"), "pendiente")
        self.assertFalse((self.raiz / "estado" / "fabrica.lock").exists())

    def test_trabajar_con_slug_ignora_horario_y_cupo_pero_solo_hace_ese(self):
        self.montar(encargos=("a", "b"), plan={"horario": {"inicio": "11:00", "fin": "12:00"}, "por_dia": 1})
        ctx = self.abrir()
        codigo, linea = nucleo.trabajar(ctx, slug="b")
        self.assertEqual((self.estado_de("a"), self.estado_de("b")), ("pendiente", "hecho"), linea)

    def test_uno_hace_un_solo_encargo(self):
        self.montar(encargos=("a", "b"))
        nucleo.trabajar(self.abrir(), uno=True)
        self.assertEqual((self.estado_de("a"), self.estado_de("b")), ("hecho", "pendiente"))


class PruebasCortes(Base):
    def test_un_corte_durante_el_motor_se_reanuda_sin_repetir_desde_cero(self):
        self.montar(motor="orden")
        self.modo("motor", "lento_corte")
        primera = self.cli_en_segundo_plano("trabajar")
        self.assertTrue(esperar(lambda: (self.control / "motor.pid").exists(), 40), "el motor no llegó a arrancar")
        self.assertEqual(self.estado_de("uno"), "en_curso")
        primera.kill()
        primera.wait(timeout=10)
        procesos.matar_arbol(int((self.control / "motor.pid").read_text()))
        self.assertTrue((self.raiz / "estado" / "fabrica.lock").exists(), "el cerrojo del proceso muerto queda")
        self.assertEqual(self.estado_de("uno"), "en_curso", "un corte no cuenta como hecho")
        codigo, salida = self.cli("trabajar")
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.estado_de("uno"), "hecho")
        salida_uno = self.raiz / "salida" / "uno"
        self.assertTrue((salida_uno / "parte1.txt").is_file(), "lo que ya había se conserva")
        self.assertTrue((salida_uno / "parte2.txt").is_file())
        self.assertEqual(len((salida_uno / "ejecuciones.txt").read_text().splitlines()), 2)
        datos = json.loads((self.raiz / "estado" / "encargos" / "uno.json").read_text(encoding="utf-8"))
        self.assertEqual(datos["intentos"], 1, "reanudar no gasta un intento")

    def test_un_corte_durante_las_puertas_no_repite_el_motor(self):
        self.montar(motor="orden", puertas=("uno", "dos"))
        self.modo("uno", "lenta")
        primera = self.cli_en_segundo_plano("trabajar")
        self.assertTrue(esperar(lambda: (self.control / "puerta.pid").exists(), 40), "la puerta no llegó a arrancar")
        self.assertEqual(self.estado_de("uno"), "en_puertas")
        primera.kill()
        primera.wait(timeout=10)
        procesos.matar_arbol(int((self.control / "puerta.pid").read_text()))
        self.assertEqual(self.estado_de("uno"), "en_puertas", "un corte no cuenta como hecho")
        (self.control / "uno.modo").unlink()
        codigo, salida = self.cli("trabajar")
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(self.estado_de("uno"), "hecho")
        self.assertEqual(len((self.raiz / "salida" / "uno" / "ejecuciones.txt").read_text().splitlines()), 1,
                         "el motor se volvió a lanzar")

    def test_dos_fabricas_a_la_vez_una_trabaja_y_la_otra_sale_con_cinco(self):
        self.montar(motor="orden")
        self.modo("motor", "dos_fabricas")
        primera = self.cli_en_segundo_plano("trabajar")
        self.assertTrue(esperar(lambda: (self.control / "motor.pid").exists(), 40), "el motor no llegó a arrancar")
        codigo, salida = self.cli("trabajar")
        self.assertEqual(codigo, 5, salida)
        self.assertIn("otra fábrica", salida)
        self.assertEqual(primera.wait(timeout=60), 0)
        self.assertEqual(self.estado_de("uno"), "hecho")
        self.assertEqual(json.loads((self.raiz / "cola.json").read_text(encoding="utf-8"))[0]["slug"], "uno")
        self.assertFalse((self.raiz / "estado" / "fabrica.lock").exists())
        self.assertEqual(len((self.raiz / "salida" / "uno" / "ejecuciones.txt").read_text().splitlines()), 1)


class PruebasOrdenUnica(Base):
    def test_sin_argumentos_da_uso_incorrecto(self):
        self.montar()
        codigo, _ = self.cli()
        self.assertEqual(codigo, 2)

    def test_un_plan_invalido_sale_con_dos_y_dice_el_error(self):
        self.montar(plan={"motor": {"tipo": "magia"}, "horario": {"inicio": "99:00"}})
        codigo, salida = self.cli("estado")
        self.assertEqual(codigo, 2)
        self.assertIn("PLAN INVÁLIDO", salida)
        self.assertIn("motor.tipo desconocido", salida)
        self.assertIn("horario.inicio", salida)

    def test_trabajar_con_plan_invalido_no_toca_nada(self):
        self.montar(plan={"aifec": "../no-existe"})
        codigo, salida = self.cli("trabajar")
        self.assertEqual(codigo, 2)
        self.assertFalse((self.raiz / "estado").exists())

    def test_estado_cuenta_hechos_y_aprobados_por_separado(self):
        self.montar(encargos=("a", "b", "c"))
        self.cli("trabajar")
        self.cli("aprobar", "a")
        codigo, salida = self.cli("estado")
        self.assertEqual(codigo, 0)
        self.assertIn("Pasan las puertas, sin mirar por una persona: 2 · Aprobados: 1", salida)
        self.assertEqual(salida.strip().splitlines()[-1],
                         "ESTADO: 3 encargos — 2 pasan las puertas, 1 aprobados, 0 atascados, 0 pendientes")
        self.assertIn("Cupo de hoy: 3 de 3 cerrados (quedan 0)", salida)

    def test_calendario_enseña_que_haria_cada_dia(self):
        self.montar(encargos=("a", "b", "c", "d", "e"), plan={"por_dia": 2})
        codigo, salida = self.cli("calendario", entorno={"AIFEC_AHORA": "2026-11-13T10:00:00"})
        self.assertEqual(codigo, 0)
        lineas = salida.strip().splitlines()
        self.assertEqual(lineas[0], "Día 1 (2026-11-13): a, b")
        self.assertEqual(lineas[1], "Día 2 (2026-11-14): c, d")
        self.assertEqual(lineas[2], "Día 3 (2026-11-15): e")
        self.assertEqual(lineas[-1], "CALENDARIO: 5 encargos en 3 días de trabajo")

    def test_anadir_pone_un_encargo_en_la_cola_y_rechaza_los_repetidos(self):
        self.montar()
        codigo, _ = self.cli("anadir", "--slug", "nuevo", "--nombre", "Nuevo", "--sector", "joyas",
                             "--campo", "tono=cálido")
        self.assertEqual(codigo, 0)
        cola = json.loads((self.raiz / "cola.json").read_text(encoding="utf-8"))
        self.assertEqual(cola[-1], {"slug": "nuevo", "nombre": "Nuevo", "sector": "joyas", "tono": "cálido"})
        codigo, salida = self.cli("anadir", "--slug", "nuevo")
        self.assertEqual(codigo, 2, salida)
        codigo, _ = self.cli("anadir", "--slug", "Mal Escrito")
        self.assertEqual(codigo, 2)

    def test_encargo_escribe_y_enseña_el_encargo_completo(self):
        self.montar()
        self.cli("trabajar")
        codigo, salida = self.cli("encargo", "uno")
        self.assertEqual(codigo, 0)
        for trozo in ("Fábrica de temas de AIFEC", "salida/uno/", "theme.json", "themes/", "estado/banco/",
                      "python fabrica.py puertas uno", "Lo que ya existe", "Lo que falló la vez anterior",
                      "Prohibido"):
            self.assertIn(trozo, salida)
        codigo, _ = self.cli("encargo", "no-existe")
        self.assertEqual(codigo, 2)

    def test_puertas_pasa_las_puertas_a_lo_que_hay_en_salida(self):
        self.montar()
        codigo, salida = self.cli("puertas", "uno")
        self.assertEqual(codigo, 1, "todavía no hay nada en salida/uno/")
        (self.raiz / "salida" / "uno").mkdir(parents=True)
        (self.raiz / "salida" / "uno" / "theme.json").write_text("{}")
        codigo, salida = self.cli("puertas", "uno")
        self.assertEqual(codigo, 0, salida)
        self.assertEqual(salida.strip().splitlines()[-1], "PUERTAS: 2 de 2 pasan")
        self.modo("dos", "1")
        codigo, salida = self.cli("puertas", "uno")
        self.assertEqual(codigo, 1)
        self.assertEqual(salida.strip().splitlines()[-1], "PUERTAS: 1 de 2 pasan, 1 no pasan")
        codigo, salida = self.cli("puertas", "uno", "--solo", "uno")
        self.assertEqual(codigo, 0)
        self.assertEqual(self.estado_de("uno"), "pendiente", "pasar las puertas a mano no cambia el estado")

    def test_aprobar_algo_que_no_esta_hecho_es_un_error(self):
        self.montar()
        codigo, salida = self.cli("aprobar", "uno")
        self.assertEqual(codigo, 1)
        self.assertIn("NO SE PUEDE APROBAR", salida)

    def test_instalar_se_niega_con_lo_que_no_esta_hecho_y_copia_lo_que_si(self):
        self.montar()
        destino = self.tmp / "instalacion"
        (destino / "core").mkdir(parents=True)
        (destino / "core" / "bootstrap.php").write_text("<?php")
        (destino / "aifec").write_text("<?php")
        codigo, salida = self.cli("instalar", "uno", "--en", str(destino))
        self.assertEqual(codigo, 1)
        self.assertIn("solo se instala lo que está hecho o aprobado", salida)
        self.assertFalse((destino / "themes").exists())
        self.cli("trabajar")
        codigo, salida = self.cli("instalar", "uno", "--en", str(destino))
        self.assertEqual(codigo, 0, salida)
        self.assertTrue((destino / "themes" / "uno" / "theme.json").is_file())
        codigo, salida = self.cli("instalar", "uno", "--en", str(destino))
        self.assertEqual(codigo, 1, "no pisa lo que ya hay sin --forzar")
        codigo, _ = self.cli("instalar", "uno", "--en", str(destino), "--forzar")
        self.assertEqual(codigo, 0)
        codigo, salida = self.cli("instalar", "uno", "--en", str(self.tmp))
        self.assertEqual(codigo, 1)
        self.assertIn("no parece una instalación", salida)

    def test_la_instalacion_de_origen_queda_intacta_tras_trabajar(self):
        self.montar(encargos=("a", "b"))
        sistema = self.tmp / "sistema"
        antes = {p.relative_to(sistema).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                 for p in sistema.rglob("*") if p.is_file()}
        self.cli("trabajar")
        despues = {p.relative_to(sistema).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                   for p in sistema.rglob("*") if p.is_file()}
        self.assertEqual(despues, antes)

    def test_banco_se_prepara_y_se_rehace_a_peticion(self):
        self.montar()
        codigo, salida = self.cli("banco")
        self.assertEqual(codigo, 0, salida)
        self.assertIn("BANCO: rehecho", salida)
        codigo, salida = self.cli("banco")
        self.assertIn("BANCO: ya estaba al día", salida)
        codigo, salida = self.cli("banco", "--rehacer")
        self.assertIn("BANCO: rehecho", salida)

    def test_parar_y_reanudar_por_la_linea_de_ordenes(self):
        self.montar()
        self.assertEqual(self.cli("parar")[0], 0)
        codigo, salida = self.cli("trabajar")
        self.assertEqual(codigo, 0)
        self.assertIn("en pausa", salida)
        self.assertEqual(self.estado_de("uno"), "pendiente")
        self.assertEqual(self.cli("reanudar")[0], 0)
        self.cli("trabajar")
        self.assertEqual(self.estado_de("uno"), "hecho")


if __name__ == "__main__":
    unittest.main()
