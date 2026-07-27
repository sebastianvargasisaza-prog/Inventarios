# Expediente de autorización de uso · EOS

**Sistema:** EOS · Sistema de gestión de producción, inventarios y calidad
**Empresa:** ÁNIMUS Lab · Espagiria Laboratorio SAS
**Destinatario:** Dirección Técnica
**Propósito:** aportar la información necesaria para decidir la autorización de uso.

> **Documento GENERADO desde el código fuente del sistema.** Los roles salen de la
> configuración real, los permisos por ruta del enrutador real de la aplicación, y los
> controles de integridad de los disparadores reales de la base de datos. Se regenera con
> `python scripts/generar_expediente_autorizacion.py`. Un documento de accesos escrito a
> mano queda desactualizado el día que alguien cambia un permiso, y uno que no coincide con
> el sistema es peor que no tenerlo.

---

## 1 · Alcance y estado de validación · LEER PRIMERO

EOS **no cuenta con validación formal de sistema computarizado** (GAMP 5 / PIC-S Anexo 11)
realizada por un tercero independiente. Eso está pendiente y es una tarea aparte.

Lo que este documento sí acredita es que **los controles de integridad de datos exigidos por
21 CFR Part 11 están implementados y son verificables en el código**: rastro de auditoría
inmutable, firma electrónica con identidad, control de accesos por rol y bloqueo de edición
sobre registros liberados. Cada afirmación de la sección 3 dice **dónde** se hace cumplir,
para que pueda comprobarse y no haya que creer en la palabra de nadie.

La decisión de autorizar un uso progresivo con estos controles, mientras se gestiona la
validación formal, es de la Dirección Técnica. Este documento existe para que esa decisión
se tome con la información completa, incluido lo que falta.

---

## 2 · Matriz de accesos y aprobaciones

### 2.1 · Qué habilita cada módulo, y a quién

| Módulo | Qué permite | Personas autorizadas |
|---|---|---|
| **Fórmulas maestras (receta)** | Ver la composición y los porcentajes de cada producto | alejandro (Dirección / Socio), hernando (Director Técnico), laura (Jefe de Control de Calidad), miguel (Aseguramiento de Calidad), sebastian (Dirección General), yuliel (Analista de Control de Calidad) |
| **Batch record electrónico (legajo de lote)** | Ejecutar los pasos del lote: despeje, pesaje, envasado, controles | alejandro (Dirección / Socio), camilo (Operario de Producción), jose (Jefe de Producción), laura (Jefe de Control de Calidad), luis (Operario (retirado · acceso desactivado)), mayerlin (Operaria de Dispensación), milton (Operario de Envasado), sebastian (Dirección General), sergio (Operario de Producción), smurillo (Operario de Producción), yuliel (Analista de Control de Calidad) |
| **Control de Calidad** | Liberar o rechazar lotes, registrar CoA e IPC | alejandro (Dirección / Socio), laura (Jefe de Control de Calidad), sebastian (Dirección General), yuliel (Analista de Control de Calidad) |
| **Aseguramiento de Calidad** | Desviaciones, CAPA, control de cambios, calificación de equipos | alejandro (Dirección / Socio), miguel (Aseguramiento de Calidad), sebastian (Dirección General) |
| **Dirección Técnica** | Aprobar procedimientos maestros (MBR) y dar visto bueno | alejandro (Dirección / Socio), hernando (Director Técnico), miguel (Aseguramiento de Calidad), sebastian (Dirección General) |
| **Planta / Producción** | Programar, iniciar y cerrar producciones | camilo (Operario de Producción), jose (Jefe de Producción), luis (Operario (retirado · acceso desactivado)), mayerlin (Operaria de Dispensación), milton (Operario de Envasado), sergio (Operario de Producción), smurillo (Operario de Producción) |
| **Compras y proveedores** | Solicitudes, órdenes de compra, recepción | alejandro (Dirección / Socio), catalina (Asistente de Compras), mayra (Contadora), sebastian (Dirección General) |
| **Autorización de órdenes de compra** | Autorizar y pagar OC (con límite · ver segregación de funciones) | catalina (Asistente de Compras), mayra (Contadora) |
| **Liberación de materia prima** | Pasar una MP de cuarentena a disponible | catalina (Asistente de Compras) |
| **Gestión humana** | Nómina y datos de personal | alejandro (Dirección / Socio), catalina (Asistente de Compras), daniela (Asistente), gloria (Gestión Humana), luz (Comercial / B2B), mayra (Contadora), sebastian (Dirección General) |
| **Marketing** | Campañas y contenido (sin acceso a datos regulados) | alejandro (Dirección / Socio), daniela (Asistente), felipe (Marketing), jefferson (Marketing), luz (Comercial / B2B), sebastian (Dirección General) |
| **Administración del sistema** | Configuración, correcciones auditadas, gestión de usuarios | alejandro (Dirección / Socio), sebastian (Dirección General) |

