"""AIFEC — fábrica de temas: puerta «validador» (el contrato de temas del sistema).

Instala el candidato en el banco y lanza `php aifec theme:check <slug>`, que es quien sabe lo que exige el
contrato de temas (theme.json y herencia, plantillas y piezas, envoltorio con `page_head()`, `<main id="main">`
y barra de móvil, peso, direcciones ajenas, galería antes que compra, traducciones y las comprobaciones en
vivo de la portada y de la página de error). Aquí no se repite ninguna de esas comprobaciones: solo se lee su
veredicto. Si el sistema no trae la orden, la puerta sale con 2 y lo dice.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _comun  # noqa: E402

PUNTUACION = re.compile(r"Score\s+(\d+)\D+?errors\s+(\d+)\D+?warnings\s+(\d+)", re.I)
LINEA = re.compile(r"^\[(OK|FAIL|WARN)\s*\]\s*(.*)$")


def puerta(ctx) -> int:
    _comun.exigir_banco(ctx)
    if not (ctx.candidato / "theme.json").is_file():
        raise _comun.NoPasa("el candidato no trae theme.json")
    _comun.instalar_candidato(ctx)
    codigo, texto = _comun.orden_aifec(ctx, ["theme:check", ctx.slug], minutos=5, nombre="theme-check")
    if codigo == _comun.procesos.TIEMPO_AGOTADO:
        raise _comun.NoPasa("theme:check se pasó del tiempo y se cortó")
    if "Unknown command" in texto:
        raise _comun.NoAplica("este AIFEC no trae la orden theme:check: no se imita su comprobación por otro lado")
    fallos = []
    avisos = []
    for linea in texto.splitlines():
        encontrada = LINEA.match(linea.strip())
        if not encontrada:
            continue
        if encontrada.group(1) == "FAIL":
            fallos.append(encontrada.group(2).strip())
        elif encontrada.group(1) == "WARN":
            avisos.append(encontrada.group(2).strip())
    puntuacion = PUNTUACION.search(texto)
    medidas = {"codigo": codigo if isinstance(codigo, int) else -1, "errores": len(fallos), "avisos": len(avisos)}
    if puntuacion:
        medidas.update({"puntuacion": int(puntuacion.group(1)), "errores": int(puntuacion.group(2)), "avisos": int(puntuacion.group(3))})
    if codigo == 0 and not fallos:
        resumen = "theme:check sin errores"
        if puntuacion:
            resumen += " (puntuación %s, %s avisos)" % (puntuacion.group(1), puntuacion.group(3))
        return ctx.terminar(_comun.PASA, resumen, ["aviso: " + a for a in avisos[:10]], medidas)
    if not fallos:
        ultimas = [l.strip() for l in texto.strip().splitlines()[-4:]]
        return ctx.terminar(_comun.NO_PASA, "theme:check salió con código %s sin explicarse" % codigo, ultimas, medidas)
    return ctx.terminar(_comun.NO_PASA, "theme:check: %d error(es), el primero: %s" % (len(fallos), fallos[0][:160]),
                        ["error: " + f for f in fallos[:25]] + ["aviso: " + a for a in avisos[:5]], medidas)


if __name__ == "__main__":
    sys.exit(_comun.ejecutar("validador", puerta))
