# MyBatch ↔ EOS · mapa de clonación para la certificación

> Relevado el **15-ago-2026** entrando a MyBatch de Espagiria
> (`esparigia-mybatch-...run.app`) con el usuario de Sebastián, perfil **Planeador**.
> Sebastián: *"necesitamos clonarlo perfecto ... ésta es la que regula INVIMA, y
> ellos ya están habilitados; la idea es reemplazarlos por EOS cuando pidamos la
> certificación"*.
>
> Este documento dice **qué tiene MyBatch, sección por sección**, y **qué tiene EOS
> hoy**, verificado contra el código y contra un recorrido E2E por los endpoints
> reales, no contra la memoria.

---

## 0 · Cómo se verificó (para que se pueda repetir)

| Qué | Cómo |
|---|---|
| Las pantallas de MyBatch | Se abrieron una por una y se leyó el texto completo de cada instructivo |
| Qué tiene EOS | `grep` del esquema + `url_map` real + los endpoints abiertos uno por uno |
| Que EOS lo recorre entero | `tests/test_ebr_e2e_demo.py` (fabricación) y `tests/test_ebr_e2e_envasado_acond.py` (envasado y acondicionamiento), los tres **en el gate** |

Las tres fases pasan hoy. Un rojo en cualquiera bloquea el push.

---

## 1 · El menú de MyBatch (perfil Planeador)

```
INICIO            tablero con 7 contadores
MANUFACTURA       /productionorder/list/        Órdenes de producción
                  /filling/list/                Envasado
                  /packing/list/                Acondicionamiento
                  /productionorder/list_premix/ Premezclas
                  /productionorder/program/     Programa de producción (calendario)
ASEGURAMIENTO     /assurance/batch_list_master/ Maestro de lotes
SOPORTE TÉCNICO   (sin opciones para este perfil)
```

**Contadores del inicio:** Fabricación pendientes / en proceso · Envasado pendientes /
lotes en proceso · Acondicionamiento pendientes / programados · Lotes en cuarentena.

**Estados oficiales** (leyenda del calendario, y es la máquina de estados que mira INVIMA):
`Pendiente · Programado · En Proceso · Aprobado · Cuarentena · Liberado · No Conforme/Rechazado/Cancelado`.

---

## 2 · FABRICACIÓN · "Instrucciones de Manufactura" (OP)

**Cabecera:** N° de orden · producto · N° de lote bulk · cantidad ordenada (Gr) ·
**área o línea** · fecha inicio · fecha final · estado actual.
**Acciones:** Timeline Batch Record · Orden · Descargar orden · Actualizar.

| # | Sección MyBatch | Contenido | EOS |
|---|---|---|---|
| 1 | Precauciones | texto + *agregar equipo* | ✅ `ebr_precauciones` |
| 2 | Despeje de línea · **Dispensación** | 13 verificaciones con Cumple | ✅ `ebr_despeje_linea` + `ebr_despeje_items` |
| 3 | Dispensado de materias primas | MP · **%** · **N° lote** · cant. a pesar · cant. pesada · **Ajustes** | ✅ `ebr_pesajes` (+ `ebr_ajustes_mp`) |
| 4 | Despeje de línea · **Fabricación** | las mismas 13, en el otro momento | ✅ EOS ya guarda las dos etapas por separado (`ebr_despeje_items.etapa`) · verificado con datos: el mismo ítem convive en dispensación y en fabricación con su firma propia |
| 5 | Fabricación/Mezcla | pasos con **Realizado por** + **Verificado por** + *Resultado* | ✅ `ebr_pasos_ejecutados` (doble firma) |
| 6 | Controles en proceso | Olor · Color · Densidad 25°C · pH 25°C · Apariencia | ✅ IPC estándar + specs del MBR |
| 7 | Observaciones generales | texto con autor y hora | ✅ `ebr_observaciones` |
| 8 | Registros físicos | adjuntos | ✅ `ebr_registros_fisicos` |

**Lo que EOS hace y MyBatch no:** descuenta la materia prima del kardex por FEFO al
iniciar, con lote y vencimiento reales; bloquea si el material está vencido o en
cuarentena; y calcula el rendimiento contra la fórmula.

---

## 3 · ENVASADO · "Orden de Envasado" (OF) + "Instrucciones de Envasado"

### 3.1 La orden

