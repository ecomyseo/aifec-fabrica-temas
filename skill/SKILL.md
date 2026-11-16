---
name: fabrica-temas-aifec
description: "Cómo construir un tema de AIFEC (el sistema de comercio electrónico en PHP) que pase las ocho puertas de la fábrica de temas a la primera: leer el encargo, descomponer las cinco superficies, partir del esqueleto, escribir cabecera, tarjeta, listado, ficha y pie con composición propia, opciones, traducción, y pasar `python fabrica.py puertas <slug>`. Usar siempre que se vaya a crear o a rehacer un tema dentro de `salida/<slug>/`."
---

# Construir un tema de AIFEC que pase las puertas

Este skill lo sigue **cualquier IA de programación** (o una persona) que reciba un encargo de la fábrica de temas. Se trabaja solo en `salida/<slug>/`; la fábrica comprueba el resultado con siete puertas y no da nada por hecho hasta que todas pasan.

## Lo que hay que saber antes de empezar

- Un tema **hijo de `base`** hereda plantillas, piezas, guion, hoja y opciones del tema base. Solo escribe lo que quiere distinto. El contrato completo está en `contratos/04-temas.md` del sistema; aquí va lo que hace falta para acertar.
- Lo que pone el tema: el envoltorio, las piezas comunes (`partials/…`), los estilos y el guion. Lo que pone cada módulo: las plantillas de sus páginas (ficha, listado, carrito, caja). Un tema puede **sustituir** una plantilla de módulo copiándola a `templates/modules/<módulo>/front/<plantilla>.php` y **conservando sus huecos y sus datos**.
- La fábrica **mira la composición, no la pintura**: dos temas con otros colores, otros textos y otras clases propias, pero el mismo orden de elementos, son un clon y no pasan.
- No se toca el sistema ni el banco (`estado/banco/`), no se sale a Internet y no se escribe fuera de `salida/<slug>/`.

## Fases (en este orden; no se salta ninguna)

### 1. Leer el encargo

`python fabrica.py encargo <slug>` lo escribe entero. Campos habituales: `nombre`, `sector`, `publico`, `idea` (lo que manda en este tema), `referencias`, `paleta`, `tipografia`, `superficies` (cómo quiere cada una), `no_hacer`. Lo que el encargo no diga se decide con sentido común y se anota en `NOTAS.md` del tema. Un dato que falte **no se inventa del mundo real** (direcciones, precios, marcas): se deja como opción del tema.

### 2. Descomponer antes de programar

Rellena la tabla de `skill/plantillas/descomposicion.md` (cinco superficies; en un borrador, porque todavía no hay carpeta: en la fase 3 `esqueleto.py` la deja como `NOTAS.md` del tema y ahí la pegas). Para cada una: **cómo será** (qué elementos, en qué orden, qué va dentro de qué) y **en qué se distingue** de la del tema base y de las de los temas que ya existen. Mira antes esos temas: `estado/banco/themes/*/templates/` y `salida/*/templates/`. Si ya hay un tema hecho desde el esqueleto, **el tuyo tiene que diferir también de ese**.

Cuenta para la comparación: etiquetas, su orden, cuánto se anidan y qué clases `af-…` llevan. **No cuenta**: texto, atributos, imágenes, iconos SVG, clases propias, el número de tarjetas repetidas. Cambiar colores o nombres no crea un diseño distinto; cambiar la composición, sí.

### 3. Esqueleto

```
python skill/esqueleto.py <slug> "<Nombre del tema>"        crea salida/<slug>/ desde plantillas/esqueleto/
```

Deja un tema hijo de `base` (con tu tabla de descomposición como `NOTAS.md`) que **ya pasa `theme:check`** con las cinco superficies propias y un prefijo de clases propio (las iniciales del slug). Es un punto de partida, no un resultado: cuanto menos lo cambies, más se parecerá a lo que ya existe. Si el sistema tiene `theme:create`, también vale (`php aifec theme:create <slug> --parent=base --name=…` en el banco), pero entonces las cinco superficies se heredan y hay que escribirlas todas.

### 4. Las cinco superficies, una a una

Para cada una: escribe la plantilla, mira `python fabrica.py puertas <slug> --solo estructura,movil` y `python skill/informe.py <slug>`, y sigue con la siguiente.

| Superficie | Fichero | Clase que la identifica |
|---|---|---|
| Cabecera | `templates/partials/header.php` | `af-header` |
| Tarjeta de producto | `templates/partials/product-card.php` | `af-product-card` |
| Listado | `templates/modules/catalog/front/listing.php` | `af-listing` |
| Ficha | `templates/modules/catalog/front/product.php` | `af-product` |
| Pie | `templates/partials/footer.php` | `af-footer` |

Además, la portada (`templates/home.php` y las vistas `modules/catalog/front/home/*.php` que sustituyas) y la hoja `assets/css/theme.css`. Reglas de cada una en `referencias/clases.md` y `referencias/huecos-y-datos.md`.

Lo que **no se negocia** aunque cambies la composición:

- En escritorio la **galería de la ficha va a la izquierda y la compra a la derecha**, y en el HTML `af-product-gallery` va antes que `af-product-buy`.
- **Contrato de móvil**: cabecera pegajosa; barra inferior fija con Buscar y Carrito **reales** (con su contador `data-af-cart-count`), Filtros solo en el listado, Cuenta si existe; el contenido reserva el alto de la barra; `env(safe-area-inset-bottom)`; zonas táctiles de 44 px; foco visible.
- Todos los **datos** que pinta la plantilla original (precio con su anterior tachado y legible y su insignia, disponibilidad, variantes, cantidad, el formulario `data-af-cart-add`, datos clave, descripción, características, preguntas, relacionados) y **todos sus huecos** (`hook('product.tabs')`…).
- `page_head($page)` en el `<head>`, `<main id="main">`, un solo `<h1>`, `theme_styles()` y `theme_scripts()`.
- Todo dato impreso, por `e()`. Todo texto que ve una persona, en inglés dentro de `t('…')`.

