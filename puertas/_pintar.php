<?php
/**
 * AIFEC — fábrica de temas: pinta las páginas de la tienda del banco con un tema puesto y guarda su HTML.
 *
 *   php _pintar.php --banco <estado/banco> --tema <slug> --paginas portada,listado,ficha,carrito --salida <carpeta>
 *                   [--muestra]
 *
 * Arranca la aplicación del sitio del banco, pone ese tema SOLO EN MEMORIA (no guarda nada en la base de datos),
 * pide cada página dentro del propio proceso y escribe `<salida>/<página>.html` y `<salida>/_resultado.json`.
 * El listado y la ficha se buscan siguiendo los enlaces de la portada (así vale cualquier demo). Si el banco no
 * tiene productos, el resultado lo dice (`necesita_muestra`) y `--muestra` pinta la página de muestra del tema
 * base (/tema/muestra, que solo existe con la depuración encendida) en su lugar.
 *
 * Sale con 0 si ha escrito el resultado y con 2 si faltan argumentos o el banco no está preparado.
 *
 * @author  Ecom Experts <ecomyseo@gmail.com>
 * @license Ver LICENSE.md
 */

if (PHP_SAPI !== 'cli') {
    exit(1);
}

$args = [];
$ultima = '';
foreach (array_slice($argv, 1) as $parte) {
    if (strpos($parte, '--') === 0) {
        $ultima = substr($parte, 2);
        $args[$ultima] = true;
    } elseif ($ultima !== '') {
        $args[$ultima] = $parte;
        $ultima = '';
    }
}
$banco = isset($args['banco']) && is_string($args['banco']) ? rtrim(str_replace('\\', '/', $args['banco']), '/') : '';
$tema = isset($args['tema']) && is_string($args['tema']) ? $args['tema'] : '';
$salida = isset($args['salida']) && is_string($args['salida']) ? rtrim(str_replace('\\', '/', $args['salida']), '/') : '';
$paginas = isset($args['paginas']) && is_string($args['paginas']) ? array_filter(explode(',', $args['paginas'])) : ['portada', 'listado', 'ficha', 'carrito'];
$muestra = !empty($args['muestra']);
// Siempre rutas absolutas: el sitio apunta en su caché a las rutas con las que se arrancó.
$banco = $banco !== '' && realpath($banco) !== false ? rtrim(str_replace('\\', '/', realpath($banco)), '/') : $banco;
if ($banco === '' || $tema === '' || $salida === '' || !is_file($banco . '/core/bootstrap.php')) {
    fwrite(STDERR, "uso: php _pintar.php --banco <banco> --tema <slug> --salida <carpeta> [--paginas a,b] [--muestra]\n");
    exit(2);
}
if (!is_dir($salida) && !mkdir($salida, 0777, true) && !is_dir($salida)) {
    fwrite(STDERR, "no puedo crear " . $salida . "\n");
    exit(2);
}

require $banco . '/core/bootstrap.php';

$datos = $banco . '/sites';
$sitios = \Aifec\Kernel\SiteResolver::all($datos);
$sitio = isset($sitios[0]) ? \Aifec\Kernel\SiteResolver::load($datos, $sitios[0]['id']) : null;
if ($sitio === null) {
    fwrite(STDERR, "el banco no tiene ningún sitio\n");
    exit(2);
}
// Una dirección de pega: la tienda del banco no es de nadie.
$sitio->host = 'banco.test';
if ($muestra) {
    $sitio->config['debug'] = true;
}
$app = new \Aifec\Kernel\App($sitio, $banco, ['public_dir' => $banco . '/public', 'log_files' => false]);
// El tema se pone en memoria ANTES de arrancar: el arranque decide ahí qué tema (y qué cadena de padres) está activo.
$app->settings()->override(['theme.active' => $tema, 'theme.options' => [], 'cache.pages' => false]);
$app->makeCurrent();

$resultado = ['tema' => $tema, 'paginas' => [], 'necesita_muestra' => false, 'muestra' => $muestra, 'errores' => []];

/**
 * Pide una dirección a la aplicación (siguiendo hasta tres redirecciones) y devuelve estado, cuerpo y dirección final.
 *
 * @return array{status:int,body:string,url:string}
 */
function fab_pedir(\Aifec\Kernel\App $app, string $ruta): array
{
    for ($salto = 0; $salto < 4; $salto++) {
        try {
            $peticion = \Aifec\Kernel\Request::create('GET', $ruta, [], [], ['sec-fetch-site' => 'same-origin', 'user-agent' => 'AifecFabrica/1.0']);
            $peticion->host = 'banco.test';
            $peticion->secure = true;
            $respuesta = $app->handle($peticion);
        } catch (\Throwable $e) {
            return ['status' => 500, 'body' => '', 'url' => $ruta, 'nota' => get_class($e) . ': ' . $e->getMessage()];
        }
        if ($respuesta->isRedirect() && isset($respuesta->headers['Location'])) {
            $ruta = (string) preg_replace('#^https?://[^/]+#', '', (string) $respuesta->headers['Location']);
            $ruta = $ruta === '' ? '/' : $ruta;
            continue;
        }

        return ['status' => (int) $respuesta->status, 'body' => (string) $respuesta->body, 'url' => $ruta, 'nota' => ''];
    }

    return ['status' => 508, 'body' => '', 'url' => $ruta, 'nota' => 'demasiadas redirecciones'];
}

