<?php
/**
 * AIFEC — tarjeta de producto de __Nombre__: una figura con su imagen y sus insignias en lista, y debajo, en un
 * pie aparte, la marca, el nombre (que es el enlace que cubre toda la tarjeta), la valoración y el precio.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 *
 * @var array<string,mixed> $product ProductCard: name, url, image, price, availability, brand, rating, badges
 */

$sk_p = isset($product) && is_array($product) ? $product : [];
$sk_url = isset($sk_p['url']) ? (string) $sk_p['url'] : '';
$sk_name = isset($sk_p['name']) ? (string) $sk_p['name'] : '';
$sk_brand = isset($sk_p['brand']) && is_string($sk_p['brand']) ? trim($sk_p['brand']) : '';
$sk_image = isset($sk_p['image']) && is_array($sk_p['image']) ? $sk_p['image'] : null;
$sk_price = isset($sk_p['price']) && is_array($sk_p['price']) ? $sk_p['price'] : [];
$sk_rating = isset($sk_p['rating']) && is_array($sk_p['rating']) ? $sk_p['rating'] : null;
$sk_have = isset($sk_p['badges']) && is_array($sk_p['badges']) ? $sk_p['badges'] : [];
$sk_badges = array_values(array_intersect(['sale', 'new', 'out'], $sk_have));
$sk_compare = isset($sk_price['compare']) ? (int) $sk_price['compare'] : 0;
$sk_amount = isset($sk_price['amount']) ? (int) $sk_price['amount'] : 0;
$sk_percent = 0;
if ($sk_compare > $sk_amount && $sk_compare > 0) {
    $sk_percent = isset($sk_price['discount_percent']) && (int) $sk_price['discount_percent'] > 0
        ? (int) $sk_price['discount_percent']
        : intdiv(($sk_compare - $sk_amount) * 100 + intdiv($sk_compare, 2), $sk_compare);
}
$sk_avg = $sk_rating !== null && isset($sk_rating['average']) ? max(0.0, min(5.0, (float) $sk_rating['average'])) : 0.0;
$sk_count = $sk_rating !== null && isset($sk_rating['count']) ? (int) $sk_rating['count'] : 0;
?>
<article class="af-product-card sk-card<?= in_array('out', $sk_badges, true) ? ' is-out' : '' ?>">
    <figure class="sk-card-figure">
        <?= image_tag($sk_image, 'card', ['class' => 'sk-card-img', 'alt' => '']) ?>
        <?php if ($sk_badges !== []) : ?>
            <ul class="af-badges">
                <?php foreach ($sk_badges as $sk_badge) : ?>
                    <?php if ($sk_badge === 'sale') : ?>
                        <li class="af-badge af-badge-sale"><?= $sk_percent > 0 ? e('−' . $sk_percent . "\u{a0}%") : e(t('Sale')) ?></li>
                    <?php elseif ($sk_badge === 'new') : ?>
                        <li class="af-badge af-badge-new"><?= e(t('New')) ?></li>
                    <?php else : ?>
                        <li class="af-badge af-badge-out"><?= e(t('Sold out')) ?></li>
                    <?php endif; ?>
                <?php endforeach; ?>
            </ul>
        <?php endif; ?>
    </figure>
    <div class="sk-card-foot">
        <?php if ($sk_brand !== '' && (int) theme_option('show_brand_in_card', 1) === 1) : ?>
            <p class="sk-card-brand"><?= e($sk_brand) ?></p>
        <?php endif; ?>
        <h3 class="sk-card-name">
            <?php if ($sk_url !== '') : ?>
                <a class="sk-card-link" href="<?= e($sk_url) ?>"><?= e($sk_name) ?></a>
            <?php else : ?>
                <?= e($sk_name) ?>
            <?php endif; ?>
        </h3>
        <?php if ($sk_count > 0) : ?>
            <p class="sk-card-rating">
                <span class="af-stars" role="img" aria-label="<?= e(t('{rating} out of 5', ['rating' => number_format($sk_avg, 1, '.', '')])) ?>" style="--rating:<?= e(number_format($sk_avg, 1, '.', '')) ?>"></span>
                <small class="af-muted">(<?= e($sk_count) ?>)</small>
            </p>
        <?php endif; ?>
        <?= $this->partial('partials/price', ['price' => $sk_price, 'size' => 'sm']) ?>
    </div>
</article>