| Campo MyBatch | EOS |
|---|---|
| N° lote bulk · Tamaño bulk (Gr **y** mL) | ✅ |
| **Densidad bulk (g/mL)** | ✅ existe (mig 212, "puente OP→OF") |
| **Cantidad por envasar** = saldo del granel | ✅ y con más: remanente declarado, tolerancia y si la cuenta cuadra (15-ago) |
| Estado · elaborado por · supervisado por · observaciones | ✅ |
| **Lotes de producto por presentación**: presentación · lote · unidades · **área/línea** · cantidad (mL) · **unid. final** · **% rendimiento** · estado | ✅ presentaciones con unidades y cliente · rendimiento en VOLUMEN siempre, y unidades teóricas + % por presentación cuando hay UNA sola. Con varias no se parte el granel a ojo: se declara el total (MyBatch tiene la columna y la deja vacía) |
| **Materiales de envase**: requerida · devuelta · utilizada · **averiada** · **diferencia** | ✅ las seis (mig 433 · la diferencia se deriva, no se guarda) |

### 3.2 El instructivo

| # | Sección MyBatch | EOS |
|---|---|---|
| 1 | Precauciones | ✅ |
| 2 | Despejes de línea (12 verificaciones) | ✅ (mismo orden · mig 381) |
| 3 | **Recepción de material de envase**: material · N° lote · cant. requerida · cant. recibida · **recibido por** | ✅ `material-envase` + `/verificar` |
| 4 | Envasado · 5 pasos con realizado/verificado | ✅ |
| 5 | Controles en proceso · **control de volumen** ("Control de llenado 30mL → 30,0mL CUMPLE") | ✅ control de llenado y de peso propios de la fase (15-ago) |
| 6 | Observaciones generales | ✅ |
| 7 | Registros físicos | ✅ |

**Lo que EOS hace y MyBatch no:** el envase sale del kardex de verdad (con su cuarentena
y su serigrafiado), y las unidades se reparten **por cliente** — desde el 15-ago eso se
ve en la LISTA de órdenes (cliente, unidades y la foto del frasco que le corresponde),
no sólo abriendo el legajo.

---

## 4 · ACONDICIONAMIENTO · "Orden" (OA) + "Instructivo"

### 4.1 La orden

| Campo MyBatch | EOS |
|---|---|
| Elaborado por · estado · supervisado por · observaciones | ✅ |
| Lotes de producto por presentación · **unid. empacadas** · fecha · estado | ✅ |
| Acción **"Aprobar Etiqueta"** por presentación | ✅ gate de artes (`ebr_artes_codificacion`) |
| **Materiales de empaque**: requerida · recibida · devuelta · utilizada · **averiada** · diferencia | ✅ las seis (mig 433) |
| Aprobación de artes / codificación | ✅ |

### 4.2 El instructivo

**Cabecera:** unidades a procesar · lote bulk · fecha inicio/final · estado ·
**cant. procesada** · **averías** · **cant. disponible** · **rendimiento %** ·
**justificación del rendimiento** · registrado por (operario) · supervisado por
(jefe de producción) · **aprobado por (jefe de calidad)**.

| # | Sección MyBatch | EOS |
|---|---|---|
| 1 | Precauciones | ✅ |
| 2 | Despejes de línea (13, **con fecha por ítem**) | ✅ |
| 3 | **Recepción de material de empaque** (varias tandas: 367 + 75 + 100) | ✅ acepta varias filas |
| 4 | Acondicionamiento · 4 pasos con realizado/verificado | ✅ |
| 5 | **Controles de atributos** · 14 ítems de Calidad (integridad de la caja, adherencia de la etiqueta, sellado, legibilidad…) | ✅ los 14, y sólo en esta fase (15-ago) |
| 6 | Observaciones generales | ✅ |
| 7 | Registros físicos | ✅ |

**Ejemplo real leído:** rendimiento **127,25 %** (367 pedidas, 467 procesadas) con la
explicación en observaciones: *"se suman 100 unidades a la orden inicial por 367 de un
cliente que canceló"*. MyBatch pide justificación cuando el rendimiento se sale de
rango, y ahí queda el rastro.

---

## 5 · Lo que falta para el clon (lista corta y verificada)