### 2.2 · Qué firma cada quién

La firma electrónica es nominal: queda registrada la persona, su cargo y su cédula al
momento de firmar, junto con el significado de la firma. No es un "aprobado" anónimo.

| Acto | Quién lo firma | Registro donde queda |
|---|---|---|
| Aprobación del procedimiento maestro (MBR) | Dirección Técnica | `e_signatures` + `audit_log` |
| Liberación de materia prima | Control de Calidad | `e_signatures` + kardex |
| Liberación de lote de producto terminado | Control de Calidad | `e_signatures` + `ebr_ejecuciones` |
| Rechazo de lote | Control de Calidad | `e_signatures` + degradación del PT |
| Verificación del despeje de línea | Operario registra · Calidad corrige | `ebr_despeje_items` |
| Autorización de orden de compra | Compras (con límite) | `audit_log` |

### 2.3 · Segregación de funciones

| Control | Cómo está resuelto |
|---|---|
| Quien produce no libera | Producción ejecuta el lote; sólo Control de Calidad lo libera |
| Quien aprueba el procedimiento no lo ejecuta | La Dirección Técnica aprueba el MBR; Planta ejecuta el EBR |
| Límite de gasto | Las órdenes por encima del límite las autoriza Dirección |
| Corrección de un registro firmado | No se edita: se registra una enmienda con motivo, autor y fecha |

#### Conflictos de segregación detectados en la configuración actual

El sistema **detecta y declara** estos cruces; no están ocultos. Requieren una decisión
explícita de la Dirección Técnica antes de autorizar el uso.

| Persona | Cargo | Conflicto | Por qué importa | Cómo se resuelve |
|---|---|---|---|---|
| **catalina** | Asistente de Compras | Compra la materia prima **y** la libera de cuarentena | La Resolución 2214/2021 art. 10 asigna la disposición del lote a Calidad. Hoy quien gestiona la compra también decide si el material entra a producción. | Sacar a la persona de `MP_LIBERA_USERS` y dejar la liberación en Control de Calidad. Es reversible: es un conjunto en `config.py`. |
| **catalina** | Asistente de Compras | Autoriza la orden de compra **y** registra el pago | Concentra autorización y ejecución del desembolso. | Decisión de gerencia ya tomada, con el rastro de auditoría como control compensatorio: cada autorización y cada pago quedan registrados con autor y fecha. |
| **mayra** | Contadora | Autoriza la orden de compra **y** registra el pago | Concentra autorización y ejecución del desembolso. | Decisión de gerencia ya tomada, con el rastro de auditoría como control compensatorio: cada autorización y cada pago quedan registrados con autor y fecha. |

> ⚠ **luis** figura(n) todavía en conjuntos de rol de `config.py` pese a estar dado(s) de
> baja. El acceso está bloqueado a nivel de contraseña (no puede iniciar sesión), pero
> conviene retirarlo de los roles para que la matriz no muestre permisos de una persona
> que ya no está.

---

## 3 · Integridad de datos y cumplimiento

Cada control indica dónde se hace cumplir, para que sea comprobable.

