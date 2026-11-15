<?php
/**
 * AIFEC — cabecera de __Nombre__: tres pisos. Arriba, una franja fina con enlaces de servicio; en medio, el logotipo,
 * un buscador ancho y el carrito; debajo, el menú principal a todo el ancho. En móvil queda el piso del medio con el
 * botón del menú. Solo pinta los accesos cuya ruta existe.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

$sk_main = menu('main');
$sk_langs = app()->languages();
$sk_path = app()->request()->path;
$sk_top = (int) theme_option('header_top', 1) === 1;
?>
<header class="af-header sk-header">
    <?php if ($sk_top) : ?>
        <div class="sk-header-top af-hide-sm">
            <div class="af-container">
                <ul class="sk-header-links">
                    <?php if (base_theme_can('account')) : ?>
                        <li><a href="<?= e(base_theme_link('account')) ?>" data-af-account><?= e(t('My account')) ?></a></li>
                    <?php endif; ?>
                    <?php foreach (count($sk_langs) > 1 ? $sk_langs : [] as $sk_code) : ?>
                        <li><a href="<?= e(app()->url()->to($sk_path, [], $sk_code)) ?>" hreflang="<?= e($sk_code) ?>" lang="<?= e($sk_code) ?>"<?= $sk_code === app()->lang() ? ' aria-current="true"' : '' ?>><?= e(strtoupper($sk_code)) ?></a></li>
                    <?php endforeach; ?>
                    <li class="sk-header-hook"><?= hook('header.actions') ?></li>
                </ul>
            </div>
        </div>
    <?php endif; ?>
    <div class="af-container sk-header-main">
        <?php if ($sk_main !== []) : ?>
            <button type="button" class="af-icon-btn af-show-sm" data-af-drawer-open="af-menu" aria-controls="af-menu" aria-expanded="false" aria-label="<?= e(t('Open the menu')) ?>">
                <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
            </button>
        <?php endif; ?>
        <a class="af-logo" href="<?= e(url('/')) ?>"><?= shop_logo() ?></a>
        <?php if (base_theme_can('search')) : ?>
            <form class="af-search sk-search af-hide-sm" role="search" action="<?= e(base_theme_link('search')) ?>" method="get"<?= hook('webmcp.form', 'search_products') ?>>
                <label class="af-sr" for="sk-q-header"><?= e(t('Search')) ?></label>
                <input id="sk-q-header" class="af-input" type="search" name="q" placeholder="<?= e(t('Search…')) ?>" autocomplete="off"<?= hook('webmcp.param', 'search_products', 'q') ?>>
                <button type="submit" class="af-btn af-btn-primary"><?= e(t('Search')) ?></button>
            </form>
        <?php endif; ?>
        <?php if (base_theme_can('cart')) : ?>
            <a class="af-icon-btn af-hide-sm sk-cart" href="<?= e(base_theme_link('cart')) ?>" data-af-drawer-open="af-cart" aria-controls="af-cart" aria-label="<?= e(t('Cart')) ?>">
                <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" focusable="false"><path d="M6 7h12l1 13H5L6 7Z"/><path d="M9 10V6a3 3 0 0 1 6 0v4"/></svg>
                <span class="af-cart-count" data-af-cart-count hidden></span>
            </a>
        <?php endif; ?>
    </div>
    <?php if ($sk_main !== []) : ?>
        <nav class="af-nav sk-header-nav af-hide-sm" aria-label="<?= e(t('Main menu')) ?>">
            <div class="af-container">
                <?= $this->partial('partials/nav', ['items' => $sk_main]) ?>
            </div>
        </nav>
    <?php endif; ?>
</header>
