# Fallos frecuentes al construir un tema

Lo que ya ha hecho tropezar a alguien, con lo que pasó y cómo se evita. Se lee **antes** de la fase 4 del skill. Cada tropiezo nuevo se apunta aquí en cuanto se arregla.

## La descripción de `theme.json` también se traduce, y va en inglés

Las etiquetas de las opciones, los nombres de los grupos y la `description` de `theme.json` cuentan como cadenas del tema. Una descripción en castellano sin su clave inglesa da «missing translation» en la puerta de traducciones; una descripción en inglés sin su entrada en `lang/es.php`, también. **Se escribe en inglés y se traduce en `lang/es.php`.** El `name` no se traduce.

## Una plantilla copiada trae sus cadenas: hay que traducirlas todas

Al sustituir `listing.php` o `product.php` se copian cadenas (`'Sort by'`, `'Frequently asked questions'`…) que el catálogo del módulo ya traduce, pero **el catálogo del tema es aparte**: `i18n:check themes/<slug>` mira solo el tema. Se pegan en `lang/es.php` las que dé la puerta de traducciones. La clave de un plural es `'{n} product|{n} products'`, con la barra.

## Añadir o renombrar clases propias no crea un diseño distinto

La puerta de estructura **no cuenta** las clases que no empiezan por `af-`: ni su nombre ni que existan. Un tema que solo cambia `class="af-header"` por `class="af-header mi-cabecera"` se parece a la cabecera de base un 1,00. Lo que cuenta es la etiqueta, su orden, su anidado y las clases `af-…` que lleva. Para diferir hay que cambiar la composición: otro orden de los bloques, otros contenedores, otras etiquetas (`figure`, `section`, `ul`/`li`, `table`, `details`), otro reparto entre filas.

## Un tema hecho desde el esqueleto sin cambiarlo es un clon del anterior

El esqueleto ya tiene cinco superficies propias respecto a `base`, pero todos los temas que salen de él **empiezan siendo iguales entre sí**. Si el tema anterior sigue en `salida/` (o instalado en el banco), el nuevo se rechaza con «se parece al tema …» en las cinco. Rediséñalas según el encargo antes de pasar las puertas.

## La clase de contrato va en el elemento raíz de la superficie

La puerta busca el primer elemento con la clase `af-header`, `af-product-card` (la primera de la página), `af-listing`, `af-product` o `af-footer`. Si la clase está en un hijo, o falta, dice que falta la superficie. En la tarjeta, además, la primera de la página es la que se mide: no pongas una tarjeta distinta antes en la portada.

## Un acceso de la barra del móvil tiene que llevar a algún sitio

`data-af-drawer-open="af-search"` es real **solo si la página trae `id="af-search"`**: ese panel lo pinta `partials/drawers.php`, que el envoltorio incluye. Un `href="#"` o un panel que no existe es un acceso decorativo y la puerta de móvil lo rechaza. El botón Filtros solo sale en páginas con filtros (`af-listing-filters`), y entonces su panel (`id="af-filters"`) tiene que estar.

## «Sticky» solo en escritorio no vale para el móvil

La puerta de móvil mira las reglas que valen a 390 px: una cabecera con `position: sticky` solo dentro de `@media (min-width: 900px)` no es pegajosa en el teléfono. Y una regla de escritorio que la deja en `position: relative` es correcta siempre que la de móvil siga siendo `sticky`.

## La hoja efectiva no es solo la tuya

`theme_styles()` carga la del tema base y, encima, la tuya; solo con `"css": "replace"` en `theme.json` la tuya sustituye a la del padre (y entonces tiene que traer **todo**: el contrato de móvil, la barra, el foco visible…). La puerta de móvil analiza la hoja efectiva, no solo la tuya.

## `<?= $variable ?>` sin `e()` da aviso

El validador avisa de cada plantilla que imprime una variable sin pasar por una función de escape. Es aceptable en HTML que el sistema ya limpió (`$description`, `$summary_html`); en cualquier otro dato, `e()`. Un `<?= hook('…') ?>` se escribe directamente.

## PHP 7.4 a 8.4

Sin `match`, sin tipos unión, sin propiedades promocionadas, sin `?->`, sin `str_contains` fuera de `core/polyfill.php`. La puerta de limpieza ejecuta `php -l` con todos los ejecutables de `php_versiones` del plan: un `.php` que vale en 8.3 puede ser un error fatal en 7.4.

