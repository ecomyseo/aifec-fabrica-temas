# Huecos y datos de cada plantilla

## Huecos (`<?= hook('nombre', …) ?>`)

Un hueco es un punto donde un módulo o un plugin puede meter HTML. El tema ofrece los del envoltorio; **cada plantilla de módulo ofrece los suyos y un tema que la sustituya los conserva todos**.

| Dónde | Huecos |
|---|---|
| Envoltorio (`layout.php`) | `body.start`, `header.before`, `header.after`, `footer.before`, `footer.after`, `body.end` |
| Cabecera | `header.actions` (junto al carrito) |
| Pie | `footer.columns` |
| Portada | `home.top`, `home.bottom` |
| Ficha de producto | `product.summary.before`, `product.gallery.after`, `product.price.after`, `product.buy.after`, `product.summary.after`, `product.tabs`, `product.bottom` |
| Carrito | `cart.before`, `cart.lines.after`, `cart.totals.after`, `cart.after` |
| Caja | `checkout.before`, `checkout.review.after`, `checkout.after` |
| Cuenta y pedido | `account.dashboard`, `order.thanks` |

Además, los formularios llevan `hook('webmcp.form', 'nombre')` y los campos `hook('webmcp.param', 'nombre', 'campo')`: son los que dejan a un agente de IA rellenar la búsqueda y la compra. Se conservan tal cual.

## Qué recibe cada plantilla

Toda página de la tienda recibe **`$page`** (título, descripción, canónica, tipo, migas, datos estructurados): se pasa al envoltorio con `$this->layout('layout', ['page' => $page])`.

### Tarjeta de producto (`partials/product-card`, variable `$product`)

`name`, `url`, `image` (`id`, `url`, `alt`, `width`, `height`, `thumb`, `card`, `large`, `srcset`), `price` (bloque de precio), `brand`, `rating` (`average`, `count`), `badges` (`sale`, `new`, `out`), `availability`. **Todo se comprueba antes de usarlo**: puede faltar.

### Bloque de precio (`partials/price`, variable `$price`)

`amount`, `compare` (el anterior, o `null`), `on_sale`, `discount_percent`, `from`, `with_tax`, `currency`. Los importes son **enteros en céntimos**. La pieza `partials/price` pinta el precio actual, el anterior tachado y legible, la insignia del porcentaje y la nota de impuestos: se usa, no se reescribe.

### Listado (`modules/catalog/front/listing.php`)

`$page`, `$crumbs`, `$kind` (`category`, `brand`, `search`), `$heading`, `$description` (HTML limpio, puede ir vacío), `$children` (subcategorías: `name`, `url`, `image`, `product_count`), `$result` (`items`, `total`, `sorts`, `page`, `pages`, `price_range`), `$facets`, `$query` (`page`, `sort`, `hasFilters()`), `$base`, `$clear_url`, `$url` (función: número de página → dirección). El panel de filtros es una pieza del módulo (`catalog::front/partials/filters`, con el `id="af-filters"` que abre el botón de la barra): se llama con `action`, `facets`, `query`, `range` y `clear_url`. El select de orden lleva `form="af-filters-form"` y `data-af-autosubmit`.

### Ficha (`modules/catalog/front/product.php`)

`$page`, `$product` (`id`, `name`, `brand`, `rating`, `images`, `attributes`, `extra`, `gtin`, `mpn`, `facts`, `min_qty`, `max_qty`, `options`), `$crumbs`, `$related` (tarjetas), `$can_buy`, `$initial` (la variante elegida de serie, o `null`), `$price`, `$sku`, `$stock` (`label`) y `$stock_class` (`is-ok`, `is-low`, `is-out`), `$delivery`, `$sold_out`, `$summary_html`, `$description_html`, `$faqs` (`question`, `answer`), `$variants_data` (lo que lee `theme.js`), `$choose_action`.

Lo que no se puede perder al reescribirla: el formulario con `data-af-cart-add` y sus campos `product_id`, `variant_id` (`data-af-variant-id`) y `qty`; el `<script type="application/json" data-af-variants-data>` con `json_html($variants_data)`; los atributos `data-af-sku`, `data-af-availability`, `data-af-gallery`, `data-af-gallery-main` y `data-src` de las miniaturas; la pieza `catalog::front/partials/options` para las variantes; el botón con `data-af-add` y su `formaction` sin JavaScript.

### Portada (`home.php`)

Recorre las secciones que dan los módulos (`$af_sections`, cada una con `id` y `html`) y conserva los huecos `home.top` y `home.bottom`. Si ninguna sección trae un `h1`, pinta uno solo para lectores de pantalla (`af-sr`) con el nombre de la tienda: **un solo `h1` por página**.

## La página de muestra

Con la depuración encendida, `/tema/muestra` pinta todas las piezas y clases del contrato con datos de mentira (con `?filtros=1`, también la barra con el botón Filtros). Es lo primero que hay que mirar de un tema nuevo si el sitio no tiene productos.