> **Al cierre del 17-ago queda UNA cosa, y es una decisión, no una función:** si los
> checklists (despeje y controles de atributos) se quedan en código -versionados y
> revisados- o pasan a ser configurables por el director técnico como en MyBatch.
>
> **Cerrado el 17-ago:** **"Aprobar Etiqueta"** ahora se puede dar **desde el legajo
> de acondicionamiento**, que es donde MyBatch la tiene -- el endpoint existía desde junio
> y sólo se llegaba por el modal del dashboard.
>
> ⚠ **Y una corrección honesta:** ese día di el **maestro de lotes** por faltante y construí
> uno nuevo. Ya existía desde el 15-ago en `/calidad/maestro-lotes`, más completo. El mío se
> retiró. Lo busqué por una URL que inventé en vez de medir qué tiene EOS -- el mismo error
> que el párrafo de abajo ya describía.
>
> **Cómo se verificó esta vez (y por qué la primera medición mintió).** Se ejerció cada
> punto del mapa contra los endpoints reales, no se leyó. La primera pasada dio "FALTA" en
> 17 de 26 puntos **y era la sonda, no EOS**: leía `controles` donde el endpoint manda
> `items`, y un campo `etapa` donde el despeje manda dos listas (`dispensacion` /
> `fabricacion`). Con las llaves correctas, **24 de 26 puntos ya estaban**. Distinguir
> "está roto" de "no supe medirlo" es la mitad del trabajo (M170).


| # | Hueco | Dónde | Estado |
|---|---|---|---|
| 1 | `cant_averiada` + diferencia en la conciliación | envasado y acondicionamiento | ✅ **hecho** 15-ago (mig 433 · `tests/test_conciliacion_averiada.py`) |
| 3 | Los 14 controles de atributos | acondicionamiento | ✅ **hecho** 15-ago · y de paso envasado pasó a pedir control de llenado en vez de densidad y pH (`tests/test_ipc_estandar_por_fase.py`) |
| 2 | Las dos etapas del despeje (dispensación / fabricación) | fabricación | ✅ **ya existía** · lo verifiqué con datos, no por lectura: columna, endpoint y pantalla dicen "13 ítems × 2 etapas" |
| 4 | Justificación del rendimiento | fabricación (y cualquier fase) | ✅ **hecho** 15-ago (mig 434): queda en el legajo y en el PDF, no sólo en el audit · y el control salió del bloque `strict`, donde **no corría nunca** (`tests/test_yield_justificacion_queda.py`) · falta todavía el % **por presentación** |
| 5 | Saldo del granel ("cantidad por envasar") | envasado | ✅ **hecho** 15-ago · resultó que EOS **ya lo calculaba** (con remanente, tolerancia y si la cuenta CUADRA, que MyBatch no tiene) y sólo lo exponía en `/vista-completa`, que el legajo no llama: el número existía y no lo veía nadie. Ahora se pinta (`tests/test_conciliacion_granel_visible.py`) |
| 6 | Maestro de lotes (lote x presentacion · teoricas vs liberadas) | Aseguramiento | OK **ya existia** desde el 15-ago en `/calidad/maestro-lotes` -- y mas completo que el de MyBatch: trae las tres fases del lote con su rendimiento, los clientes, el material de envase y **declara de donde saca la teorica**. ⚠ El 17-ago construi un SEGUNDO maestro en `/aseguramiento/maestro-lotes` sin verlo: lo busque preguntandole a EOS por `/api/brd/maestro-lotes`, una URL que invente yo, vi el 404 y lo anote como hueco. Se retiro (la ruta redirige) y quedo un guard que impide que vuelva a haber dos (`tests/test_maestro_de_lotes.py`). **Es exactamente el error que este mismo documento ya advertia: antes de anotar un hueco, medirlo contra el codigo** |
| 7 | "Aprobar Etiqueta" desde la orden de acondicionamiento | acondicionamiento | OK **hecho** 17-ago · el endpoint existia desde junio para las tres fases, pero el unico camino era el modal del dashboard: en la pantalla del producto terminado la aprobacion era inalcanzable (M121). El guard fija ademas el CONTRATO: `firmar-rapido` firma siempre sobre `ebr_ejecuciones` y el aprobador valida contra `ebr_artes_codificacion`, asi que con la firma rapida el boton se ve bien y la aprobacion lo rechaza -- la peor forma de negar un permiso (M219) (`tests/test_aprobar_etiqueta_acondicionamiento.py`) |

> **Corrección honesta del propio mapa (15-ago).** De los cinco huecos que listé al
> relevar MyBatch, **tres ya existían en EOS** (el saldo del granel, el rendimiento y las
> dos etapas del despeje). Los marqué como faltantes por buscarlos con el nombre que usa
> MyBatch en vez de medir qué hace EOS. Lo que de verdad faltaba en esos tres no era la
> función: era que **el número calculado llegara a una pantalla**. Regla para el resto de
> la clonación: antes de anotar un hueco, medirlo contra el código.

