<?php
/**
 * AIFEC — pie de __Nombre__: la tienda y sus datos en una banda de presentación, los menús en una fila de
 * secciones y, aparte, la franja legal. Respeta el hueco de columnas de los módulos.
 *
 * @author    Ecom Experts <ecomyseo@gmail.com>
 * @copyright 2026 Ecom Experts
 * @license   Ver LICENSE.md
 */

$sk_settings = app()->settings();
$sk_shop = $sk_settings->str('store.name', 'AIFEC');
$sk_email = trim($sk_settings->str('store.email', ''));
$sk_phone = trim($sk_settings->str('store.phone', ''));
$sk_address = trim($sk_settings->str('store.address', ''));
$sk_footer = menu('footer');
$sk_legal = menu('legal');
$sk_year = gmdate('Y', app()->clock()->now());
?>
<footer class="af-footer sk-footer">
    <section class="sk-footer-intro">
        <div class="af-container">
            <h2 class="sk-footer-name"><?= e($sk_shop) ?></h2>
            <address class="sk-footer-contact">
                <?php if ($sk_address !== '') : ?>
                    <span><?= nl2br(e($sk_address), false) ?></span>
                <?php endif; ?>
                <?php if ($sk_email !== '') : ?>
                    <a href="mailto:<?= e($sk_email) ?>"><?= e($sk_email) ?></a>
                <?php endif; ?>
                <?php if ($sk_phone !== '') : ?>
                    <a href="tel:<?= e(preg_replace('/[^0-9+]/', '', $sk_phone)) ?>"><?= e($sk_phone) ?></a>
                <?php endif; ?>
            </address>
        </div>
    </section>
    <div class="sk-footer-sections">
        <div class="af-container">
            <?php if ($sk_footer !== []) : ?>
                <nav aria-label="<?= e(t('Footer')) ?>">
                    <h3 class="sk-footer-heading"><?= e(t('Information')) ?></h3>
                    <?= $this->partial('partials/nav', ['items' => $sk_footer]) ?>
                </nav>
            <?php endif; ?>
            <?= hook('footer.columns') ?>
        </div>
    </div>
    <div class="sk-footer-legal">
        <div class="af-container">
            <small>&copy; <?= e($sk_year) ?> <?= e($sk_shop) ?></small>
            <?php if ($sk_legal !== []) : ?>
                <nav aria-label="<?= e(t('Legal links')) ?>">
                    <?= $this->partial('partials/nav', ['items' => $sk_legal]) ?>
                </nav>
            <?php endif; ?>
        </div>
    </div>
</footer>
