<?php
/**
 * AIFEC — fábrica de temas: carga el paquete de demostración mínimo en el sitio del banco, para que haya productos
 * que pintar. Solo toca el banco (una copia de trabajo), nunca la instalación de origen.
 *
 *   php _sembrar.php --banco <estado/banco> [--paquete <nombre>]
 *
 * Deja `<banco>/sites/<sitio>/demo-cargada.txt` con el nombre del paquete: así se carga una sola vez por banco.
 * Sale con 0 si el paquete está cargado (ahora o antes), con 2 si falta algo (no hay paquete o el banco no está
 * preparado) y con 1 si la carga falla.
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
$paquete = isset($args['paquete']) && is_string($args['paquete']) ? $args['paquete'] : 'minimo';
// Siempre rutas absolutas: el sitio apunta en su caché a las rutas con las que se arrancó.
$banco = $banco !== '' && realpath($banco) !== false ? rtrim(str_replace('\\', '/', realpath($banco)), '/') : $banco;
if ($banco === '' || !is_file($banco . '/core/bootstrap.php')) {
    fwrite(STDERR, "uso: php _sembrar.php --banco <banco> [--paquete <nombre>]\n");
    exit(2);
}
if (!is_dir($banco . '/demos/' . $paquete)) {
    fwrite(STDERR, "el banco no trae el paquete de demostración «" . $paquete . "»\n");
    exit(2);
}

require $banco . '/core/bootstrap.php';

$datos = $banco . '/sites';
$sitios = \Aifec\Kernel\SiteResolver::all($datos);
if (!isset($sitios[0])) {
    fwrite(STDERR, "el banco no tiene ningún sitio\n");
    exit(2);
}
$id = $sitios[0]['id'];
$marca = $datos . '/' . $id . '/demo-cargada.txt';
if (is_file($marca)) {
    echo "ya estaba cargado\n";
    exit(0);
}

try {
    $constructor = new \Aifec\Modules\Sites\DemoBuilder($banco, $datos, $banco . '/public');
    $resultado = $constructor->build($id, $paquete);
} catch (\Throwable $e) {
    fwrite(STDERR, get_class($e) . ': ' . $e->getMessage() . "\n");
    exit(1);
}
file_put_contents($marca, $paquete . "\n");
echo 'cargado: ' . json_encode(isset($resultado['counts']) ? $resultado['counts'] : [], JSON_UNESCAPED_UNICODE) . "\n";
exit(0);