Ninguno de los cinco rompe nada hoy: son **campos y datos que se agregan**, no cambios
en lo que ya está firmado (aditivo · M117).

---

## 6 · Lo que NO se copia (y por qué)

- **El calendario de MyBatch** es una grilla de estados. EOS tiene plan autónomo con
  ventas de Shopify, cadencias y buffer de 20 días: es superior y ya está en uso.
- **Las órdenes se numeran distinto** (MyBatch OP/OF/OA-año-N; EOS ya tiene su propia
  serie). No se toca: renumerar registros firmados es falsificar historia (M105).
- **MyBatch no toca inventario.** EOS descuenta materia prima y envases del kardex, con
  FEFO, cuarentena y vencimiento. Eso es lo que Sebastián llama "EOS es superior: jala
  todo", y no tiene equivalente que copiar.

---

## 8 · Aseguramiento: maestro, cuarentena y alta de granel

**Maestro de lotes** (`/assurance/batch_list_master/`) · 123 registros:
`N° de lote · producto · presentación · estado · unid. teóricas · unid. liberadas`.
La fila es por **(lote, presentación)**, no por lote: el mismo 262151 aparece dos
veces, una por cada tamaño.

**Lotes en cuarentena** (`/assurance/batch_quarantine_list/`) · mismas columnas
filtradas por estado. Ahí se ve algo que conviene copiar: **la liberación es
PARCIAL** (692 teóricas / 136 liberadas · 2666 / 2484). Un lote puede quedar
parcialmente liberado y el resto retenido.

**Alta de granel** (`/assurance/add_batch_bulk/`): descripción del granel (elegido
de los 30 productos, con código `PT-…`), presentación, N° de lote, N° de unidades,
observaciones.

**Acondicionamiento por TANDAS** — en la orden OA-2026-85 la misma presentación
aparece **cuatro veces** para el mismo lote (367, 75, 100 y 100 unidades), cada
una con su propio estado (`Programado` / `Aprobado ✓`) y su acción **Aprobar
Etiqueta**. Es decir: una orden agrupa varias tandas del mismo lote, y cada tanda
tiene su ciclo y su etiqueta aprobada por separado.

**Códigos de producto:** MyBatch identifica el producto terminado con un código
(`PT-TRIACTIVE-30-001`) y EOS lo hace por nombre. Para la certificación conviene
que el legajo de EOS **muestre también ese código**, porque es el que aparece en
los registros ya firmados de MyBatch.

---

## 7 · Vistas por rol (relevadas una por una · 15-ago-2026)

Sebastián abrió la sesión de cada persona y se recorrió su tablero. La conclusión de
diseño: **el tablero no es el mismo con permisos distintos; es una cola de trabajo
distinta por rol**, y el mismo objeto aparece en la etapa que a cada uno le toca actuar.

| | Planeador (Sebastián) | Jefe de producción (Jose Alfredo) | Jefe de calidad (Laura) | Operario (Maierlin) |
|---|---|---|---|---|
| Tarjetas | 7 | 8 | 8 | **3** |
| Menú extra | — | **Materiales** | **Materiales** + Productos | — |
| Pendientes de fabricación / envasado / acondicionamiento | sí | sí | parcial | **no** |
| Lo que está EN CURSO | sí | sí | sí | **sí (lo único)** |
| Cuarentena | sí | sí | sí | no |
| Colas propias | — | Controles de cambio **por revisar** (3) | Controles en proceso pendientes (6) · Artes por aprobar (1) · Controles de cambio **por aprobar** (9) | — |

Tres cosas que vale la pena copiar:

1. **El operario ve SÓLO lo ejecutable hoy** (en proceso / programado). No ve pendientes
   ni aprobaciones: nada que no pueda tocar.
2. **El mismo objeto, dos colas distintas**: el control de cambio le aparece al jefe de
   producción como *por revisar* y a Calidad como *por aprobar*. No es un permiso, es la
   etapa del flujo.
3. **Calidad no trabaja sobre el legajo, trabaja sobre la cola**: sus controles
   pendientes salen de todos los lotes abiertos en una sola lista.

**Director técnico / Administrador** (Hernando Acevedo, 15-ago): 9 tarjetas y **tres
secciones que nadie más tiene**:

