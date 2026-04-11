# Reglas de Negocio y Lógica de Agenda

Este documento define los parámetros exactos, tiempos de ejecución y restricciones que rigen el algoritmo de decisión del Agente de IA ("El Cerebro") y del Gestor de Flujos. El sistema deberá programarse para cumplir estas reglas de forma estricta.

## 1. Definición de Capacidad Operativa ("La Cuota")

El sistema gestionará la agenda según un modelo de inventario de minutos, no de franjas horarias tradicionales.

| Parámetro | Valor |
|-----------|--------|
| Días operativos | Lunes a jueves (viernes, sábado y domingo bloqueados por defecto para cirugía, salvo indicación contraria). |
| Ventana quirúrgica | 09:00 a 13:00. |
| Capacidad diaria máxima | 240 minutos disponibles en total por día. |
| Lógica de ocupación | Cada cita restará minutos de esta capacidad total según la tabla de servicios (sección 2). |

## 2. Tabla Maestra de Servicios y Tiempos

El Agente de IA clasificará la petición del cliente y asignará una duración ("coste en tiempo") según la tabla siguiente. Estos son los valores que se restarán de la cuota de 240 minutos.

### A. Especie: GATO (sin límite de cantidad; solo límite de tiempo)

| Servicio | Tiempo (minutos) |
|----------|------------------|
| Esterilización gato macho | 12 |
| Esterilización gata hembra | 15 |

**Nota:** Puede aplicarse una alerta interna de "Gato callejero" cuando proceda; el tiempo asignado se mantiene estándar.

### B. Especie: PERRO (sujeto a restricción de cantidad)

El tiempo se determina por sexo y peso según lo indique el cliente.

| Categoría | Tiempo (minutos) |
|-----------|------------------|
| Perro macho (cualquier peso) | 30 |
| Perra (0–10 kg) | 45 |
| Perra (10–20 kg) | 50 |
| Perra (20–30 kg) | 60 |
| Perra (30–40 kg) | 60 |
| Perra (>40 kg) | 70 |

## 3. Algoritmo de Restricción y Bloqueo ("El Tetris")

Para confirmar una fecha, el sistema debe validar ambas condiciones lógicas siguientes de forma positiva. Si alguna falla, la fecha se considerará **NO DISPONIBLE**.

### Regla 1: Validación de tiempo (suma ≤ 240)

`(Minutos ya ocupados + Minutos de la nueva cita) ≤ 240`

### Regla 2: Límite de perros (máximo 2)

Si la nueva cita se clasifica como **Especie: PERRO**:

`(Número de perros del día + 1) ≤ 2`

**Explicación:** Si ya hay 2 perros programados en un día, el sistema bloqueará ese día para cualquier nueva solicitud de perro, aunque queden minutos libres.

**Excepción:** Esta regla no se aplica a los gatos. Un día con 2 perros puede seguir aceptando gatos hasta completar los 240 minutos.

## 4. Ventanas de Entrega por Especie (Obligatorias)

Las horas de entrega son específicas por especie y no negociables. El sistema solo ofrecerá y confirmará citas cuya entrega caiga dentro de las siguientes ventanas.

| Especie | Ventana de entrega | Días aplicables |
|---------|-------------------|-----------------|
| Gatos | 08:00–09:00 (estricto) | Lunes a viernes |
| Perros | 09:00–10:30 (estricto) | Reglas de validación (ver abajo) |

### Reglas de validación — Días operativos (lunes a jueves)

- **Gatos:** Un gato no puede ser entregado fuera de 08:00–09:00. El sistema no confirmará ninguna cita de gato que exija entrega fuera de esta ventana. En días operativos (lun–jue), los gatos usan la ventana 08:00–09:00; el viernes (si se abre para gatos), rige la misma ventana 08:00–09:00.
- **Perros:** Un perro no puede ser entregado fuera de 09:00–10:30. El sistema no confirmará ninguna cita de perro que exija entrega fuera de esta ventana.

### Resumen

- **Gatos:** entrega 08:00–09:00, lunes–viernes.
- **Perros:** entrega 09:00–10:30, lunes–jueves (días operativos).

## 5. Protocolo de Comunicación y Logística

El sistema gestionará las expectativas del cliente distinguiendo entre "Reserva" y "Entrega".

| Regla | Descripción |
|-------|-------------|
| Ocultar horarios quirúrgicos | El cliente nunca elegirá una hora concreta (p. ej. 10:30). Solo elegirá el **DÍA**. |
| Mensaje de entrega por especie | Al confirmar la cita, el sistema indicará automáticamente al cliente la ventana correcta: **Gatos:** "El gato debe ser entregado estrictamente entre las 08:00 y las 09:00 de la mañana." **Perros:** "El perro debe ser entregado estrictamente entre las 09:00 y las 10:30 de la mañana para su preparación." |
| Protocolo de ayuno | Las instrucciones de ayuno (desde medianoche de la noche anterior) se adjuntarán al mensaje final de confirmación. |
