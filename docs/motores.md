# Los motores

La fábrica no sabe nada de ninguna IA concreta. Un motor es quien hace el trabajo de un encargo dentro de `salida/<slug>/`. Hay tres.

**Ningún motor escribe fuera de `salida/<slug>/`.** Tras cada sesión se compara una instantánea (fechas y tamaños) de toda la carpeta de la fábrica, salvo `salida/<slug>/`, `estado/`, `escaparate/` y `cola.json`. Si algo cambió, el encargo se rechaza con ese motivo.

## `manual`

```json
{"motor": {"tipo": "manual"}}
```

La fábrica escribe el encargo completo en `estado/encargos/<slug>.encargo.md` (qué hay que hacer, dónde, con qué skill y cómo comprobarlo: `python fabrica.py puertas <slug>`), deja el encargo `en_curso` y termina diciendo dónde está. Una persona (o una IA a mano) hace el trabajo en `salida/<slug>/`. Cuando vuelve a lanzarse `python fabrica.py trabajar`, la fábrica le pasa las puertas a lo que haya.

Lanza `trabajar` solo cuando el trabajo esté listo, o usa antes `python fabrica.py puertas <slug>`: un intento rechazado cuenta como intento.

## `simulado`

```json
{"motor": {"tipo": "simulado", "origen": "../un-tema-ya-hecho"}}
```

Copia a `salida/<slug>/` lo que haya en `origen` y sigue. No gasta. Sirve para las pruebas y para enseñar la fábrica.

## `orden`

```json
{"motor": {"tipo": "orden", "minutos": 45,
           "orden": ["programa", "--opcion", "{encargo}"]},
 "gasto": {"tope_eur": 20, "por_sesion_eur": 1.5}}
```

Lanza `motor.orden` (una lista: programa y argumentos) con el directorio de trabajo en `salida/<slug>/`. Se sustituyen, en una sola pasada:

| Marca | Valor |
|---|---|
| `{encargo}` | ruta del fichero del encargo |
| `{texto}` | su contenido |
| `{trabajo}` | la carpeta de salida |
| `{fabrica}` | la carpeta de la fábrica |

- **Límite de tiempo:** `motor.minutos` (45 por defecto). Al pasarse se mata el árbol entero de procesos y el intento se rechaza.
- **Salida:** `estado/sesiones/<slug>-<n>.log`.
- **Gasto:** antes de lanzar se comprueba el libro (`estado/gasto.json`): si `gastado + por_sesion_eur > tope_eur`, o el tope es 0, **no se lanza**, el encargo queda como estaba y la fábrica sale con código 3. La sesión se apunta **antes** de lanzar (una sesión cortada también cuesta). Si `motor.coste_regex` es una expresión con un grupo de captura y encuentra el coste en la salida, se corrige el apunte.
- **Entrada vacía:** el programa no recibe nada por la entrada estándar. En Windows se lanza sin ventana.
- Para pasar un texto largo, mejor `{encargo}` (una ruta) que `{texto}` (un argumento enorme).

### Ejemplos genéricos de `motor.orden`

Los programas y sus opciones cambian con cada versión: aquí solo la forma. Sustituye el programa por el que uses y comprueba sus opciones con su propia ayuda.

Un programa que recibe el encargo por un fichero:

```json
["programa-de-ia", "--tarea-desde", "{encargo}"]
```

Un programa que recibe el texto del encargo como argumento:

```json
["programa-de-ia", "--instruccion", "{texto}"]
```

Un programa que lee de un fichero y trabaja en una carpeta que se le indica:

```json
["programa-de-ia", "--directorio", "{trabajo}", "--leer", "{encargo}"]
```

Un guion propio que prepara el entorno y llama a la IA:

```json
["python", "{fabrica}/mi-guion.py", "{encargo}", "{trabajo}"]
```

La fábrica no recomienda ninguno ni da precios: el coste de cada sesión es el que pongas en `gasto.por_sesion_eur`.
