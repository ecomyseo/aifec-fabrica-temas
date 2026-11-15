"""AIFEC — fábrica: pruebas del plan, la configuración y la cola de encargos.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import json
import unittest
from datetime import datetime

from ayudas import Base, CONFIGS
from motor import cola as cola_mod, estado, nucleo, plan as plan_mod


class PruebasPlan(Base):
    def _cargar(self, **cambios):
        raiz = self.montar(plan=cambios.pop("plan", None))
        if cambios:
            crudo = json.loads((raiz / "plan.json").read_text(encoding="utf-8"))
            crudo.update(cambios)
            (raiz / "plan.json").write_text(json.dumps(crudo), encoding="utf-8")
        return plan_mod.cargar(raiz, plan_mod.cargar_config(raiz))

    def test_un_plan_valido_no_da_errores(self):
        plan, errores = self._cargar()
        self.assertEqual(errores, [])

    def test_se_aplican_los_valores_por_defecto_del_contrato(self):
        raiz = self.montar()
        (raiz / "plan.json").write_text(json.dumps({"aifec": "../sistema", "puertas": ["uno"]}), encoding="utf-8")
        plan, errores = plan_mod.cargar(raiz, plan_mod.cargar_config(raiz))
        self.assertEqual(errores, [])
        self.assertTrue(plan["activo"])
        self.assertEqual(plan["php"], "php")
        self.assertEqual(plan["horario"], {"inicio": "00:00", "fin": "23:59"})
        self.assertEqual((plan["por_dia"], plan["intentos"], plan["atascados_seguidos_que_paran"]), (3, 3, 2))
        self.assertEqual(plan["motor"]["tipo"], "manual")
        self.assertEqual(plan["gasto"], {"tope_eur": 0, "por_sesion_eur": 0})
        self.assertEqual(plan["umbral_estructura"], 0.82)
        self.assertEqual(plan["capturas"], {"activas": False})
        self.assertEqual(plan["aviso"], {"orden": []})

    def test_las_puertas_por_defecto_son_todas_las_de_la_fabrica(self):
        raiz = self.montar(puertas=("b", "a"))
        (raiz / "plan.json").write_text(json.dumps({"aifec": "../sistema"}), encoding="utf-8")
        plan, errores = plan_mod.cargar(raiz, plan_mod.cargar_config(raiz))
        self.assertEqual(plan["puertas"], ["a", "b"])
        self.assertEqual(errores, [])

    def test_una_ruta_de_aifec_que_no_existe_da_un_error_claro(self):
        _, errores = self._cargar(aifec="../no-existe")
        self.assertTrue(any("«aifec» no existe" in e for e in errores), errores)

    def test_aifec_tiene_que_parecer_una_instalacion(self):
        raiz = self.montar()
        (self.tmp / "vacia").mkdir()
        crudo = json.loads((raiz / "plan.json").read_text(encoding="utf-8"))
        crudo["aifec"] = "../vacia"
        (raiz / "plan.json").write_text(json.dumps(crudo), encoding="utf-8")
        _, errores = plan_mod.cargar(raiz, plan_mod.cargar_config(raiz))
        self.assertTrue(any("no parece una instalación" in e for e in errores), errores)

    def test_una_hora_mal_escrita_da_error(self):
        _, errores = self._cargar(horario={"inicio": "25:00", "fin": "9h"})
        self.assertEqual(len([e for e in errores if "horario" in e]), 2, errores)

    def test_un_motor_desconocido_da_error(self):
        _, errores = self._cargar(motor={"tipo": "magia"})
        self.assertTrue(any("motor.tipo desconocido" in e for e in errores), errores)

    def test_el_motor_orden_necesita_una_orden(self):
        _, errores = self._cargar(motor={"tipo": "orden"})
        self.assertTrue(any("motor.orden" in e for e in errores), errores)

    def test_una_clave_desconocida_es_un_error_pero_las_que_empiezan_por_guion_bajo_se_ignoran(self):
        _, errores = self._cargar(por_diaa=3, _nota="comentario")
        self.assertEqual([e for e in errores if "desconocida" in e], ["plan.json: clave desconocida «por_diaa»"])

    def test_numeros_que_no_valen_dan_error(self):
        _, errores = self._cargar(por_dia=0, intentos="tres", gasto={"tope_eur": -1})
        self.assertGreaterEqual(len(errores), 3, errores)

    def test_sin_plan_json_da_error(self):
        raiz = self.montar()
        (raiz / "plan.json").unlink()
        _, errores = plan_mod.cargar(raiz, plan_mod.cargar_config(raiz))
        self.assertTrue(any("plan.json no existe" in e for e in errores))

    def test_sin_ninguna_puerta_nada_podria_darse_por_hecho(self):
        _, errores = self._cargar(puertas=[])
        self.assertTrue(any("ninguna puerta" in e for e in errores), errores)

    def test_la_configuracion_de_la_fabrica_se_valida(self):
        raiz = self.montar()
        (raiz / "fabrica.json").write_text(json.dumps({"clase": "temas"}), encoding="utf-8")
        with self.assertRaises(plan_mod.PlanInvalido) as contexto:
            plan_mod.cargar_config(raiz)
        self.assertGreaterEqual(len(contexto.exception.errores), 4)

    def test_en_horario_dentro_fuera_y_cruzando_la_medianoche(self):
        plan = {"horario": {"inicio": "10:00", "fin": "12:00"}}
        self.assertTrue(plan_mod.en_horario(plan, datetime(2026, 11, 13, 10, 0)))
        self.assertTrue(plan_mod.en_horario(plan, datetime(2026, 11, 13, 12, 0)))
        self.assertFalse(plan_mod.en_horario(plan, datetime(2026, 11, 13, 9, 59)))
        self.assertFalse(plan_mod.en_horario(plan, datetime(2026, 11, 13, 12, 1)))
        noche = {"horario": {"inicio": "22:00", "fin": "06:00"}}
        self.assertTrue(plan_mod.en_horario(noche, datetime(2026, 11, 13, 23, 30)))
        self.assertTrue(plan_mod.en_horario(noche, datetime(2026, 11, 13, 5, 0)))
        self.assertFalse(plan_mod.en_horario(noche, datetime(2026, 11, 13, 12, 0)))

    def test_el_cupo_de_hoy_resta_lo_cerrado_hoy_y_ayer_no_cuenta(self):
        plan = {"por_dia": 2}
        ahora = datetime(2026, 11, 13, 10, 0)
        dias = {"2026-11-12": {"slugs": ["a", "b", "c"]}, "2026-11-13": {"slugs": ["d"]}}
        self.assertEqual(plan_mod.cupo_de_hoy(plan, dias, ahora), 1)
        self.assertEqual(plan_mod.cupo_de_hoy(plan, {}, ahora), 2)
        self.assertEqual(plan_mod.cupo_de_hoy(plan, {"2026-11-13": {"slugs": ["a", "b", "c"]}}, ahora), 0)


class PruebasCola(Base):
    def setUp(self):
        super().setUp()
        self.montar(encargos=("a", "b", "c"))
        self.ctx = self.abrir()
        self.cola = self.ctx.cola

    def test_un_slug_en_mayusculas_o_con_espacios_no_vale(self):
        for slug in ("Mayuscula", "con espacio", "", "-guion", "doble--guion", "../fuera"):
            self.assertTrue(cola_mod.validar([{"slug": slug}]), slug)

    def test_un_slug_repetido_no_vale(self):
        self.assertTrue(any("repetido" in e for e in cola_mod.validar([{"slug": "a"}, {"slug": "a"}])))

    def test_anadir_comprueba_la_cola(self):
        self.cola.anadir({"slug": "d", "nombre": "Cuarto"})
        self.assertEqual([e["slug"] for e in self.cola.encargos()], ["a", "b", "c", "d"])
        with self.assertRaises(cola_mod.ColaInvalida):
            self.cola.anadir({"slug": "d"})

    def test_la_cola_tambien_puede_ser_un_objeto_con_encargos(self):
        (self.raiz / "cola.json").write_text(json.dumps({"encargos": [{"slug": "x"}]}), encoding="utf-8")
        self.assertEqual([e["slug"] for e in self.cola.encargos()], ["x"])

    def test_un_encargo_sin_estado_es_pendiente(self):
        self.assertEqual(self.cola.estado("a")["estado"], "pendiente")

    def test_el_camino_feliz_apunta_cada_paso_con_fecha(self):
        for destino in ("en_curso", "en_puertas", "hecho", "aprobado"):
            self.cola.transicionar("a", destino, "nota " + destino)
        datos = self.cola.estado("a")
        self.assertEqual([h["a"] for h in datos["historial"]], ["en_curso", "en_puertas", "hecho", "aprobado"])
        self.assertTrue(all(h["fecha"].startswith("2026-11-13T10:00") for h in datos["historial"]))
        self.assertEqual(datos["historial"][0]["de"], "pendiente")

    def test_las_transiciones_no_permitidas_son_un_error(self):
        permitidas = {
            ("pendiente", "en_curso"), ("en_curso", "en_puertas"), ("en_puertas", "hecho"),
            ("en_puertas", "rechazado"), ("hecho", "aprobado"), ("hecho", "rechazado"),
            ("aprobado", "rechazado"), ("rechazado", "en_curso"), ("rechazado", "atascado")}
        for origen in cola_mod.ESTADOS:
            for destino in cola_mod.ESTADOS:
                self.cola.guardar("a", {"slug": "a", "estado": origen, "intentos": 0, "motivo": "", "historial": []})
                if (origen, destino) in permitidas:
                    self.cola.transicionar("a", destino)
                else:
                    with self.assertRaises(cola_mod.TransicionInvalida, msg="%s -> %s" % (origen, destino)):
                        self.cola.transicionar("a", destino)

    def test_comenzar_intento_cuenta_intentos(self):
        self.cola.comenzar_intento("a")
        self.assertEqual(self.cola.estado("a")["intentos"], 1)
        self.cola.transicionar("a", "en_puertas")
        self.cola.rechazar("a", "motivo", 3)
        self.cola.comenzar_intento("a")
        self.assertEqual(self.cola.estado("a")["intentos"], 2)

    def test_rechazar_agota_los_intentos_y_deja_atascado(self):
        for _ in range(3):
            self.cola.comenzar_intento("a")
            self.cola.transicionar("a", "en_puertas")
            final = self.cola.rechazar("a", "no pasa", 3)
        self.assertEqual(final, "atascado")
        datos = self.cola.estado("a")
        self.assertEqual(datos["estado"], "atascado")
        self.assertEqual(datos["motivo"], "no pasa")

    def test_siguiente_prefiere_lo_que_quedo_a_medias_luego_rechazados_luego_pendientes(self):
        self.assertEqual(self.cola.siguiente(3), "a")
        self.cola.comenzar_intento("c")  # c quedó a medias
        self.assertEqual(self.cola.siguiente(3), "c")
        self.cola.transicionar("c", "en_puertas")
        self.cola.rechazar("c", "x", 3)
        self.cola.comenzar_intento("b")
        self.cola.transicionar("b", "en_puertas")
        self.cola.rechazar("b", "y", 3)
        self.assertEqual(self.cola.en_orden_de_trabajo(3), ["b", "c", "a"])

    def test_un_rechazado_sin_intentos_no_vuelve_a_salir(self):
        for _ in range(2):
            self.cola.comenzar_intento("a")
            self.cola.transicionar("a", "en_puertas")
            self.cola.rechazar("a", "x", 5)
        self.assertEqual(self.cola.en_orden_de_trabajo(2), ["b", "c"])

    def test_las_cuentas_separan_hecho_de_aprobado(self):
        for destino in ("en_curso", "en_puertas", "hecho"):
            self.cola.transicionar("a", destino)
        for destino in ("en_curso", "en_puertas", "hecho", "aprobado"):
            self.cola.transicionar("b", destino)
        cuentas = self.cola.cuentas()
        self.assertEqual((cuentas["hecho"], cuentas["aprobado"], cuentas["pendiente"]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
