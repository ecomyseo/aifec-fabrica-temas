# El plan (`plan.json`)

JSON no admite comentarios, así que cada clave se explica aquí. `plan.ejemplo.json` es un punto de partida; `plan.json` queda fuera del repositorio. Las claves que empiezan por `_` se ignoran (sirven de nota); cualquier otra clave desconocida es un error, para cazar erratas.

Las rutas relativas se resuelven desde la carpeta de la fábrica. Un plan inválido sale con código 2 y dice qué está mal.

| Clave | Por defecto | Qué es |
|---|---|---|
| `activo` | `true` | Con `false`, `trabajar` sale sin hacer nada. |
| `aifec` | — (obligatoria) | Ruta de una instalación de AIFEC. Tiene que traer `core/bootstrap.php` y el fichero `aifec`. Se lee; nunca se escribe en ella. |
| `php` | `"php"` | Ejecutable de PHP con el que se lanzan las órdenes de AIFEC en el banco. |
| `php_versiones` | `[]` | Otros ejecutables de PHP para la puerta de sintaxis (el más bajo y el más alto admitidos). |
| `horario` | `{"inicio": "00:00", "fin": "23:59"}` | No se empieza un encargo fuera de ese tramo. Un tramo que cruza la medianoche (`22:00` a `06:00`) vale. |
| `por_dia` | `3` | Encargos que se cierran (hechos o atascados) por día de trabajo. Un día sin lanzar la fábrica no gasta plan ni lo acumula. |
| `intentos` | `3` | Veces que se relanza un encargo que no pasa las puertas; al agotarlas queda `atascado`. |
| `atascados_seguidos_que_paran` | `2` | Cuántos encargos atascados seguidos paran la fábrica (código 4) y avisan. Un `hecho` reinicia la cuenta. |
| `motor` | `{"tipo": "manual", "minutos": 45}` | `manual`, `simulado` u `orden` (ver `motores.md`). `minutos` es el límite de una sesión del motor. |
| `gasto` | `{"tope_eur": 0, "por_sesion_eur": 0}` | Con `tope_eur` a 0, un motor de pago **no se lanza**. `por_sesion_eur` es lo que se apunta por cada sesión. |
| `puertas` | las de `fabrica.json` o, si no dice, las de `puertas/` | Lista y orden de las puertas. Una lista vacía es un error: sin puertas nada podría darse por hecho. |
| `puertas_minutos` | `15` | Límite de tiempo de cada puerta; al pasarse se corta y cuenta como que no pasa. |
| `umbral_estructura` | `0.82` | Parecido máximo de una superficie con la de otro tema (lo lee la puerta `estructura`). |
| `capturas` | `{"activas": false}` | Con `true` y Playwright instalado, la puerta `capturas` trabaja. |
| `aviso` | `{"orden": []}` | Orden (lista) que se lanza al terminar el día, al atascarse y al parar por gasto, con `{mensaje}` sustituido. Vacía = no avisa a nadie. |
| `banco` | `{"sitio": "banco", "orden_sitio": null}` | Identificador del sitio del banco y, si hace falta, la orden de AIFEC (lista) con la que crearlo, en lugar de la de por defecto. |

## El motor dentro del plan

```json
{"motor": {"tipo": "manual"}}
{"motor": {"tipo": "simulado", "origen": "../un-tema-ya-hecho"}}
{"motor": {"tipo": "orden", "orden": ["programa", "{encargo}", "{trabajo}"], "minutos": 45,
           "coste_regex": "coste: ([0-9.,]+)"}}
```

Detalle de cada uno en `motores.md`.

## Variable de entorno para pruebas

`AIFEC_AHORA=2026-11-13T10:00:00` fija la hora que cree la fábrica (horario, cupo y calendario). No hace falta nunca fuera de las pruebas.