### 5. Opciones (`theme.json`)

Como mínimo **tres opciones de estructura** (no solo colores) que el comerciante pueda cambiar, y cada color con su `var` (`--mi-color`) **usada** en la hoja. Una opción con `var` que ninguna hoja usa da aviso en el validador. Colores solo por variables; contraste AA también en el precio anterior, las insignias y el texto sobre el acento. La descripción del tema va **en inglés** (también se traduce).

### 6. Traducción

Cada cadena de tus plantillas y de `theme.json` (etiquetas y descripción) tiene su traducción en `lang/es.php`, en castellano con tildes y eñes. Para saber cuáles faltan:

```
python fabrica.py puertas <slug> --solo traducciones
```

La puerta enseña las que faltan (el sistema las da listas para pegar). La clave es la cadena inglesa tal cual; no se toca.

### 7. Pasar las puertas

```
python fabrica.py puertas <slug>
```

Sale con 0 si ninguna da 1. `python fabrica.py puertas` solo escribe una línea por puerta; el detalle completo (la tabla de parecidos, las cadenas que faltan, el elemento de móvil que no cumple) lo enseña `python skill/informe.py <slug>`. Léelo y arregla **la causa**, no el síntoma. Una puerta que sale como «no aplica» no bloquea, pero tampoco demuestra nada: dilo en la entrega. Repite hasta que acabe en `PUERTAS: n de n pasan` (o con «no aplican» explicados).

### 8. Entrega

Lo que se dice: el tema está en `salida/<slug>/`, la última línea de las puertas tal cual, y lo que no se pudo comprobar (por ejemplo «capturas: no aplica»). Lo que **no** se dice: que está «terminado» o «aprobado» (eso lo decide una persona que lo mire), ni que se ve bien en un navegador si no se ha abierto uno.

## Lista de comprobación: las puertas y su medida

| Puerta | Pasa si… | Medida |
|---|---|---|
| `validador` | `php aifec theme:check <slug>` sale sin errores | errores = 0 |
| `estructura` | ninguna superficie se parece a la de otro tema | parecido < 0,82 con cada tema y < 0,90 con tu padre |
| `peso` | presupuesto | cada hoja ≤ 45 000 bytes, cada guion ≤ 25 000, ficha pintada ≤ 150 000 sin imágenes, toda imagen con `width` y `height` |
| `movil` | contrato de móvil, en lo pintado y en la hoja | cabecera pegajosa, barra fija con accesos reales, `safe-area`, 44 px, `:focus-visible` |
| `traducciones` | `php aifec i18n:check themes/<slug>` | `0 missing` |
| `limpieza` | nada de fuera ni de sobra | ninguna dirección de otro dominio ni `@import`; ningún `.zip`, `.map`, `node_modules`, captura suelta ni tipografía que no sea woff2; PHP válido en todas las versiones del plan |
| `contrato` | las pruebas de temas del propio AIFEC (`tests/Themes/`) siguen pasando con tu tema dentro | toda imagen de plantilla con `width` y `height`, también las que montas dentro de una cadena de PHP; si tu hoja nombra `.af-prose{`, lleva `.af-prose{max-width:none;` y `.af-post>*,.af-page>*{max-width:none}` y ninguna regla estrecha `.af-prose`, `.af-post` ni `.af-page`; hoja sin `url()` relativas ni `@import` |
| `capturas` | (opcional) cero errores de JavaScript, cero 5xx, cero desborde a 390 px | solo si el plan la activa |

## Lo prohibido

- **Cambiar solo colores y tipografías y llamarlo tema.** No pasa la puerta de estructura ni debe pasar.
- **Invertir galería y compra** en escritorio para parecer distinto.
- **Quitar huecos o datos** de una plantilla de módulo para simplificarla.
- **Enlazar fuentes, scripts, imágenes o hojas de otro dominio**, ni `@import`, ni bibliotecas, ni iconos como fuente (los iconos, SVG en línea).
- **Tocar el sistema** (`core/`, `modules/`, otros temas) o el banco, o escribir fuera de `salida/<slug>/`.
- Datos de ejemplo con pinta de reales: correos, teléfonos, direcciones o marcas de verdad. Todo inventado y con pinta de inventado (`tienda.test`), y **sin teléfonos**: un número «de relleno» con forma de móvil es el de alguien.
- Dar por bueno lo que no se ha comprobado. Si una puerta no aplica, se dice.

## Referencias

- `skill/referencias/funciones.md` — las funciones de plantilla.
- `skill/referencias/clases.md` — el contrato de clases, los atributos `data-af-*` y las variables de color.
- `skill/referencias/huecos-y-datos.md` — los huecos y los datos que recibe cada plantilla.
- `skill/referencias/fallos-frecuentes.md` — lo que ya ha hecho tropezar a alguien. **Léelo antes de la fase 4.**
- `skill/plantillas/descomposicion.md` — la tabla de la fase 2.
- `docs/puertas.md` y `docs/primer-tema.md` — qué mira cada puerta y el recorrido completo de un tema.
