# Las puertas

Una puerta es un programa de `puertas/` que comprueba **una** cosa de lo fabricado. La fábrica las lanza en el orden del plan, junta sus informes en `estado/encargos/<slug>.puertas.json` y decide: el encargo pasa si ninguna da 1. Una puerta que no existe, que revienta o que no deja informe **cuenta como que no pasa**.

## La interfaz

```
python puertas/<nombre>.py --slug <slug> --candidato <salida/slug> --banco <estado/banco> --plan <plan.json> --informe <fichero.json> [--paginas <carpeta>]
```

| Código | Significa |
|---|---|
| 0 | pasa |
| 1 | no pasa (el informe dice por qué) |
| 2 | no aplica: falta algo opcional (PHP, el banco, una orden del sistema, Playwright). **No bloquea, pero tampoco demuestra nada** |

El informe es un JSON con `puerta`, `ok` (falso solo si no pasa), `resumen` (una línea), `detalles` (la lista que explica el resumen) y `medidas` (los números). Ninguna puerta modifica el candidato: lo que escriben va al informe y a `estado/`.

`--paginas <carpeta>` evita pintar nada: lee las páginas de `<carpeta>/<tema>/{portada,listado,ficha,carrito}.html`. Sirve para las pruebas y para usar una puerta suelta sin banco.

## Cómo se lee un informe

`python fabrica.py puertas <slug>` escribe **una línea por puerta**:

```
  [pasa] validador — theme:check sin errores (puntuación 96, 4 avisos)
  [no_pasa] estructura — 2 superficie(s) demasiado parecidas a otro tema
PUERTAS: 5 de 7 pasan, 1 no aplican, 1 no pasan
```

El detalle (la tabla de parecidos, las cadenas que faltan, el acceso de móvil que no cumple) está en el JSON y lo enseña `python skill/informe.py <slug> [--puerta estructura]`. Para repetir una sola puerta: `python fabrica.py puertas <slug> --solo movil,peso`.

## Cómo se pintan las páginas

Las puertas `estructura`, `peso` y `movil` miran HTML **servido de verdad**, no plantillas:

1. `_sembrar.php` carga el paquete de demostración mínimo (`demos/minimo`) en el sitio del banco, una sola vez por banco (deja `demo-cargada.txt`). Sin él no habría productos que pintar.
2. `_pintar.php --banco … --tema <slug> --salida <carpeta>` arranca la aplicación del sitio del banco, **pone ese tema solo en memoria** (no guarda nada en la base de datos), pide en el propio proceso la portada, un listado y una ficha (los busca siguiendo los enlaces de la portada) y el carrito, y guarda su HTML.
3. Si el banco no tiene productos, lo dice y pinta la página de muestra del tema base (`/tema/muestra`, que solo existe con la depuración encendida); entonces no hay listado ni ficha reales y las superficies que faltan no se comparan.
4. El resultado se guarda en `estado/paginas/<slug>/` con la huella del tema: no se repite el trabajo mientras el tema no cambie. Los demás temas con los que se compara se pintan igual.

Todas las rutas que se pasan a PHP van **absolutas**: el sitio guarda en su caché las rutas con las que arrancó y una relativa deja el banco roto para las siguientes.

## Las ocho

### `validador` — el contrato de temas del sistema

Instala el candidato en el banco y lanza `php aifec theme:check <slug>`. **No repite ninguna de sus comprobaciones**: lee su veredicto (`[FAIL]` = no pasa; `[WARN]` solo se cuenta). Lo que mira el sistema: `theme.json` y herencia, plantillas y piezas del contrato, envoltorio con `page_head()`, `<main id="main">` y barra de móvil, peso, direcciones ajenas, galería antes que compra, traducciones, contraste y las comprobaciones en vivo de la portada y la página de error. Si el sistema no trae la orden, sale con 2.

### `estructura` — que el tema no es un clon