- **Audit Trail** · siete pantallas, una por dominio (materiales, productos, manufactura,
  envasado, acondicionamiento, **observaciones**, documentos), con `Tipo · Cambios
  realizados · Elemento · Fecha · Realizado por`. Sólo la de observaciones tiene 506
  registros.
- **Usuarios** (`/user/list/`).
- **Configuración** · Áreas productivas · Equipos productivos · **Despejes de línea** ·
  Microbiología · **Control de atributos** · Formatos · Códigos QR.

Dos cosas que salen de ahí:

1. **En MyBatch los checklists son CONFIGURABLES por el director técnico** (los ítems del
   despeje de línea y los 14 controles de atributos son pantallas de configuración). En
   EOS son constantes del código. Las dos posturas son defendibles -en código quedan
   versionadas y revisadas; en pantalla el DT las cambia sin depender de un despliegue- y
   **es una decisión de Sebastián**, no un hueco que se tape solo.
2. **El audit trail de MyBatch muestra el JSON crudo de Django** en "Cambios realizados"
   (`{"model": "assurance.observationprocess", "pk": "ecaacab3-…", "fields": {…}}`).
   Es trazabilidad real, pero un auditor no la lee. EOS guarda antes/después en
   `audit_log` y puede presentarlo en lenguaje humano: acá conviene **no copiar**.

(Analista de calidad: se asume igual que jefe de control de calidad hasta ver una
diferencia. Y en los registros aparece un rol más, **Asistente de Gerencia**, corrigiendo
observaciones.)

---

### Quién firma qué (leído de los propios documentos)


| Acto | Quién lo firma en MyBatch |
|---|---|
| Programar la orden | Jefe de producción |
| Dispensar, ejecutar pasos, recibir material | Operario de producción |
| Verificar cada paso | Jefe de producción |
| Controles en proceso y de atributos | Jefe de calidad |
| Aprobar el acondicionamiento | Jefe de calidad |

EOS ya tiene esos roles y la doble firma. Las vistas de planeador, jefe de producción,
jefe de calidad y operario ya se contrastaron (tabla de arriba); falta el director
técnico.

---

## Cierre del relevamiento · 15-ago-2026

Los cinco perfiles de MyBatch (planeador, jefe de producción, jefe de calidad, operario y
director técnico) quedaron recorridos. Lo que faltaba se construyó, y en tres de los
cuatro puntos EOS no copió: mejoró.

### 1. Maestro de lotes · lo único funcional que faltaba

MyBatch lo tiene en Aseguramiento: por lote, cuántas unidades debían salir y cuántas se
liberaron, cruzado con la presentación. El dato en EOS estaba **entero** pero repartido en
tres tablas (`ebr_envasado_unidades`, el granel envasable del legajo, el kardex de PT) y
sólo se veía abriendo legajo por legajo: la pregunta que hace un auditor no tenía pantalla.

`/calidad/maestro-lotes` la arma con consultas agregadas, y agrega lo que MyBatch no tiene:

- **de dónde salió** el lote (el calendario, con sus kilos y su fecha),
- **para quién es** (los clientes B2B con sus unidades, su envase y la foto),
- **qué debía salir**: el granel envasable repartido por VOLUMEN de la mezcla real, no por
  unidades — una unidad de 30 mL se lleva el triple de granel que una de 10.
- **con qué se envasó**: el material de envase del lote — lo que se pidió, lo que Compras
  entregó, lo que la línea usó, lo que volvió a bodega y lo que se rompió — con la
  diferencia sin explicar derivada del helper canónico, nunca recalculada aparte. Lo que
  se pidió y no llegó se señala y enlaza a Compras: eso es lo que hay que reclamar.

Sin granel medido **no se estima**: se declara. Una teórica inventada se lee igual que una
medida, y sobre ésa se firma.

### 2. Checklists configurables · igual que MyBatch, con lo que el código daba gratis

El director técnico ya edita los ítems del despeje y los controles de cada fase desde
`/aseguramiento/checklists`. Lo que se conservó y MyBatch no muestra:

- cada cambio queda en `audit_log` **con el antes y el después completos**;
- **el texto de lo ya firmado no cambia nunca** — la vista muestra el texto que se guardó
  con cada registro, no el que hoy ocupe esa posición;
- un ítem retirado **sigue apareciendo** en los lotes donde se registró, marcado;
- una clave ya firmada **nunca se recicla**, así que reordenar la pantalla no le cambia el
  significado a ningún registro;
- la tabla **nace vacía**: sin configurar, todo funciona exactamente como antes.

### 3. Audit trail legible · acá no se copia

