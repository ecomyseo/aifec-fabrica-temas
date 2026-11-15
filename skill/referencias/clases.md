# El contrato de clases

Las plantillas de los módulos solo usan estas clases; un tema nuevo tiene que darles estilo (o heredar el del tema base, que ya lo hace). Un hijo de `base` hereda la hoja del padre y escribe encima solo lo que cambia; con `"css": "replace"` en `theme.json` su hoja sustituye a la del padre y entonces **tiene que dar estilo a todas**.

## Las clases del contrato

- **Estructura**: `af-container`, `af-section`, `af-grid` + `af-cols-2|3|4|5|6` (rejilla que baja sola en móvil), `af-stack`, `af-row`, `af-split` (contenido y lateral), `af-sr` (solo lectores de pantalla), `af-hide-sm`, `af-show-sm`.
- **Texto**: `af-title` (el `h1` de la página), `af-subtitle`, `af-muted`, `af-small`, `af-prose` (contenido largo).
- **Controles**: `af-btn` (`af-btn-primary`, `af-btn-ghost`, `af-btn-block`, `af-btn-sm`, `af-btn-lg`), `af-input`, `af-select`, `af-textarea`, `af-field` (etiqueta + control + `af-hint` + `af-error`), `af-check`, `af-radio-card`, `af-qty`.
- **Avisos y marcas**: `af-alert af-alert-ok|bad|info|warn`, `af-badge` (`af-badge-sale`, `af-badge-new`, `af-badge-out`), `af-stars`.
- **Comercio**: `af-product-card`, `af-price` (`af-price-now`, `af-price-old`, `af-price-off`, `af-price-note`), `af-listing` (`af-listing-filters` + `af-listing-results`), `af-filter`, `af-product` (`af-product-gallery` **a la izquierda** + `af-product-buy` **a la derecha**), `af-gallery` (`af-gallery-main`, `af-gallery-thumbs`), `af-variants` (`af-variant` con `aria-pressed`), `af-availability` (`is-ok`, `is-low`, `is-out`), `af-facts`, `af-tabs`, `af-cart` (`af-cart-line`), `af-totals` (`af-totals-row`, `af-totals-total`), `af-steps`, `af-summary`, `af-table`, `af-card`, `af-empty`.
- **Móvil**: `af-mobile-bar`, `af-drawer` (panel lateral: menú, filtros, carrito) con `af-drawer-backdrop`.

### Clases que la fábrica busca para identificar las cinco superficies

`af-header`, `af-product-card` (la primera de la página), `af-listing`, `af-product` y `af-footer`. **Si una plantilla no las lleva, la puerta de estructura no encuentra la superficie y no pasa.** Van en el elemento raíz de cada superficie, no en un hijo.

## Variables de color y medida

Todo color sale de variables, y un tema hijo cambia el aspecto cambiando variables:

`--bg`, `--surface`, `--surface-2`, `--ink`, `--muted`, `--line`, `--accent`, `--accent-ink`, `--ok`, `--warn`, `--bad`, `--sale`, `--radius`, `--container`, `--font`, `--font-head`, `--font-size`, `--header-h`, `--bar-h` (alto de la barra del móvil: la puerta de móvil lo lee de `:root`).

Un campo de `theme.json` con `"var": "--mi-color"` sale solo como variable CSS dentro de `page_head()`. Tiene que **usarse** en alguna hoja (`var(--mi-color)`).

## Comportamiento que pone `theme.js` (atributos `data-af-*`, todo por delegación)

| Atributo | Qué hace |
|---|---|
| `data-af-drawer-open="id"` / `data-af-drawer-close` | Abre y cierra un `af-drawer`; Escape y pulsar fuera cierran. El `id` tiene que existir en la página. |
| `data-af-cart-count` | Se rellena con las unidades del carrito. Un elemento vacío con `hidden`. |
| `form[data-af-cart-add]` | Añade al carrito por `fetch` y actualiza el contador; sin JavaScript el formulario funciona igual. |
| `data-af-qty` | Botones − y + de cantidad. |
| `data-af-autosubmit` | Envía su formulario al cambiar (orden y filtros del listado). |
| `data-af-gallery` | Cambia la imagen principal al pulsar una miniatura (`[data-af-gallery-main]`, `a[data-src]`). |
| `data-af-variants` (con un `<script type="application/json" data-af-variants-data>` dentro) | Al elegir opciones, actualiza precio, disponibilidad, imagen y el campo `variant_id`. |
| `data-af-tabs`, `data-af-toggle="id"` | Pestañas accesibles y bloques que se enseñan u ocultan. |

`theme.js` del padre **se sigue cargando** (no declares `"js": "replace"`). Si necesitas comportamiento propio, un guion pequeño aparte (≤ 8 KB) cargado con `defer`.

## Móvil (bloqueante)

- Cabecera fija o pegajosa arriba (`position: sticky`) y **barra de acciones fija abajo** (`af-mobile-bar`, `position: fixed`) con Buscar y Carrito reales y con su contador, Cuenta, y Filtros solo donde hay filtros que funcionan.
- La barra no tapa nada: el contenido reserva su alto (`.af-has-bar{padding-bottom:…}`) y respeta `env(safe-area-inset-bottom)`. Áreas táctiles de 44 × 44 px como mínimo, foco visible (`:focus-visible`), etiquetas accesibles.
- **Cero desbordamiento horizontal** entre 360 y 430 px: todo contenedor con desplazamiento lleva `position: relative`; toda fila de botones, `flex-wrap: wrap`; las tablas, dentro de un contenedor con desplazamiento (`af-table-wrap`).

## Peso

`theme.css` ≤ 45 000 bytes y cada guion ≤ 25 000; ni una petición a otro dominio (fuentes del sistema o `woff2` propias con `font-display: swap`); toda imagen con `width` y `height`; nada de `@import`, ni de bibliotecas, ni de iconos como fuente.