Saca de cada página pintada las cinco superficies por su clase de contrato y las reduce a un **esqueleto**:

| Superficie | Clase | De qué página |
|---|---|---|
| cabecera | `af-header` | la primera donde esté |
| tarjeta de producto | `af-product-card` (la primera) | listado, o portada |
| listado | `af-listing` | listado |
| ficha | `af-product` | ficha |
| pie | `af-footer` | la primera donde esté |

El esqueleto es la lista de marcas `profundidad:etiqueta.clases-af` en orden. **Cuenta**: la etiqueta, su orden, el anidado y las clases `af-…`. **No cuenta**: el texto, los atributos, las imágenes (`img`, `picture`), los iconos SVG, los guiones y estilos, **las clases que no empiezan por `af-`** (ni su nombre ni que existan) y el número de elementos hermanos repetidos seguidos (veinte tarjetas cuentan como una). El parecido es `difflib.SequenceMatcher` sobre esas listas, de 0 a 1.

| Regla | Límite |
|---|---|
| Una superficie contra la de **otro tema** (los del banco y los ya fabricados en `salida/`) | no puede llegar a `umbral_estructura` (0,82 por defecto) |
| Una superficie contra la de **su tema padre** | no puede llegar a 0,90 («superficie heredada sin rediseñar») |
| Una superficie del contrato que el tema no pinta | no pasa y dice qué clase falta |
| Sin otros temas con los que comparar | pasa y lo dice |

Lo que el informe enseña: la tabla superficie × tema con su cifra, y la más alta señalada (`Más alto: ficha con 0,63 (tema «despensa»)`). Suelta, sobre dos páginas HTML:

```
python puertas/estructura.py --comparar a.html b.html
```

### `peso` — el presupuesto

Cada hoja de estilos del tema ≤ **45 000 bytes**, cada guion ≤ **25 000**, la ficha de producto pintada ≤ **150 000** sin imágenes (sin `<img>`, `<picture>`, `<source>` ni `data:`), y toda imagen de lo pintado con `width` y `height`. Medidas: `css_bytes`, `js_bytes`, `ficha_bytes`, `imagenes_sin_medidas`.

### `movil` — el contrato de móvil

En lo pintado, para portada, listado, ficha y carrito: hay `af-header`; hay `af-mobile-bar`; la barra trae un acceso **real** a Buscar y a Carrito (un enlace con dirección o un botón que abre un panel que existe en la página; nunca `#`), el carrito con su contador `data-af-cart-count`, cada acceso con nombre accesible; y el botón Filtros sale **solo** en las páginas con filtros (`af-listing-filters`) y entonces su panel está. En la hoja efectiva (la de los padres y la propia, tal como la carga `theme_styles()`; `"css": "replace"` empieza de cero): cabecera con `position: sticky` o `fixed` **a 390 px**, barra con `position: fixed`, `env(safe-area-inset-bottom)`, espacio reservado bajo el contenido (`padding-bottom` en `.af-has-bar`, `body` o `main`), zona táctil de la barra ≥ 44 px (lee las variables de `:root`) y `:focus-visible`.

### `traducciones` — nada sin traducir

Instala el candidato y lanza `php aifec i18n:check themes/<slug> es`. Pasa con código 0 y la línea final `… strings, 0 missing`. Enseña las cadenas que faltan, listas para pegar en `lang/es.php`.

### `limpieza` — nada de fuera ni de sobra

1. **Direcciones ajenas**: ninguna `http(s)://` (salvo el espacio de nombres de SVG, `www.w3.org`), ninguna dirección sin protocolo (`//host.tld`) y ningún `@import` en plantillas y recursos de texto de `assets/`.
2. **Ficheros de sobra**: paquetes comprimidos, mapas de código, ficheros de trabajo, tipografías `.ttf`/`.otf`/`.eot` (solo woff2), carpetas `node_modules`, `.git`, `capturas`…, e imágenes fuera de `assets/` (solo `preview.png` y `mockup.png` en la raíz).
3. **Sintaxis de PHP** con `php -l` en cada ejecutable de `php_versiones` del plan y en el de `php`. Uno que no se encuentra **no pasa**: sin él no se prueba esa versión.

