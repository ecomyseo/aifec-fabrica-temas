<?php
/**
 * AIFEC — ficha de producto de __Nombre__ (sustituye `catalog::front/product`): el título y los datos de referencia van
 * en una cabecera propia sobre las dos columnas; la galería a la izquierda y, a la derecha, la oferta (precio y
 * disponibilidad) y la compra. Debajo, las secciones. Conserva todos los datos, los formularios y los huecos
 * `product.*` de la plantilla original.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 *
 * @var array<string,mixed>                  $page             datos de cabecera (ver Aifec\Front\Page)
 * @var array<string,mixed>                  $product          ProductData
 * @var array<int,array<string,mixed>>       $crumbs
 * @var array<int,array<string,mixed>>       $related          tarjetas de los productos relacionados
 * @var bool                                 $can_buy          existe la ruta cart.add
 * @var array<string,mixed>|null             $initial          variante elegida de serie (solo con variantes)
 * @var array<string,mixed>                  $price            bloque de precio de lo que se enseña
 * @var string                               $sku
 * @var array<string,mixed>                  $stock            disponibilidad de lo que se enseña
 * @var string                               $stock_class      is-ok, is-low o is-out
 * @var string                               $delivery         plazo de entrega en palabras (puede ir vacío)
 * @var bool                                 $sold_out
 * @var string                               $summary_html
 * @var string                               $description_html
 * @var array<int,array<string,string>>      $faqs             question, answer (HTML limpio)
 * @var array<string,mixed>|null             $variants_data    lo que lee theme.js (solo con variantes)
 * @var string                               $choose_action    dirección del paso que resuelve la variante sin JavaScript
 */

$this->layout('layout', ['page' => $page]);
$sk_p = $product;
$sk_has_variants = $initial !== null && is_array($variants_data);
$sk_images = isset($sk_p['images']) && is_array($sk_p['images']) ? array_values($sk_p['images']) : [];
$sk_rating = isset($sk_p['rating']) && is_array($sk_p['rating']) ? $sk_p['rating'] : null;
$sk_avg = $sk_rating !== null ? max(0.0, min(5.0, (float) $sk_rating['average'])) : 0.0;
$sk_count = $sk_rating !== null ? (int) $sk_rating['count'] : 0;
$sk_min = max(1, (int) $sk_p['min_qty']);
$sk_max = (int) $sk_p['max_qty'] > 0 ? (int) $sk_p['max_qty'] : null;
$sk_selected = $sk_has_variants && isset($initial['values']) && is_array($initial['values']) ? $initial['values'] : [];

