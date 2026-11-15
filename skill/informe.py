"""AIFEC — fábrica de temas: enseña el informe completo de las puertas de un tema.

    python skill/informe.py <slug> [--puerta estructura]

`python fabrica.py puertas <slug>` solo escribe una línea por puerta. El detalle (la tabla de parecidos de
estructura, las cadenas que faltan, el elemento de móvil que no cumple…) queda en
`estado/encargos/<slug>.puertas.json`; este guion lo lee y lo enseña. Solo lee: no pasa ninguna puerta.
Sale con 0 si ninguna puerta no pasa y con 1 si alguna no pasa; con 2 si todavía no hay informe.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass


def main() -> int:
    analizador = argparse.ArgumentParser(description="Informe completo de las puertas de un tema")
    analizador.add_argument("slug")
    analizador.add_argument("--puerta", default=None, help="solo esta puerta")
    args = analizador.parse_args()
    ruta = RAIZ / "estado" / "encargos" / ("%s.puertas.json" % args.slug)
    try:
        informe = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("No hay informe de puertas para «%s»: lanza antes `python fabrica.py puertas %s`." % (args.slug, args.slug))
        return 2
    mostradas = 0
    for puerta in informe.get("puertas", []):
        if args.puerta and puerta.get("nombre") != args.puerta:
            continue
        mostradas += 1
        print("[%s] %s: %s" % (puerta.get("estado"), puerta.get("nombre"), puerta.get("resumen")))
        for detalle in puerta.get("detalles") or []:
            print("    " + str(detalle))
    if args.puerta and not mostradas:
        print("El informe no trae la puerta «%s»." % args.puerta)
        return 2
    print(informe.get("linea", ""))
    return 0 if informe.get("pasa") else 1


if __name__ == "__main__":
    sys.exit(main())