## Los ficheros se escriben con la herramienta de escribir, no con `echo` ni heredocs

Un script de shell que escribe un PHP se come las barras invertidas y los `$`, y un `python -c "…"` con comillas dobles ejecuta lo que haya entre comillas invertidas. Se usan las herramientas de escribir y editar ficheros. Tras escribir, `php -l` en 7.4.

## El tema no es un sitio donde guardar cosas

Un tema no incluye capturas, zips, mapas de código ni `node_modules`: la puerta de limpieza los rechaza. Solo `preview.png` (1200 × 900) o `mockup.png` en la raíz; lo demás, imágenes dentro de `assets/`.

## Lo que `theme:check` no ve y las pruebas del sistema sí (puerta «contrato»)

Los tres primeros temas fabricados (`cafe`, `metrica` y `lookbook`) pasaban `theme:check` y rompieron la batería de AIFEC al instalarse, por dos cosas:

- **Una imagen escrita sin `width` y `height`**, aunque sea dentro de una cadena de PHP que solo comprueba si el logotipo es una imagen. La prueba lee el texto de la plantilla, no lo que pinta: cualquier `<img …>` literal cuenta. La comprobación se lleva a una función de `functions.php` y la plantilla no escribe la etiqueta.
- **Estrechar el texto con `max-width` en `.af-prose`, `.af-post` o `.af-page`.** En AIFEC el texto de entradas, páginas y fichas ocupa el ancho de su contenedor. Si quieres una columna de lectura, el límite va en el contenedor (la sección, la rejilla), y la hoja lleva tal cual `.af-prose{max-width:none;…}` y `.af-post>*,.af-page>*{max-width:none}`.

Se ve antes de las puertas con `python puertas/contrato.py` (los argumentos, como cualquier puerta) o, más cómodo, con `python fabrica.py puertas <slug> --solo contrato`.

## Al seguir el skill con un encargo de ejemplo

Se construyó «Floristería Pétalo» (`salida/floristeria-petalo/`) siguiendo este skill al pie de la letra. Lo que salió mal, y lo que se cambió:

1. **Sin sitio donde guardar la descomposición.** La fase 2 pedía rellenar la tabla antes de tener carpeta. Ahora `esqueleto.py` deja la tabla como `NOTAS.md` del tema y la fase 2 se rellena en un borrador.
2. **`esqueleto.py` imprimía mal las tildes** en la consola de Windows («Tema �…�»). Ahora escribe en UTF-8.
3. **Redeclarar campos de `theme.json` multiplica las cadenas.** Cambiar los colores por defecto obliga a volver a declarar cada campo (`bg`, `ink`, `accent`…) y la puerta de traducciones pidió **25 cadenas** de golpe: etiquetas de colores, de tipografía y los nombres de los grupos. El esqueleto solo trae 41. Se pegan todas en `lang/es.php`; las que la puerta da ya van listas para pegar.
4. **Un panel que en escritorio es una columna fija no se convierte en cajón con solo un botón.** El listado de `base` deja `af-listing-filters` estático a partir de 900 px; para abrirlo desde un botón hubo que reescribir su posición y su transformación en escritorio y devolver el botón de cerrar (`af-drawer-head af-show-sm` se oculta ahí con `!important`).
5. **`fabrica.py puertas` solo da una línea por puerta.** Para ver la tabla de parecidos o las cadenas que faltan hay que usar `python skill/informe.py <slug>`. Sin eso se corregía a ciegas.
6. **Los temas de prueba se quedan en el banco.** Cada tema que pasa por las puertas se copia a `estado/banco/themes/<slug>/` y cuenta después como «tema que ya existe» (aparece en el encargo y en la tabla de parecidos). Un tema de pega se borra de ahí, o se rehace el banco (`python fabrica.py banco --rehacer`).
7. **Rediseñar la ficha puede acercarla a otro tema.** Pasar el título de una cabecera sobre las dos columnas a la columna de compra y poner la oferta en su propia `section` **subió** el parecido de la ficha con `despensa` de 0,63 a 0,68: la ficha lleva tantos datos obligatorios (galería, precio, formulario, hechos) que dos fichas hechas con razón se parecen. Es la superficie más cercana al límite: se mira su cifra después de cada cambio con `python skill/informe.py <slug> --puerta estructura`, y si sube, se cambia el orden y el anidado de las secciones, no solo dónde va el título.
