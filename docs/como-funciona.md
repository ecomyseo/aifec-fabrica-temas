# Cómo funciona

## La idea

Una fábrica trabaja con **cuatro cosas en disco** y nada en memoria:

| Qué | Dónde | Quién lo escribe |
|---|---|---|
| El plan | `plan.json` | tú |
| La cola de encargos | `cola.json` | tú, o `python fabrica.py anadir` |
| El estado de cada encargo | `estado/encargos/<slug>.json` | la fábrica |
| Lo fabricado | `salida/<slug>/` | el motor |

Como el estado vive en disco y se escribe de forma atómica (fichero temporal y `os.replace`), un corte a mitad —se apaga el equipo, se acaba la cuota de la IA, alguien mata el proceso— no deja nada a medias: al relanzar, la fábrica sigue por donde iba.

## El ciclo de un encargo

```
pendiente ──► en_curso ──► en_puertas ──► hecho ──► aprobado
                 │              │           │
                 │              └───────────┴──► rechazado ──► (vuelve a la cola) ──► atascado
```

1. **Preparar.** La fábrica pasa el encargo a `en_curso` (y cuenta un intento), prepara `salida/<slug>/` y, en el primer intento, le pide a AIFEC el esqueleto con la orden de `fabrica.json` (`orden_esqueleto`). Escribe el encargo completo en `estado/encargos/<slug>.encargo.md`.
2. **Motor.** El motor hace el trabajo en `salida/<slug>/` (ver `motores.md`). Tras la sesión, la fábrica compara una instantánea de su carpeta: si algo cambió fuera de `salida/<slug>/`, `estado/` y `escaparate/`, el intento se rechaza con ese motivo.
3. **Puertas.** Pasa a `en_puertas`. La fábrica comprueba que está el manifiesto que dice `fabrica.json`, prepara el banco, instala el candidato en él y lanza cada puerta de `puertas/`. Una puerta que no existe, que revienta o que no deja informe **cuenta como que no pasa**.
4. **Hecho o rechazado.** Si ninguna puerta da 1, pasa a `hecho` y se escribe su ficha en `escaparate/<slug>/`. Si alguna no pasa, `rechazado`, con el motivo y los informes; el siguiente encargo que recibe el motor lleva lo que falló. Al agotar `intentos`, `atascado`.
5. **Aprobado.** Solo una persona lo pone (`python fabrica.py aprobar <slug>`), después de mirarlo.

Las transiciones son **solo** las del dibujo: cualquier otra es un error.

## El orden en que se toma un encargo

Primero el que quedó a medias (`en_curso` o `en_puertas`), después los `rechazado` con intentos, después los `pendiente`, en el orden de la cola. Por eso un corte se reanuda por el mismo encargo, sin repetirlo desde cero: lo que ya había en `salida/<slug>/` se conserva y reanudar no gasta un intento.

## El trabajo de cada día (`trabajar`)

Respeta el plan, en este orden: `activo`, `parar`, horario, cupo de hoy (`por_dia`), tope de gasto y atascos seguidos. Los días cuentan **cuando la fábrica trabaja**: un día sin lanzarla no gasta plan. Los reintentos de un encargo rechazado van seguidos. Termina siempre con el cerrojo suelto y una línea de resumen.

- **Cerrojo.** `estado/fabrica.lock` guarda el PID. Si ya existe y ese PID sigue vivo y es un Python, otra fábrica está trabajando y esta sale con 5. Si el PID está muerto, o lo ha reutilizado otro programa, el cerrojo se toma.
- **Atascos.** Con `atascados_seguidos_que_paran` encargos atascados seguidos, la fábrica para (código 4) y avisa. La cola queda intacta. Sigue parada hasta `python fabrica.py reanudar`.
- **Tope de gasto.** Con un motor de pago, si `gastado + por_sesion_eur` pasa de `tope_eur` (o el tope es 0), no se lanza nada: el encargo queda como estaba y sale con 3.
- **Parar.** `parar` deja terminar el encargo en curso y no empieza otro.
- **Avisos.** Al terminar el día, al atascarse un encargo y al parar por gasto se lanza `aviso.orden`, si el plan la trae.

## El banco de pruebas

Una copia de trabajo de AIFEC en `estado/banco/`, sin `sites`, `storage`, cachés ni `.git`, ni `data-path.php` (apunta a los datos reales de quien desarrolla). Dentro se crea un sitio propio con `php aifec site:create` y SQLite, y toda orden de AIFEC que lance la fábrica lleva `--data=` apuntando a `estado/banco/sites`. Se rehace cuando cambia el fichero de versión de AIFEC o la fecha de `core/`, o con `python fabrica.py banco --rehacer`.

## Las puertas

Cada puerta es un programa de `puertas/` con esta interfaz:

```
python puertas/<nombre>.py --slug <slug> --candidato <salida/slug> --banco <estado/banco> --plan <plan.json> --informe <fichero.json>
```

Sale con **0** (pasa), **1** (no pasa) o **2** (no aplica: falta algo opcional) y escribe en `--informe`:

```json
{"puerta": "peso", "ok": true, "resumen": "CSS 31 KB de 45", "detalles": ["…"], "medidas": {"css_bytes": 31022}}
```

No modifica el candidato. La fábrica junta los informes en `estado/encargos/<slug>.puertas.json` y decide: pasa si ninguna da 1. Una puerta con 2 no bloquea, pero tampoco demuestra nada.

## El escaparate

`escaparate/<slug>/ficha.json` (y `ficha.md`) por cada encargo que pasa las puertas, y `escaparate/index.html`: una página estática, sin nada de fuera, que separa «pasan las puertas» de «aprobados».

## Una fábrica de plugins

`motor/` y `fabrica.py` no saben si fabrican temas o plugins: lo leen todo de `fabrica.json` (`clase`, `titulo`, `carpeta_destino`, `manifiesto`, `orden_esqueleto` y, opcionalmente, `puertas`). La fábrica de plugins copia esos ficheros tal cual y cambia `fabrica.json` y sus puertas.

## Para reponer un encargo atascado

Un `atascado` no sale solo de ese estado. Cuando hayas arreglado la causa: borra `estado/encargos/<slug>.json` (vuelve a empezar de `pendiente`) y, si quieres rehacerlo desde cero, la carpeta `salida/<slug>/`.
