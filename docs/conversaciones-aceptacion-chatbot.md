# Conversaciones de aceptación — Chatbot clínica veterinaria

Guiones de prueba ejecutables (texto usuario/asistente en **inglés**; encabezados de tabla en **español**) y su correspondencia con los tickets Doc **VET-n**. La definición de cada ticket está en el backlog del curso.

**MVP:** reducir fricción al agendar esterilización / castración. Identificación de usuario (login, CRM): opcional, fuera del núcleo del MVP.

**Orden de numeración:** las conversaciones 1 a 7 son las que suman la base de 5 puntos (en ese orden). Luego 8 y 9 (+tool disponibilidad) y 10 (guion típico para +RAG). Son las mismas diez situaciones de antes, solo reordenadas y renumeradas.

## System prompt y RAG (compatible; no hace falta elegir una sola vía)

- La misma información del caso puede vivir en el system prompt, en el corpus recuperado (p. ej. la página oficial indexada) o en ambos. No es obligatorio declarar de qué capa sale cada dato: lo que se exige es coherencia con la especificación del caso y ausencia de contradicciones entre fuentes.
- En particular, horarios (ventanas de entrega, recogida, etc., conversaciones 2 y 6) e instrucciones preoperatorias / ayuno (conversación 10) pueden atenderse con una fuente o la otra (prompt o RAG o ambos). La misma conversación sirve para comprobar que el asistente usa alguna fuente de información adecuada; no se penaliza el solapamiento.
- En particular, el **+1 pt de RAG (VET-11)** sigue exigiendo implementación y documentación del pipeline (ingesta desde la URL oficial, recuperación observable). Que parte del texto también esté en el prompt no sustituye ese requisito, pero sí es compatible: el punto se concede al demostrar que el retriever funciona, no al prohibir duplicar contenido en el prompt.

## Puntuación (10 pt) — resumen

- **Base (5 pt)** — Conversaciones 1 a 7 consecutivas, con memoria de sesión y conocimiento de dominio coherente (VET-9, VET-10; VET-14 + material en repo). Sin tool de disponibilidad. El conocimiento puede apoyarse en system prompt y/o RAG indistintamente (pueden solaparse).
- **Conversaciones 8 y 9** — Tool de disponibilidad (VET-12 / VET-13) → **+1 pt**.
- **+1 RAG (VET-11)** — Pipeline documentado y demostrable con contenido desde la URL oficial; la conversación 10 es el guion habitual (ayuno / preoperatorio), válida aunque esas mismas frases existan también en el prompt.
- **Vercel (VET-3)** y **tablero Jira (VET-4)** → **+1 pt** cada uno; sin conversación asociada.
- **Intents documentados (VET-5 / docs)** → **+1 pt**; alineados con las 10 conversaciones.

### Puntuación y conversaciones (tabla rápida)

| Tramo | Pt | Conversaciones (orden) | Tickets Doc VET (principal) |
| --- | --- | --- | --- |
| Base (memoria + dominio; sin tool; prompt y/o RAG compatibles) | 5 | 1 → 2 → 3 → 4 → 5 → 6 → 7 | VET-9, VET-10; VET-14 + repo |
| + Vercel | 1 | — | VET-3 |
| + Jira (tablero) | 1 | — | VET-4 |
| + RAG (URL oficial; demostrar retriever) | 1 | 10 (guion típico; puede solaparse con prompt) | VET-11 |
| + Tool disponibilidad | 1 | 8, 9 | VET-12 (mock); VET-13 (calendario real) |
| + Intents documentados | 1 | 1–10 | VET-5 / doc en repo |

**Infraestructura:** VET-7 (API), VET-8 (UI). VET-1, VET-2 para clonar/ejecutar. VET-4, VET-6 proceso SDD.

## Matriz conversación → tickets y EPIC

| # | Tema | EPIC | Doc VET principal | Doc VET apoyo |
| --- | --- | --- | --- | --- |
| 1 | Alcance y saludo | CHATBOT | VET-9 | VET-7, VET-8, VET-14 |
| 2 | Ventanas entrega + memoria | CHATBOT | VET-10, VET-9 | VET-7, VET-8, VET-14 |
| 3 | Analítica / edad | CHATBOT | VET-9 | VET-14 |
| 4 | Emergencia / fuera de alcance | CHATBOT | VET-9 | VET-14 |
| 5 | Reserva rechazada (celo) | CHATBOT | VET-9 | VET-14 |
| 6 | Horarios recogida + memoria | CHATBOT | VET-10, VET-9 | VET-14 |
| 7 | Derivación a humano | CHATBOT | VET-9 | VET-14 |
| 8 | Disponibilidad (tool) | CHATBOT | VET-12 | VET-9, VET-10, VET-7, VET-8, VET-14; VET-13 si calendario real |
| 9 | Capacidad / Tetris (tool) | CHATBOT | VET-12 | VET-9, VET-14; VET-13 opcional |
| 10 | Ayuno preoperatorio (guion +1 RAG; prompt y/o RAG) | CHATBOT | VET-11 | VET-9, VET-10 |