### `contrato` — las pruebas de temas del propio sistema

Instala el candidato en el banco y lanza, con el lanzador del sistema (`php tests/run.php …`), las pruebas de `tests/Themes/` que AIFEC pasa a **todos** los temas a la vez:

| Prueba | Lo que exige a un tema |
|---|---|
| `AriaTest.php` | entre otras cosas, ninguna plantilla escribe un `<img>` o un `<iframe>` sin `width` y `height`, tampoco dentro de una cadena de PHP |
| `ReadingColumnTest.php` | si la hoja nombra `.af-prose{`, el texto de entradas, páginas y fichas va a todo el ancho: lleva `.af-prose{max-width:none;` y `.af-post>*,.af-page>*{max-width:none}`, y ninguna regla de `.af-prose`, `.af-post` o `.af-page` pone un `max-width` con medida |
| `InlineCssTest.php` | la hoja cabe dentro de la página: sin `url()` relativas, sin `@import` y por debajo del tope |

**No repite ninguna comprobación**: lee la línea final `PRUEBAS: n OK, m FALLAN` y cada `FALLA …`. Pasa con código 0 y cero fallos. Cuando un fallo no nombra a este tema (`themes/<slug>/` o `<slug>: …`), lo dice: otro tema del banco tiene las pruebas rotas y tapa el resultado de este, y hay que rehacer el banco (`python fabrica.py banco --rehacer`). Si el sistema no trae el lanzador o ninguna de las tres pruebas, sale con 2.

Existe porque los tres primeros temas fabricados pasaban `theme:check` y rompían la batería de AIFEC el día que se instalaron.

### `capturas` — lo que solo se ve en un navegador (opcional)

Con `capturas.activas` y Playwright: arranca `php -S` del banco en un puerto libre **como hijo suyo** (salida a un fichero, sin ventana), pone el tema candidato en el sitio del banco (`setting:set theme.active`, que repone al acabar), lanza **un** navegador sin ventana con `--disable-gpu`, captura portada, listado, ficha y carrito a 1440 y a 390 px en `escaparate/<slug>/` y exige cero errores de JavaScript, cero respuestas 5xx y cero desbordamiento horizontal (medido contra 390 px, no contra `innerWidth`). Al acabar, también si falla, para el servidor y el navegador y comprueba que el puerto queda libre. Sin Playwright, apagada o sin banco, sale con 2. **Abre un navegador: no se lanza sin que lo pida una persona** (y por el turno de la máquina, si el equipo lo exige).

## Las claves del plan que leen las puertas

| Clave | Lo usa |
|---|---|
| `php` | todas las que lanzan PHP (tiene que tener `pdo_sqlite` para el banco) |
| `php_versiones` | `limpieza` |
| `umbral_estructura` | `estructura` |
| `capturas.activas` | `capturas` |
| `puertas_minutos` | el límite de tiempo de cada puerta |

## Si algo falla

| Síntoma | Causa y arreglo |
|---|---|
| Varias puertas salen con 2 «el banco no está preparado» | `python fabrica.py banco`. |
| `estructura` dice «no hay otros temas con los que comparar» | el banco no trae temas o `--paginas` no tiene carpetas de otros temas. |
| Las páginas salen todas iguales para temas distintos | el tema se activó **después** de arrancar la aplicación; `_pintar.php` lo pone antes, no se toca. |
| «Failed to open stream … estado/banco/modules/…» | se arrancó algún guion con una ruta relativa: el sitio la guardó en su caché. `python fabrica.py banco --rehacer`. |
| La puerta de capturas deja un puerto abierto | un servidor que no se paró: la propia puerta lo cuenta como fallo (`puerto_libre`). |
