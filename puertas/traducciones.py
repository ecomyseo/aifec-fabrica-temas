"""AIFEC — fábrica de temas: puerta «traducciones» (nada sin traducir).

Instala el candidato en el banco y lanza `php aifec i18n:check themes/<slug>`. Pasa si sale con 0, es decir,
si su última línea dice «… strings, 0 missing». Si no, enseña las cadenas que faltan (el propio sistema las
da listas para pegar en `lang/es.php`). Si el sistema no trae la orden, sale con 2.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

RESUMEN = re.compile(r"I18N\s+\S+\s+\[[^\]]*\]:\s*(\d+)\s+strings,\s*(\d+)\s+missing(?:,\s*(\d+)\s+duplicated)?", re.I)


def puerta(ctx) -> int:
    _comun.exigir_banco(ctx)
    if not (ctx.candidato / "theme.json").is_file():
        raise _comun.NoPasa("el candidato no trae theme.json")
    _comun.instalar_candidato(ctx)
    codigo, texto = _comun.orden_aifec(ctx, ["i18n:check", "themes/" + ctx.slug, "es"], minutos=5, nombre="i18n-check")
    if codigo == _comun.procesos.TIEMPO_AGOTADO:
        raise _comun.NoPasa("i18n:check se pasó del tiempo y se cortó")
    if "Unknown command" in texto:
        raise _comun.NoAplica("este AIFEC no trae la orden i18n:check: no se imita su comprobación por otro lado")
    resumen = None
    for linea in texto.splitlines():
        encontrado = RESUMEN.search(linea)
        if encontrado:
            resumen = encontrado
    if resumen is None:
        ultimas = [l.strip() for l in texto.strip().splitlines()[-4:]]
        raise _comun.NoPasa("i18n:check no dio su línea final (código %s)" % codigo if not ultimas else
                            "i18n:check no dio su línea final (código %s): %s" % (codigo, " | ".join(ultimas)[:200]))
    cadenas, faltan = int(resumen.group(1)), int(resumen.group(2))
    medidas = {"cadenas": cadenas, "faltan": faltan, "codigo": codigo if isinstance(codigo, int) else -1}
    if codigo == 0 and faltan == 0:
        return ctx.terminar(_comun.PASA, "%d cadenas, 0 sin traducir" % cadenas, [], medidas)
    detalles = [l.strip() for l in texto.splitlines() if l.strip() and not RESUMEN.search(l)][:30]
    return ctx.terminar(_comun.NO_PASA, "%d cadena(s) sin traducir de %d" % (faltan, cadenas), detalles, medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("traducciones", puerta))