---

## Conversación 1 — Saludo, alcance y límite (texto del diálogo en inglés)

| Campo | Detalle |
| --- | --- |
| Intents | Salutation; OutOfScopeGeneralConsult (implícito) |
| Tickets principales | VET-9, VET-14 |
| Supera si | Saludo profesional; foco esterilización y logística; rechaza consulta general; no promete emergencias 24/7. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | Hi, what can you help me with? |
| 2 | Asistente | (Welcomes; explains support for booking sterilisation/castration, pre-op and drop-off/pick-up info; clarifies not for emergencies or routine illness consults.) |
| 3 | Usuario | My cat has a cough for three days—can you prescribe something? |
| 4 | Asistente | (Politely refuses clinical diagnosis/prescription; redirects to a veterinarian appointment or emergency if severe; stays within assistant scope.) |

---

## Conversación 2 — Ventanas de entrega (especie + memoria)

| Campo | Detalle |
| --- | --- |
| Intents | QueryDropOffWindow |
| Tickets principales | VET-10, VET-9 |
| Apoyo | VET-7, VET-8, VET-14 (gato 08:00–09:00, perro 09:00–10:30; elige día) |
| Fuentes (horarios) | Las ventanas pueden estar solo en el prompt, solo en documentos recuperados o en ambos; no hay que fijar una sola vía para aprobar el guion. |
| Supera si | Turno 2: ventana gato; turno 4: ventana perro sin volver a preguntar especie; transportín rígido si aplica. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | What time should I bring my cat on surgery day? |
| 2 | Asistente | (Cat drop-off window; carrier note if applicable.) |
| 3 | Usuario | And if it were a dog instead? |
| 4 | Asistente | (Dog drop-off window; operating days constraint; must remember switch from cat to dog.) |

---

## Conversación 3 — Requisito analítica (animal mayor)

| Campo | Detalle |
| --- | --- |
| Intents | QueryMedicalRequirements, QueryEligibility |
| Tickets principales | VET-9 |
| Apoyo | VET-14 (analítica obligatoria >6 años) |
| Supera si | Obligatorio >6 años; por debajo, recomendada; puede pedir confirmación en casos límite. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | My dog is 8 years old. Is a blood test required before sterilisation? |
| 2 | Asistente | (Confirms mandatory for >6 years per policy.) |
| 3 | Usuario | What if she were 5? |
| 4 | Asistente | (Distinguishes: typically recommended but not mandatory under threshold—consistent with spec.) |

---

## Conversación 4 — Emergencia / fuera de alcance

| Campo | Detalle |
| --- | --- |
| Intents | RequestEmergencyCare |
| Tickets principales | VET-9 |
| Apoyo | VET-14 |
| Supera si | No priorizar reserva; triaje: emergencia veterinaria ya; breve y empático. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | My dog was hit by a car and is bleeding. Can you book me for tomorrow? |
| 2 | Asistente | (Directs to emergency vet now; no scheduling priority over safety.) |

---

## Conversación 5 — Reserva imposible: perra en celo

| Campo | Detalle |
| --- | --- |
| Intents | BookProcedure, CheckAvailability (opcional) |
| Tickets principales | VET-9 |
| Apoyo | VET-14 (~2 meses tras fin del celo) |
| Supera si | Rechazo claro; plazo alineado al caso; sin confirmación falsa. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | I want to book a spay for my female dog. She is currently in heat. |
| 2 | Asistente | (Explains cannot schedule during/around heat; wait until two months after heat ends before sterilisation—per domain rules.) |

---

## Conversación 6 — Horarios de recogida (especie + memoria)

| Campo | Detalle |
| --- | --- |
| Intents | QueryPickUpTime |
| Tickets principales | VET-10, VET-9 |
| Apoyo | VET-14 (perro ~12:00, gato ~15:00) |
| Fuentes (horarios) | Igual que en la conversación 2: prompt, RAG o ambos; una misma conversación valida el uso de cualquiera de esas fuentes si la respuesta es correcta. |
| Supera si | Hora perro; gato en turno 4 sin repetir especie. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | When can I pick up my dog after castration? |
| 2 | Asistente | (Dog pick-up ~12:00 or per spec; brief rationale.) |
| 3 | Usuario | And for a cat? |
| 4 | Asistente | (Cat pick-up ~15:00; consistent with spec.) |

---

## Conversación 7 — Paso a humano

