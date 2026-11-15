"""AIFEC — motor de fábrica.

Qué es: el mecanismo que toma encargos de una cola y los lleva, uno a uno y sin perder el
hilo aunque se apague el equipo, hasta «hecho» o «atascado». No sabe qué fabrica: todo lo que
distingue a una fábrica de otra lo lee de `fabrica.json`.

@author  Ecom Experts <ecomyseo@gmail.com>
@license Ver LICENSE.md
"""