// La tabla de características: los atributos visibles, los datos públicos que añaden los plugins y las referencias.
$sk_specs = [];
foreach (is_array($sk_p['attributes']) ? $sk_p['attributes'] : [] as $sk_attr) {
    $sk_specs[] = [(string) $sk_attr['name'], (string) $sk_attr['value']];
}
foreach (is_array($sk_p['extra']) ? $sk_p['extra'] : [] as $sk_extra) {
    if (is_array($sk_extra) && !empty($sk_extra['public']) && isset($sk_extra['label']) && isset($sk_extra['value']) && is_scalar($sk_extra['value']) && (string) $sk_extra['value'] !== '') {
        $sk_specs[] = [(string) $sk_extra['label'], (string) $sk_extra['value']];
    }
}
foreach ([[t('GTIN'), $sk_p['gtin']], [t('MPN'), $sk_p['mpn']]] as $sk_ref) {
    if ($sk_ref[1] !== null && (string) $sk_ref[1] !== '') {
        $sk_specs[] = [$sk_ref[0], (string) $sk_ref[1]];
    }
}
$sk_facts = array_slice(is_array($sk_p['facts']) ? $sk_p['facts'] : [], 0, 6);
?>
<div class="af-container af-section">
    <?= $this->partial('partials/breadcrumbs', ['crumbs' => $crumbs]) ?>
    <article class="af-product sk-product"<?= $sk_has_variants ? ' data-af-variants' : '' ?>>
        <header class="sk-product-head">
            <?= hook('product.summary.before', $sk_p) ?>
            <h1 class="af-title"><?= e((string) $sk_p['name']) ?></h1>
            <ul class="sk-product-meta af-small af-muted">
                <?php if (is_array($sk_p['brand'])) : ?>
                    <li><a href="<?= e((string) $sk_p['brand']['url']) ?>"><?= e((string) $sk_p['brand']['name']) ?></a></li>
                <?php endif; ?>
                <?php if ($sk_count > 0) : ?>
                    <li>
                        <span class="af-stars" role="img" aria-label="<?= e(t('{rating} out of 5', ['rating' => number_format($sk_avg, 1, '.', '')])) ?>" style="--rating:<?= e(number_format($sk_avg, 1, '.', '')) ?>"></span>
                        (<?= e($sk_count) ?>)
                    </li>
                <?php endif; ?>
                <?php if ($sku !== '' || $sk_has_variants) : ?>
                    <li><?= e(t('SKU')) ?>: <span data-af-sku><?= e($sku) ?></span></li>
                <?php endif; ?>
            </ul>
        </header>
        <div class="af-product-gallery">
            <div class="af-gallery" data-af-gallery>
                <?php
                $sk_first = $sk_images !== [] ? $sk_images[0] : null;
                if ($sk_first !== null && (string) $sk_first['alt'] === '') {
                    $sk_first['alt'] = (string) $sk_p['name'];
                }
                ?>
                <figure class="af-gallery-main">
                    <?= image_tag($sk_first, 'large', ['loading' => 'eager', 'fetchpriority' => 'high', 'data-af-gallery-main' => true]) ?>
                </figure>
                <?php if (count($sk_images) > 1) : ?>
                    <ul class="af-gallery-thumbs">
                        <?php foreach ($sk_images as $sk_i => $sk_image) : ?>
                            <li><a href="<?= e((string) $sk_image['large']) ?>" data-src="<?= e((string) $sk_image['large']) ?>" data-alt="<?= e((string) $sk_image['alt'] !== '' ? (string) $sk_image['alt'] : (string) $sk_p['name']) ?>" data-image-id="<?= e($sk_image['id']) ?>" aria-label="<?= e(t('Image {n}', ['n' => $sk_i + 1])) ?>"<?= $sk_i === 0 ? ' aria-current="true"' : '' ?>>
                                <?= image_tag($sk_image, 'thumb', ['alt' => '']) ?>
                            </a></li>
                        <?php endforeach; ?>
                    </ul>
                <?php endif; ?>
            </div>
            <?= hook('product.gallery.after', $sk_p) ?>
        </div>
        <div class="af-product-buy">
            <section class="sk-product-offer">
                <?= $this->partial('partials/price', ['price' => $price, 'size' => 'lg', 'live' => $sk_has_variants]) ?>
                <?= hook('product.price.after', $sk_p) ?>
                <p class="af-availability <?= e($stock_class) ?>" data-af-availability><?= e((string) $stock['label']) ?></p>
                <?php if ($delivery !== '') : ?>
                    <p class="af-small af-muted"><?= e($delivery) ?></p>
                <?php endif; ?>
            </section>
            <?php if ($can_buy) : ?>
                <form class="sk-product-form" method="post" action="<?= e(route('cart.add')) ?>" data-af-cart-add<?= hook('webmcp.form', 'add_to_cart') ?>>
                    <input type="hidden" name="product_id" value="<?= e($sk_p['id']) ?>"<?= hook('webmcp.param', 'add_to_cart', 'product_id') ?>>
                    <input type="hidden" name="variant_id" value="<?= e($sk_has_variants ? $initial['id'] : 0) ?>" data-af-variant-id<?= hook('webmcp.param', 'add_to_cart', 'variant_id') ?>>
                    <?php if ($sk_has_variants) : ?>
                        <?= $this->partial('catalog::front/partials/options', ['options' => $sk_p['options'], 'selected' => $sk_selected, 'tool' => 'add_to_cart']) ?>
                        <script type="application/json" data-af-variants-data><?= json_html($variants_data) ?></script>
                    <?php endif; ?>
                    <div class="af-buy-row">
                        <?= $this->partial('partials/qty', ['name' => 'qty', 'value' => $sk_min, 'min' => $sk_min, 'max' => $sk_max, 'tool' => 'add_to_cart']) ?>
                        <button type="submit" class="af-btn af-btn-primary af-btn-lg" data-af-add<?= $sk_has_variants && $choose_action !== '' ? ' formaction="' . e($choose_action) . '"' : '' ?><?= $sold_out ? ' disabled' : '' ?>><?= e($sold_out && !$sk_has_variants ? t('Sold out') : t('Add to cart')) ?></button>
                    </div>
                </form>
            <?php elseif ($sk_has_variants) : ?>
                <div>
                    <?= $this->partial('catalog::front/partials/options', ['options' => $sk_p['options'], 'selected' => $sk_selected]) ?>
                    <script type="application/json" data-af-variants-data><?= json_html($variants_data) ?></script>
                </div>
            <?php endif; ?>
            <?= hook('product.buy.after', $sk_p) ?>
            <?php if ($sk_facts !== []) : ?>
                <ul class="af-facts">
                    <?php foreach ($sk_facts as $sk_fact) : ?>
                        <li><span><?= e((string) $sk_fact['label']) ?></span> <strong><?= e((string) $sk_fact['value']) ?></strong></li>
                    <?php endforeach; ?>
                </ul>
            <?php endif; ?>
            <?php if ($summary_html !== '') : ?>
                <section class="sk-product-summary af-prose"><?= $summary_html ?></section>
            <?php endif; ?>
            <?= hook('product.summary.after', $sk_p) ?>
        </div>
    </article>

    <div class="sk-product-sections">
        <?php if ($description_html !== '') : ?>
            <section class="af-section" id="af-description">
                <h2><?= e(t('Description')) ?></h2>
                <div class="af-prose"><?= $description_html ?></div>
            </section>
        <?php endif; ?>
        <?= hook('product.tabs', $sk_p) ?>
        <?php if ($sk_specs !== []) : ?>
            <section class="af-section" id="af-specs">
                <h2><?= e(t('Specifications')) ?></h2>
                <div class="af-table-wrap">
                    <table class="af-table">
                        <tbody>
                            <?php foreach ($sk_specs as $sk_spec) : ?>
                                <tr><th scope="row"><?= e($sk_spec[0]) ?></th><td><?= e($sk_spec[1]) ?></td></tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
            </section>
        <?php endif; ?>
        <?php if ($faqs !== []) : ?>
            <section class="af-section" id="af-faq">
                <h2><?= e(t('Frequently asked questions')) ?></h2>
                <?php foreach ($faqs as $sk_faq) : ?>
                    <details class="af-card">
                        <summary><?= e($sk_faq['question']) ?></summary>
                        <div class="af-prose"><?= $sk_faq['answer'] ?></div>
                    </details>
                <?php endforeach; ?>
            </section>
        <?php endif; ?>
        <?php if ($related !== []) : ?>
            <section class="af-section" id="af-related">
                <h2><?= e(t('Related products')) ?></h2>
                <ul class="af-grid af-cols-4 sk-grid">
                    <?php foreach ($related as $sk_card) : ?>
                        <li><?= $this->partial('partials/product-card', ['product' => $sk_card]) ?></li>
                    <?php endforeach; ?>
                </ul>
            </section>
        <?php endif; ?>
        <?= hook('product.bottom', $sk_p) ?>
    </div>
</div>