/** Las direcciones de la tienda (mismo sitio) que enlaza un trozo de HTML, en orden y sin repetir. */
function fab_enlaces(string $html, string $contiene = ''): array
{
    $enlaces = [];
    $dentro = $html;
    if ($contiene !== '' && preg_match('/<[a-z0-9]+\b[^>]*class="[^"]*\b' . preg_quote($contiene, '/') . '\b[^"]*"[^>]*>/i', $html, $m, PREG_OFFSET_CAPTURE) === 1) {
        $dentro = substr($html, (int) $m[0][1]);
    }
    if (preg_match_all('/<a\b[^>]*\bhref="([^"#]+)"/i', $dentro, $encontrados) > 0) {
        foreach ($encontrados[1] as $href) {
            $href = html_entity_decode($href, ENT_QUOTES);
            $href = (string) preg_replace('#^https?://banco\.test#', '', $href);
            if ($href === '' || $href[0] !== '/' || strpos($href, '//') === 0 || isset($enlaces[$href])) {
                continue;
            }
            if (preg_match('#^/(admin|buscar|cuenta|mi-cuenta|carrito|pedido|tema|api|r/)#', $href) === 1) {
                continue;
            }
            $enlaces[$href] = true;
        }
    }

    return array_keys($enlaces);
}

/** ¿Trae el HTML un elemento con esa clase de contrato? */
function fab_tiene(string $html, string $clase): bool
{
    return preg_match('/\bclass="(?:[^"]*\s)?' . preg_quote($clase, '/') . '(?:\s[^"]*)?"/', $html) === 1;
}

/** Busca, entre los enlaces de una página, la primera que al abrirla enseña la clase dada. */
function fab_buscar(\Aifec\Kernel\App $app, array $enlaces, string $clase, int $maximo): ?array
{
    $mirados = 0;
    foreach ($enlaces as $enlace) {
        if ($mirados++ >= $maximo) {
            break;
        }
        $pagina = fab_pedir($app, $enlace);
        if ($pagina['status'] === 200 && fab_tiene($pagina['body'], $clase)) {
            return $pagina;
        }
    }

    return null;
}

$guardar = static function (string $nombre, array $pagina) use ($salida, &$resultado): void {
    file_put_contents($salida . '/' . $nombre . '.html', $pagina['body']);
    $resultado['paginas'][$nombre] = ['url' => $pagina['url'], 'status' => $pagina['status'], 'bytes' => strlen($pagina['body']), 'nota' => isset($pagina['nota']) ? $pagina['nota'] : ''];
};

if ($muestra) {
    $guardar('muestra', fab_pedir($app, '/tema/muestra'));
    $guardar('muestra-filtros', fab_pedir($app, '/tema/muestra?filtros=1'));
} else {
    $portada = fab_pedir($app, '/');
    $listado = null;
    $ficha = null;
    if (in_array('portada', $paginas, true)) {
        $guardar('portada', $portada);
    }
    if (array_intersect(['listado', 'ficha'], $paginas) !== [] && $portada['status'] === 200) {
        $listado = fab_buscar($app, fab_enlaces($portada['body']), 'af-listing', 12);
        $origen = $listado !== null ? $listado['body'] : $portada['body'];
        $ficha = fab_buscar($app, fab_enlaces($origen, 'af-product-card'), 'af-product', 8);
        if ($ficha === null && $listado !== null) {
            $ficha = fab_buscar($app, fab_enlaces($portada['body'], 'af-product-card'), 'af-product', 8);
        }
        if ($listado === null || $ficha === null) {
            $resultado['necesita_muestra'] = true;
            $resultado['errores'][] = 'el banco no tiene productos que pintar' . ($listado === null ? ' (sin listado)' : '') . ($ficha === null ? ' (sin ficha)' : '');
        }
    }
    if ($listado !== null && in_array('listado', $paginas, true)) {
        $guardar('listado', $listado);
    }
    if ($ficha !== null && in_array('ficha', $paginas, true)) {
        $guardar('ficha', $ficha);
    }
    if (in_array('carrito', $paginas, true)) {
        $carrito = $app->router()->has('cart') ? route('cart') : '/carrito';
        $guardar('carrito', fab_pedir($app, (string) preg_replace('#^https?://[^/]+#', '', $carrito)));
    }
}

file_put_contents($salida . '/_resultado.json', json_encode($resultado, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES | JSON_PRETTY_PRINT));
exit(0);