MyBatch imprime el JSON de Django. EOS ya guardaba antes/después, así que
`/aseguramiento/audit-trail` lo dice en palabras — *"laura liberó el legajo del lote ·
estado: completado → liberado"* — filtrable por área del proceso, con el registro crudo
debajo de cada renglón como prueba. Lo que no se puede traducir se declara en vez de
quedar a medias.

De paso apareció que el reporte crudo anterior devolvía `total = len(items)` con
`LIMIT 500`: con 3.000 cambios en el rango decía "total: 500", que es justo el número con
el que alguien decide si ya revisó todo.

### 4. Qué falta para reemplazar MyBatch de verdad

El clon puede estar completo y no reemplazar nada: **el registro de lote de EOS nace
oculto** (`brd_visible` default `'0'`) y **el modo de control nace apagado** (`ebr_mode`
`'off'`), a propósito, hasta terminar la validación Part 11. Un sistema construido y
apagado se ve, desde afuera, igual que uno que no existe.

`/aseguramiento/reemplazo-mybatch` lo mide contra la base real y dice dónde se cambia cada
cosa: quién ve el registro de lote, el modo, los cuatro controles que MyBatch aplica y EOS
trae apagados, cuántos productos tienen instructivo aprobado (con la lista de los que no),
si el DT ya revisó las verificaciones, y cuántos lotes recorrieron cada fase.

Declara explícitamente lo que **no** mide: la validación del sistema por un tercero
(GAMP 5), que INVIMA pide aparte y no se puede leer de la base.

### Y un hallazgo que no venía de MyBatch

Al enlazar la pantalla del director técnico apareció que **la matriz de permisos y las
puertas de los módulos no decían lo mismo**: el menú le ofrecía Aseguramiento al DT y a
Luz, el gate global los dejaba pasar, y la página los rechazaba con un set propio. El
barrido -entrar por la ruta de cada módulo con cada persona que la matriz autoriza-
encontró **seis casos**: `/calidad` rebotaba a Miguel, al director técnico, a Catalina y a
Luz; `/compras` y `/tecnica` a Luz.

Quedó alineado: **ver** un módulo sale de la matriz, **firmar** sigue con el guard propio
de cada acción, que es la separación que `config.py` ya declaraba.

---

## Cierre de pendientes · 15-ago-2026 (tarde)

Cuatro cosas que quedaban abiertas y ya no lo están:

**1. El aviso de contraseñas mentía.** Decía, con severidad alta y en cada arranque, que
José y Milton *"NO pueden entrar"*. Falso: el login resuelve primero por la tabla de
contraseñas y ellos la tienen. Ahora el chequeo mira la base antes de opinar y distingue
tres casos: sin clave por ningún lado (problema real), sólo en la base (funciona) y **no
se pudo verificar** (que es lo que responde cuando no puede consultar). Un aviso de
severidad alta que miente todos los días es lo que hace que se ignoren los demás.

**2. Los instructivos que faltan se resuelven desde donde se mide.** El punto de la
pantalla de estado ahora lleva a `/planta/activar-legajos`, que genera el instructivo
desde la fórmula y lo aprueba con una re-autenticación — la firma queda a nombre de quien
la da. Un enlace a una pantalla del tema, en vez de a la que resuelve, obliga a buscar.

**3. La etiqueta y la caja del cliente dejaron de ser una marca sin efecto.** Catalina
definía *si* el pedido las lleva, pero sin el **código** del material nadie puede
comprarlo, alistarlo ni descontarlo: la marca quedaba de adorno y el material se olvidaba
hasta que faltaba en el piso. Ahora el pedido guarda **cuál** etiqueta y **cuál** caja
(validadas contra el maestro de envases), el lote lo dice, y lo que falta definir se
**declara** en vez de adivinarse con un código parecido — que es como se termina
comprando el material de otro cliente.

**4. El enlace de facturación se sugiere.** Cuando el cruce es inequívoco (mismo NIT, o
nombre idéntico y único) el selector viene preseleccionado y dice de dónde sale la
sugerencia; con dos candidatas no propone ninguna. Confirmar cuesta un clic, pero sigue
siendo una decisión de una persona: enlazar mal deja a un cliente viendo las facturas de
otro.

**Y uno que se cerró sin escribir código:** el reparto manual cuando un pedido de cliente
se suma a un lote compartido **ya estaba resuelto** (el reparto sale por volumen y el
ajuste por lote existe desde el 12-ago). Se verificó y se sacó de la lista.