| Requisito | Cómo lo cumple EOS | Dónde se verifica |
|---|---|---|
| **Rastro de auditoría** (§11.10 e) | Toda operación sobre inventario, lotes, órdenes y registros de calidad deja usuario, acción, fecha y valores antes/después | `audit_log` · **524** puntos de registro en el código |
| **Rastro inalterable** | El propio rastro **no se puede editar ni borrar**, ni siquiera por un administrador: lo impide la base de datos | Disparadores `trg_audit_log_no_delete`, `trg_audit_log_no_update`, `trg_op_fija_audit` |
| **Firma electrónica** (§11.50) | Firma nominal con nombre, cargo y cédula capturados al firmar, más el significado del acto | `e_signatures` · **34** referencias en el código |
| **Registros liberados inmutables** | Un lote liberado o rechazado no admite cambios en sus pasos, pesajes ni controles | **21** disparadores de inmutabilidad |
| **Control de accesos** (§11.10 d) | Cada función exige un rol; no alcanza con tener sesión iniciada | Sección 2 · verificado sobre el enrutador real |
| **Datos exactos y completos** (ALCOA+) | El inventario se calcula sumando los movimientos del kardex, nunca un total guardado que pueda desviarse | `movimientos` / `movimientos_mee` |
| **Trazabilidad del lote** | De producto terminado a materia prima y viceversa, con sus documentos | Expediente por lote · `documentos_regulados` |
| **Control de cambios del sistema** | Cada cambio de esquema queda numerado y registrado | **375** migraciones registradas |
| **Verificación continua** | Batería automática que se ejecuta antes de cada publicación | **405** archivos de prueba |

### 3.1 · Control de accesos medido sobre el sistema real

Medido recorriendo el enrutador real de la aplicación, no una lista escrita a mano.

| Nivel de acceso | Quién entra | Funciones |
|---|---|---:|
| `AUTENTICADO` | cualquier usuario con sesión | 1007 |
| `ADMIN` | solo Sebastián y Alejandro | 487 |
| `COMPRAS` | Catalina, Mayra + Admin | 38 |
| `PLANTA` | operarios de planta + Admin | 33 |
| `EJECUTOR DE LOTE` | Planta ∪ Calidad ∪ Admin | 27 |
| `FINANZAS` | contadora / compras + Admin | 22 |
| `PÚBLICA` | sin sesión (a propósito) | 18 |
| `CALIDAD+ADMIN` | Control de Calidad o Dirección | 13 |
| `CALIDAD` | Laura, Yulieth + Admin | 7 |
| `ASEGURAMIENTO` | Miguel + Calidad + Admin | 6 |
| `FÓRMULAS (INVIMA)` | Técnica ∪ Calidad ∪ Aseguramiento ∪ Dirección | 6 |
| `CALIDAD (QC)` | Control de Calidad + backup DT/Aseguramiento + Admin | 5 |
| `AUTORIZA OC` | Compras con límite · contadora bloqueada (SoD) | 4 |
| `PORTAL B2B` | — | 3 |
| `RRHH` | Gloria + asistentes + Admin | 1 |
| `TÉCNICA` | Hernando, Miguel + Admin | 1 |

> **Ninguna función queda sin control de acceso.**

---

## 4 · Manual de uso por rol

El sistema se usa distinto según el puesto. Cada rol ve sólo lo que necesita.

### 4.1 · Operario de producción

1. **Abrir la orden del día** en Planta › Producción. Cada orden muestra el producto, el lote,
   cuánto avanzó y hace cuántos días está abierta.
2. **Despeje de línea.** Antes de tocar nada se recorren las 12 verificaciones, en el orden en que
   están: primero que no quede nada del producto anterior, después limpieza, después los rótulos y
   formatos, y al final las condiciones, los equipos y el elemento de protección personal. Cada una
   se marca Sí o No; un No abre el aviso correspondiente.
3. **Pesaje.** El sistema muestra la cantidad teórica de cada materia prima calculada sobre el
   tamaño real del lote. Se registra lo pesado; la diferencia queda a la vista.
4. **Ejecutar los pasos** del procedimiento en orden. Cada paso se inicia y se cierra; queda
   registrado quién lo hizo y cuándo.
5. **Envasado.** Se registran las unidades realmente obtenidas de cada presentación. Si una
   presentación no salió, se marca como no envasada indicando el motivo: dejarla en cero no sirve,
   porque no distingue "todavía no conté" de "no salió ninguna".