| Campo | Detalle |
| --- | --- |
| Intents | HumanHandoff |
| Tickets principales | VET-9 |
| Apoyo | VET-14 |
| Supera si | Canal concreto (teléfono, email, recepción); placeholders OK; sin bloquear. |
| ¿Suma para la base de 5 puntos? | Sí — memoria de sesión; sin tool de disponibilidad. Dominio vía prompt y/o RAG si es coherente (pueden solaparse; véase arriba). |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | I'd rather speak to a person about my invoice. |
| 2 | Asistente | (Acknowledges; gives escalation path or collects callback preference politely.) |

---

## Conversación 8 — Comprobar disponibilidad (tool)

| Campo | Detalle |
| --- | --- |
| Intents | CheckAvailability |
| Tickets principales | VET-12; VET-13 con calendario real |
| Apoyo | VET-9, VET-10, VET-7, VET-8, VET-14 |
| Supera si | Se invoca la tool; días/huecos concretos; lun–jue y capacidad coherentes con el caso. |
| ¿Suma para la base de 5 puntos? | No — cuenta para el +1 de tool de disponibilidad. |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | I need to spay my cat next week. What days do you have capacity? |
| 2 | Asistente | (Uses check-availability path; species cat already stated—should not re-ask unless unclear; returns valid weekday options consistent with mock or calendar.) |
| 3 | Usuario | Are you open on weekends for surgery? |
| 4 | Asistente | (Clarifies surgical schedule vs weekend; consistent with clinic rules in prompt/docs.) |

---

## Conversación 9 — Capacidad: ya hay dos perros (Tetris / tool)

| Campo | Detalle |
| --- | --- |
| Intents | CheckAvailability, BookProcedure |
| Tickets principales | VET-12; VET-13 con calendario real |
| Apoyo | VET-9, VET-14 (240 min/día, máx. 2 perros/día) |
| Supera si | Tool refleja techo y límite de perros; explica bloqueo; ofrece otro día. |
| ¿Suma para la base de 5 puntos? | No — cuenta para el +1 de tool de disponibilidad. |

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | Can we do my large dog's surgery this Thursday if you already have two other dogs that day? |
| 2 | Asistente | (Uses availability logic; if blocked by two-dog limit or minute budget, states reason clearly; suggests alternatives.) |
| 3 | Usuario | What about the following Tuesday? |
| 4 | Asistente | (Returns a coherent availability outcome for the new day—still via tool/rules, not a generic “yes” without basis.) |

---

## Conversación 10 — Ayuno preoperatorio (instrucciones; prompt y/o RAG)

| Campo | Detalle |
| --- | --- |
| Intents | QueryPreOpInstructions |
| Tickets principales | VET-11 |
| Apoyo | VET-9, VET-10 |
| Fuentes (ayuno / preoperatorio) | Coherente con la página oficial vía system prompt, RAG o ambos. El guion sirve para evaluar respuestas correctas con cualquiera de esas vías. |
| Supera si | Ventana de ayuno y agua alineadas con el caso; si falta contexto, fallback documentado (p. ej. remitir a clínica). |
| ¿Suma para la base de 5 puntos? | No — el +1 RAG exige implementación demostrable del retriever (README + evidencia); ver resumen «System prompt y RAG». |

**+1 pt RAG (VET-11):** Concedido si el equipo documenta ingesta desde la URL y demuestra que la recuperación funciona; no se penaliza que el mismo texto exista también en el prompt.

| Turno | Rol | Mensaje |
| --- | --- | --- |
| 1 | Usuario | How long should my dog fast before the operation? |
| 2 | Asistente | (States fasting window and water guidance per case — from system prompt, retrieved chunks, or both.) |
| 3 | Usuario | Can he drink water right up until we leave home? |
| 4 | Asistente | (Still consistent with pre-op instructions for the case; if unknown, says so and suggests confirming with clinic.) |

---

## Tickets sin conversación dedicada

| Doc VET | EPIC | Motivo |
| --- | --- | --- |
| VET-1 | SET UP | Fork y accesos |
| VET-2 | SET UP | README maestro |
| VET-3 | SET UP | Vercel (+Vercel) |
| VET-4 | SDD | Reglas repo + Jira (+Jira) |
| VET-5 | SDD | enrich |
| VET-6 | SDD | implementar |
| VET-7 | CHATBOT | API |
| VET-8 | CHATBOT | UI chat |

## Checklist de cierre (equipo / profesor)

- [ ] Conversaciones 1 a 7 superadas en la misma sesión, sin tool de disponibilidad (base 5 pt); dominio vía prompt y/o RAG según implementación del equipo (compatibles).
- [ ] +1 RAG: pipeline desde la URL oficial documentado en README y demostración de que el retriever opera (log, captura o prueba acordada). La conversación 10 es el guion típico; solapamiento con el prompt es aceptable.
- [ ] Conversaciones 8 y 9 superadas con tool observable (+Tool).
- [ ] Catálogo de intents alineado con las 10 conversaciones (+Intents).
- [ ] README enlaza a `Jira_Backlog_Caso_Veterinario_ES.md` y al tablero; VET-14 si se citan reglas en corrección.
