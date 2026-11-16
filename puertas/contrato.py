"""AIFEC — fábrica de temas: puerta «contrato» (las pruebas de temas que trae el propio sistema).

`theme:check` mira el tema por dentro. Las pruebas de `tests/Themes/` del sistema miran, además, lo que AIFEC exige
a todos los temas a la vez y que solo se ve leyendo sus plantillas y sus hojas: ninguna imagen escrita sin `width`
y `height`, el texto de entradas, páginas y fichas a todo el ancho de su contenedor, y una hoja que quepa dentro
de la página. Un tema que pasa `theme:check` y no pasa estas pruebas rompe la batería del sistema el día que se
instala. Esta puerta instala el candidato en el banco y lanza esas pruebas tal cual, con el lanzador del sistema
(`tests/run.php`): aquí no se repite ninguna comprobación, solo se lee el veredicto.

Se lanzan las tres de `PRUEBAS`; las que el sistema no traiga se saltan, y si no trae ninguna, o no trae el
lanzador, la puerta sale con 2 y lo dice.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

PRUEBAS = ("tests/Themes/AriaTest.php", "tests/Themes/ReadingColumnTest.php", "tests/Themes/InlineCssTest.php")
LANZADOR = "tests/run.php"
FINAL = re.compile(r"^PRUEBAS:\s*(\d+)\s*OK,\s*(\d+)\s*FALLAN\s*\((\d+)\s*comprobaciones", re.M)


def fallos(texto: str) -> list:
    """Cada «FALLA …» del lanzador con las líneas sangradas que la explican: [(título, [líneas])]."""
    bloques = []
    for linea in texto.splitlines():
        if linea.startswith("FALLA "):
            bloques.append((linea[6:].strip(), []))
        elif bloques and linea.startswith("  ") and linea.strip():
            bloques[-1][1].append(linea.strip())
    return bloques


def nombra(bloque: tuple, slug: str) -> bool:
    """¿El fallo habla de este tema? Las pruebas lo nombran por su carpeta (`themes/<slug>/`) o como «<slug>: …»."""
    entero = bloque[0] + "\n" + "\n".join(bloque[1])
    if ("themes/%s/" % slug) in entero:
        return True
    return re.search(r"(?<![\w/-])%s[:] " % re.escape(slug), entero) is not None


def puerta(ctx) -> int:
    _comun.exigir_banco(ctx)
    if not (ctx.candidato / "theme.json").is_file():
        raise _comun.NoPasa("el candidato no trae theme.json")
    presentes = [p for p in PRUEBAS if (ctx.banco / p).is_file()]
    if not (ctx.banco / LANZADOR).is_file() or not presentes:
        raise _comun.NoAplica("este AIFEC no trae las pruebas de temas (%s y tests/Themes/): no se imita su comprobación por otro lado" % LANZADOR)
    _comun.instalar_candidato(ctx)
    registro = ctx.sesiones / ("%s.contrato.pruebas.log" % ctx.slug)
    if registro.exists():
        registro.unlink()
    codigo = _comun.procesos.lanzar([_comun.php_principal(ctx), LANZADOR] + presentes, ctx.banco, registro, 5)
    if codigo == _comun.procesos.TIEMPO_AGOTADO:
        raise _comun.NoPasa("las pruebas de temas del sistema se pasaron del tiempo y se cortaron")
    texto = _comun.leer_texto(registro)
    final = FINAL.search(texto)
    bloques = fallos(texto)
    medidas = {"codigo": codigo if isinstance(codigo, int) else -1, "ficheros": len(presentes), "fallan": len(bloques), "del_tema": 0}
    if final:
        medidas.update({"pruebas_ok": int(final.group(1)), "fallan": max(int(final.group(2)), len(bloques)), "comprobaciones": int(final.group(3))})
    if codigo == 0 and final and int(final.group(2)) == 0 and not bloques:
        return ctx.terminar(_comun.PASA, "las %s pruebas de temas del sistema pasan con este tema dentro (%s comprobaciones, %d ficheros)" % (
            final.group(1), final.group(3), len(presentes)), [], medidas)
    if not bloques:
        ultimas = [l.strip()[:200] for l in texto.strip().splitlines()[-4:]]
        return ctx.terminar(_comun.NO_PASA, "las pruebas de temas del sistema salieron con código %s sin decir qué falla" % codigo, ultimas, medidas)
    detalles = []
    for titulo, lineas in bloques[:12]:
        detalles.append("falla: " + titulo[:200])
        detalles += ["   " + l[:260] for l in lineas[:6]]
    mios = [b for b in bloques if nombra(b, ctx.slug)]
    medidas["del_tema"] = len(mios)
    if mios:
        primero = mios[0]
        motivo = (primero[1] or [""])[0]
        return ctx.terminar(_comun.NO_PASA, "%d prueba(s) de temas del sistema no pasan con este tema, la primera: %s — %s" % (
            len(mios), primero[0][:120], motivo[:160]), detalles, medidas)
    primero = bloques[0]
    return ctx.terminar(_comun.NO_PASA, "%d prueba(s) de temas del sistema no pasan y ninguna nombra este tema (la primera: %s): otro tema del banco "
                        "las tiene rotas y tapa el resultado de este; rehaz el banco (`python fabrica.py banco --rehacer`) y vuelve a pasar las puertas" % (
                            len(bloques), primero[0][:120]), detalles, medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("contrato", puerta))
