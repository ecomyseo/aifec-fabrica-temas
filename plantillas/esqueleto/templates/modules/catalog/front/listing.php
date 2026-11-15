<?php
/**
 * AIFEC — listado de productos de __Nombre__ (sustituye `catalog::front/listing`): cabecera de sección con el
 * recuento y el orden en una barra propia, rejilla como lista de tres columnas y, a la derecha, el panel de filtros
 * (en móvil, el panel lateral que abre el botón Filtros de la barra inferior). Conserva todos los datos de la
 * plantilla original y su estructura de variables.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 *
 * @var array<string,mixed>                       $page      datos de cabecera (ver Aifec\Front\Page)
 * @var array<int,array<string,mixed>>            $crumbs
 * @var string                                    $kind      category, brand o search
 * @var string                                    $heading   título de la página
 * @var string                                    $description HTML limpio de la descripción (puede ir vacío)
 * @var array<int,array<string,mixed>>            $children  subcategorías: name, url, image, product_count
 * @var array<string,mixed>                       $result    lo que da catalog->listing()
 * @var array<int,array<string,mixed>>            $facets
 * @var \Aifec\Modules\Catalog\Front\ListingQuery $query
 * @var string                                    $base      dirección del listado sin parámetros
 * @var string                                    $clear_url dirección sin filtros
 * @var callable                                  $url       recibe un número de página y da su dirección
 */

$this->layout('layout', ['page' => $page, 'filters' => true]);
$sk_total = (int) $result['total'];
$sk_cols = (int) theme_option('listing_cols', 3) === 4 ? 4 : 3;
?>
<div class="af-container af-section">
    <?= $this->partial('partials/breadcrumbs', ['crumbs' => $crumbs]) ?>
    <section class="af-listing sk-listing">
        <div class="af-listing-results">
            <header class="sk-listing-head">
                <h1 class="af-title"><?= e($heading) ?></h1>
                <?php if ($description !== '' && $query->page === 1) : ?>
                    <div class="af-prose"><?= $description ?></div>
                <?php endif; ?>
                <?php if ($children !== []) : ?>
                    <ul class="sk-listing-children" aria-label="<?= e(t('Subcategories')) ?>">
                        <?php foreach ($children as $sk_child) : ?>
                            <li><a href="<?= e((string) $sk_child['url']) ?>"><?= e((string) $sk_child['name']) ?> <small class="af-muted">(<?= e((int) $sk_child['product_count']) ?>)</small></a></li>
                        <?php endforeach; ?>
                    </ul>
                <?php endif; ?>
            </header>
            <div class="sk-listing-bar">
                <p class="af-muted" role="status"><?= e(tn('{n} product', '{n} products', $sk_total)) ?></p>
                <?php if ($sk_total > 0 && count($result['sorts']) > 1) : ?>
                    <label class="af-sr" for="af-sort"><?= e(t('Sort by')) ?></label>
                    <select id="af-sort" class="af-select" name="sort" form="af-filters-form" data-af-autosubmit>
                        <?php foreach ($result['sorts'] as $sk_code => $sk_label) : ?>
                            <option value="<?= e((string) $sk_code) ?>"<?= (string) $sk_code === $query->sort ? ' selected' : '' ?>><?= e((string) $sk_label) ?></option>
                        <?php endforeach; ?>
                    </select>
                    <noscript><button type="submit" class="af-btn af-btn-sm" form="af-filters-form"><?= e(t('Sort')) ?></button></noscript>
                <?php endif; ?>
            </div>
            <?php if ($result['items'] !== []) : ?>
                <h2 class="af-sr"><?= e(t('Products')) ?></h2>
                <ul class="af-grid af-cols-<?= e($sk_cols) ?> sk-grid">
                    <?php foreach ($result['items'] as $sk_card) : ?>
                        <li><?= $this->partial('partials/product-card', ['product' => $sk_card]) ?></li>
                    <?php endforeach; ?>
                </ul>
                <?= $this->partial('partials/pagination', ['page' => $result['page'], 'pages' => $result['pages'], 'url' => $url]) ?>
            <?php else : ?>
                <div class="af-card af-empty">
                    <p class="af-empty-title"><?= e(t('No products found')) ?></p>
                    <?php if ($query->hasFilters()) : ?>
                        <p class="af-muted"><?= e(t('Try removing some filters.')) ?></p>
                        <p><a class="af-btn" href="<?= e($clear_url) ?>"><?= e(t('Clear filters')) ?></a></p>
                    <?php elseif ($kind === 'search') : ?>
                        <p class="af-muted"><?= e(t('Check the spelling or try fewer or different words.')) ?></p>
                    <?php else : ?>
                        <p class="af-muted"><?= e(t('There are no products here yet. Come back soon.')) ?></p>
                    <?php endif; ?>
                </div>
            <?php endif; ?>
        </div>
        <?= $this->partial('catalog::front/partials/filters', [
            'action' => $base,
            'facets' => $facets,
            'query' => $query,
            'range' => $result['price_range'],
            'clear_url' => $clear_url,
        ]) ?>
    </section>
</div>
