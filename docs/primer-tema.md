# Tu primer tema: de una frase a un tema instalado

El recorrido completo, a mano (motor `manual`), con un encargo de una frase. Lo mismo hace una IA con un motor `orden`: la diferencia es solo quién escribe `salida/<slug>/`.

## 0. Antes de empezar

```
cp plan.ejemplo.json plan.json      edita "aifec" (tu instalación), "php" (con pdo_sqlite) y "php_versiones"
python fabrica.py estado            comprueba que el plan vale
python fabrica.py banco             prepara el banco de pruebas (una copia de trabajo de AIFEC)
```

## 1. Un encargo de una frase

```
python fabrica.py anadir --slug floristeria-petalo --nombre "Floristería Pétalo" \
    --sector "floristería con reparto el mismo día" \
    --idea "la fecha de entrega se elige antes que el ramo"
```

Un encargo completo trae además `publico`, `referencias`, `paleta`, `tipografia`, `superficies` y `no_hacer` (mira `cola.ejemplo.json`); se pueden añadir con `--campo clave=valor` o editando `cola.json`. Cuanto más concreto sea `superficies`, menos hay que inventar.

## 2. Que la fábrica escriba lo que hay que hacer

```
python fabrica.py trabajar --uno
```

Con el motor `manual` deja el encargo en `estado/encargos/floristeria-petalo.encargo.md` (el texto completo: qué hacer, dónde, con qué skill, cómo comprobarlo) y el encargo en `en_curso`. También se ve con `python fabrica.py encargo floristeria-petalo`.

## 3. Descomponer antes de programar

Sigue `skill/SKILL.md`. La primera hoja que se rellena es `skill/plantillas/descomposicion.md`: las cinco superficies (cabecera, tarjeta, listado, ficha, pie), cómo será cada una y en qué se distingue de las de `base` y de los temas que ya existen (mira `estado/banco/themes/*/templates/`).

## 4. El esqueleto

```
python skill/esqueleto.py floristeria-petalo "Floristería Pétalo"
```

Crea `salida/floristeria-petalo/` con un tema hijo de `base`, las cinco superficies ya propias y un prefijo de clases propio (`fp-`). Ya pasa `theme:check`. Es un punto de partida: **cámbialo según tu descomposición**.

## 5. Las cinco superficies, una a una

Para cada una, escribe la plantilla y comprueba solo lo que has tocado:

```
python fabrica.py puertas floristeria-petalo --solo estructura,movil
python skill/informe.py floristeria-petalo
```

`informe.py` enseña la tabla de parecidos (ninguna cifra puede llegar a 0,82 con otro tema ni a 0,90 con `base`) y los accesos de móvil que no cumplen.

## 6. Opciones y traducción

`theme.json`: como mínimo tres opciones de estructura, cada color con su `var` usada en la hoja, la descripción en inglés. `lang/es.php`: cada cadena en castellano. La puerta de traducciones te dice cuáles faltan:

```
python fabrica.py puertas floristeria-petalo --solo traducciones
```

## 7. Pasar todas las puertas

```
python fabrica.py puertas floristeria-petalo
```

Acaba en `PUERTAS: n de n pasan` (con las que «no aplican» explicadas: sin Playwright, por ejemplo, `capturas`). Arregla la causa de cada `no_pasa` leyendo `python skill/informe.py floristeria-petalo` y repite.

## 8. Cuando pasan: mirarlo y aprobarlo

Pasar las puertas es **hecho**, no **aprobado**: lo aprueba una persona después de mirarlo.

```
python fabrica.py trabajar --slug floristeria-petalo     pasa las puertas y lo deja «hecho», con su ficha en escaparate/
python fabrica.py escaparate                             rehace escaparate/index.html
python fabrica.py aprobar floristeria-petalo             el visto bueno
python fabrica.py instalar floristeria-petalo --en <instalación>
```

`instalar` copia el tema a `themes/` de una instalación (solo si está hecho o aprobado) y **nunca pisa** uno que ya exista sin `--forzar`.

## Si te atascas

| Qué pasa | Qué mirar |
|---|---|
| `estructura` rechaza una superficie que has rediseñado | que cambie el **orden y el anidado**, no solo las clases: las clases propias no cuentan |
| `movil` dice que un acceso no funciona | que `data-af-drawer-open="id"` apunte a un `id` que exista en la página |
| `traducciones` enseña cadenas que ya traduce el catálogo | el catálogo del tema es aparte: pégalas en `lang/es.php` |
| `peso` rechaza la hoja | ≤ 45 000 bytes; no copies la hoja de `base` si no declaras `"css": "replace"` |
| Todo sale «no aplica» | `python fabrica.py banco`; revisa `php` y `aifec` en `plan.json` |

Más: `skill/referencias/fallos-frecuentes.md` y `docs/puertas.md`.
