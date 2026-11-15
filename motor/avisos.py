"""AIFEC — motor de fábrica: los avisos.

Al terminar el día, al atascarse un encargo y al parar por gasto, la fábrica lanza la orden que diga
`aviso.orden` del plan, con `{mensaje}` sustituido. Vacía (lo normal) = no avisa a nadie.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""

from __future__ import annotations

from . import motores, procesos


def avisar(ctx, mensaje: str) -> bool:
    """Lanza la orden de aviso. Devuelve True si se lanzó y salió bien; un fallo del aviso no
    detiene nunca a la fábrica: solo se apunta."""
    orden = ctx.plan["aviso"]["orden"]
    if not orden:
        return False
    lanzada = motores.sustituir_marcas(orden, {"mensaje": mensaje})
    codigo = procesos.lanzar(lanzada, ctx.raiz, ctx.rutas.avisos, 1)
    ctx.apuntar("aviso: %s (código %s)" % (mensaje, codigo))
    return codigo == 0
