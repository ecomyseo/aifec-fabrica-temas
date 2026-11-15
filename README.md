# Fábrica de temas de AIFEC

Toma encargos de una cola y los lleva, uno a uno y sin perder el hilo aunque se apague el equipo, hasta «hecho» o «atascado». Cada encargo es un tema de AIFEC: la fábrica prepara el esqueleto, entrega el trabajo a un **motor** (una IA de programación o una persona) y no da nada por hecho hasta que pasa todas las **puertas**.

Es un proyecto independiente del sistema: **no lleva AIFEC dentro**. Lo localiza por `plan.json` y **solo lo lee**; para validar trabaja sobre un banco de pruebas, una copia de trabajo en `estado/banco/`.

## Requisitos

- Python 3.10 o posterior. Solo biblioteca estándar: nada que instalar.
- Windows, Linux o macOS.
- Una instalación de AIFEC cercana (la que se pone en `plan.json`) y PHP para el banco.
- Opcional: Playwright, solo para la puerta `capturas`. Sin él, esa puerta sale como «no aplica» y lo dice.

## Primeros pasos

```
copy plan.ejemplo.json plan.json        (o cp en Linux y macOS) y edita "aifec" con la ruta de tu instalación
copy cola.ejemplo.json cola.json        los encargos de ejemplo, o los tuyos
python fabrica.py estado                comprueba que el plan vale y mira el día, el cupo y lo que toca
python fabrica.py trabajar --uno        el primer encargo, con el motor manual: deja el encargo escrito
python fabrica.py puertas <slug>        cuando el trabajo esté en salida/<slug>/, pásale las puertas
```

Con el motor `manual` (el de por defecto) la fábrica escribe el encargo completo en `estado/encargos/<slug>.encargo.md` y espera. Para que trabaje sola, se configura un motor `orden` (ver `docs/motores.md`).

## Cómo se conecta al sistema

Solo con `plan.json` → `"aifec": "<ruta de una instalación>"`. La fábrica lee esa instalación, hace una copia en `estado/banco/` (sin `sites`, `storage`, cachés ni `.git`, ni `data-path.php`), crea ahí un sitio propio con las órdenes de AIFEC (`site:create`, con SQLite) e instala el candidato en `themes/` del banco para pasarle las puertas. En la instalación de origen no escribe jamás. Si AIFEC no trae alguna orden que una puerta necesita, esa puerta sale con 2 («no aplica») y lo dice; no se imita la comprobación por otro lado.

## Las órdenes

```
python fabrica.py estado                  día, cupo, hechos hoy, en curso, atascados, siguiente, gasto
python fabrica.py calendario              qué haría cada día hasta vaciar la cola
python fabrica.py trabajar [--uno] [--slug X]     lo de hoy (o un solo encargo)
python fabrica.py parar | reanudar        acaba el encargo en curso y no empieza otro | vuelve a trabajar
python fabrica.py anadir --slug X --nombre "…" …   añade un encargo a la cola
python fabrica.py encargo <slug>          escribe y enseña el encargo completo (lo que se le da al motor)
python fabrica.py puertas <slug> [--solo validador,peso]   pasa las puertas a lo que hay en salida/<slug>/
python fabrica.py aprobar <slug> | rechazar <slug> --motivo "…"   el visto bueno (o no) de una persona
python fabrica.py instalar <slug> --en <instalación>   copia lo fabricado (solo si está hecho o aprobado)
python fabrica.py escaparate              rehace escaparate/index.html
python fabrica.py banco [--rehacer]       prepara o rehace el banco de pruebas
```

## Estados de un encargo

`pendiente` → `en_curso` → `en_puertas` → `hecho` → `aprobado`. Si las puertas (o una persona) lo rechazan pasa a `rechazado`, guarda el motivo y vuelve a la cola: el siguiente encargo que se le da al motor **incluye lo que falló**. Tras `intentos` intentos queda `atascado`.

`hecho` significa «pasa todas las puertas»; `aprobado`, «además lo ha mirado una persona». En `estado` y en el escaparate las dos cifras van separadas: no se llama terminado a lo que nadie ha mirado.

## Códigos de salida

| Código | Significado |
|---|---|
| 0 | bien |
| 1 | algo no pasa (una puerta, un atascado, una instalación que se niega) |
| 2 | uso incorrecto o plan inválido |
| 3 | parada por tope de gasto |
| 4 | parada por atascos seguidos |
| 5 | hay otra fábrica trabajando en esta carpeta |

## Qué hay dentro

- `fabrica.py` y `motor/`: el mecanismo, idéntico en la fábrica de temas y en la de plugins. Todo lo que distingue a una fábrica de otra está en `fabrica.json`.
- `puertas/`: las comprobaciones, propias de esta fábrica.
- `plantillas/`: el encargo que recibe el motor y la ficha de cada tema.
- `pruebas/`: `python -m unittest discover -s pruebas`.
- `docs/`: `como-funciona.md`, `plan.md` y `motores.md`.

Licencia: ver `LICENSE.md`.