6. **Cerrar.** Al cerrar el envasado el sistema descuenta del inventario el frasco y todas sus
   piezas (tapa, caja, gotero) por las unidades registradas.

**Lo que un operario no puede hacer:** liberar un lote, aprobar un procedimiento, ver las fórmulas
maestras ni modificar un registro ya firmado.

### 4.2 · Control de Calidad

1. **Recepción de materia prima.** Todo lo que entra queda en cuarentena. Calidad revisa y libera
   o rechaza; hasta que no libere, esa materia prima no se puede usar en producción: el sistema la
   excluye del cálculo de disponible.
2. **Controles en proceso.** Se registran los valores medidos contra la especificación. Un
   resultado fuera de especificación abre una desviación automáticamente y bloquea la liberación.
3. **Liberación del lote.** Requiere firma electrónica. El sistema no deja liberar si hay una
   desviación abierta, un control fuera de especificación o un paso obligatorio sin ejecutar.
4. **Corrección de un registro.** Un resultado ya registrado sólo lo corrige Calidad o Dirección
   Técnica, y la corrección queda como enmienda: se conserva el valor anterior, el motivo y el
   autor.

### 4.3 · Dirección Técnica

1. **Aprobar el procedimiento maestro (MBR)** de cada producto. Una vez aprobado **no se puede
   modificar**: para cambiarlo se obsoleta la versión y se crea la siguiente. Los lotes en curso
   siguen con la versión con la que empezaron.
2. **Visto bueno** en los puntos del proceso que lo requieren.
3. **Consultar el expediente de cualquier lote**: materias primas y sus lotes, quién hizo cada
   paso, controles, desviaciones y documentos, en una sola pantalla.

### 4.4 · Compras

1. **Necesidades.** El sistema calcula qué falta cruzando el plan de producción con la fórmula de
   cada producto y el inventario disponible, descontando lo que ya está pedido.
2. **Solicitud y orden de compra.** Con autorización según el monto.
3. **Recepción.** Lo recibido entra en cuarentena a nombre de Calidad.

### 4.5 · Dirección

Acceso completo, incluidas las correcciones administrativas. **Toda corrección queda auditada**:
el administrador puede corregir un error, pero no puede hacerlo sin dejar rastro.

---

## 5 · Instructivo: reglas de operación que el sistema hace cumplir

Estas no son recomendaciones; el sistema las impide.

| Regla | Qué pasa si se intenta |
|---|---|
| No se produce con materia prima en cuarentena | El sistema la excluye del disponible y bloquea el inicio |
| No se produce con materia prima vencida | El descuento la rechaza aunque el estado no se haya actualizado |
| Un procedimiento aprobado no se modifica | La base de datos rechaza el cambio |
| Un lote liberado no se modifica | La base de datos rechaza el cambio |
| El rastro de auditoría no se borra | La base de datos rechaza el borrado y la edición |
| Un lote con desviación abierta no se libera | La liberación se bloquea con el motivo |
| No se descuenta dos veces el mismo material | Reclamo atómico: la segunda vez se rechaza |
| Una anulación no deja el inventario descuadrado | Se registra el movimiento inverso, nunca se borra el original |

**Qué hacer cuando el sistema bloquea algo.** El bloqueo indica la causa concreta. No hay forma de
saltarlo desde la pantalla, y es deliberado: si un control se pudiera omitir con un clic, no sería
un control. Cuando una situación legítima queda bloqueada, se resuelve corrigiendo la causa (por
ejemplo, liberando la materia prima que falta), no anulando la verificación.


---

## 6 · Constancia

Documento generado automáticamente desde el código fuente de EOS.
Regenerar con `python scripts/generar_expediente_autorizacion.py` después de cualquier
cambio de permisos, para que la matriz siga reflejando el sistema.

| | Nombre | Cargo | Fecha | Firma |
|---|---|---|---|---|
| Elabora | | | | |
| Revisa | | Aseguramiento de Calidad | | |
| **Autoriza el uso** | | **Dirección Técnica** | | |
