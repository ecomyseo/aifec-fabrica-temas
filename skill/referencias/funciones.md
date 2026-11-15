# Funciones de plantilla

Todas están disponibles en cualquier plantilla del tema. Las de `base_theme_*` las define el tema base, así que valen en un tema hijo mientras `base` sea su padre.

| Función | Para qué | Notas |
|---|---|---|
| `e($valor)` | Escapa para HTML. | **Todo dato impreso pasa por aquí.** Es la defensa contra la inyección de HTML. |
| `t('Texto en inglés', ['n' => 3])` | Traduce una cadena. | La clave es la cadena inglesa; su traducción va en `lang/es.php`. Los parámetros se escriben `{n}`. |
| `tn('{n} product', '{n} products', $n)` | Plural. | La clave del catálogo es `'{n} product\|{n} products'` (con la barra). |
| `url('/ruta')` | Dirección de una ruta de la tienda. | Respeta el prefijo del sitio y el idioma. |
| `route('nombre')` | Dirección de una ruta con nombre (`cart`, `search`, `account`…). | Falla si la ruta no existe: se comprueba antes con `base_theme_can('cart')`. |
| `money($céntimos, $moneda)` | Un importe ya formateado. | **Siempre enteros en céntimos**, nunca decimales. |
| `hook('nombre', …)` | Enchufe para módulos y plugins. | Devuelve HTML ya listo. Se conserva en cada plantilla que se sustituye. |
| `asset(…)`, `attrs([…])`, `json_html($datos)` | Recursos del tema, atributos HTML y JSON seguro dentro de una página. | `json_html` es lo que va dentro de `<script type="application/json">`. |
| `page_head($page)` | **Obligatoria en el `<head>` del envoltorio.** | Título, descripción, canónica, robots, idiomas, datos para compartir, JSON-LD, variables del tema y el hueco `head`. |
| `page_meta($page)` | El array completo de la página. | Para `body_class`, `breadcrumbs`, `type`. |
| `shop_logo($attrs = [])` | El logotipo de la cabecera. | La imagen elegida en Ajustes o, si no hay, el nombre de la tienda ya escapado. **Se usa en vez de escribir el nombre a mano.** |
| `theme_styles()` / `theme_scripts()` | Las etiquetas `<link>` y `<script defer>` del tema y de sus padres. | **Se usan en vez de escribir las direcciones a mano.** |
| `theme_option('clave', $defecto)` | Una opción del tema. | La que el comerciante cambia en el personalizador. |
| `menu('main')` | Elementos de un menú. | `[['label', 'url', 'current', 'children' => […]]]`. Puede venir vacío: se comprueba. Menús: `main`, `footer`, `legal`. |
| `breadcrumbs($page['breadcrumbs'])` | Migas accesibles. | O la pieza `partials/breadcrumbs`. |
| `image_tag($imagen, 'card', ['class' => '…'])` | `<img>` con ancho, alto, texto alternativo y carga diferida. | Sin imagen, un hueco del mismo tamaño. La primera imagen de la página lleva `['loading' => 'eager', 'fetchpriority' => 'high']`. Tamaños: `thumb`, `card`, `large`. |
| `$this->partial('partials/product-card', ['product' => $c])` | Una pieza del tema. | Se busca en el tema activo y en sus padres. Las piezas de un módulo se llaman `catalog::front/partials/filters`. |
| `$this->layout('layout', ['page' => $page, 'filters' => true])` | Empieza una plantilla de módulo dentro del envoltorio. | `filters => true` activa el botón Filtros de la barra del móvil: solo en páginas con filtros. |
| `base_theme_can('search'\|'cart'\|'account')` | ¿Existe esa ruta? | La cabecera y la barra solo pintan los accesos que existen. |
| `base_theme_link('cart')` | Dirección de esa ruta. | |
| `app()->settings()->str('store.name', '')` | Un ajuste de la tienda. | Nombre, correo, teléfono y dirección: `store.name`, `store.email`, `store.phone`, `store.address`. |

## Reglas de uso

- **Nada personal en el HTML.** Las páginas se guardan en caché y se sirven a todo el mundo: el contador del carrito y el saludo los rellena `theme.js`. No se pinta el nombre de nadie ni el contenido del carrito.
- **Nada de `echo` de un dato sin `e()`.** El validador avisa de `<?= $variable ?>` sin escapar: solo es aceptable en HTML que el sistema ya limpió (descripciones y resúmenes de producto).
- Un `<?= hook('…') ?>` se escribe directamente; no se guarda su resultado en una variable para pintarlo después (se ejecutaría el hueco dos veces si se llama dos).
- PHP **7.4 a 8.4**: sin `match`, sin tipos unión, sin propiedades promocionadas, sin `?->`. Un `functions.php` declara sus funciones dentro de `if (!function_exists('…'))`.
- Un `partial` recibe solo lo que se le pasa: nada de variables globales.
