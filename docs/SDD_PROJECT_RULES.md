# Normas SDD del proyecto (repositorio + tablero Jira)

Este documento fija el marco **SDD** (Specification-Driven Development / ingeniería con contexto explícito) para el equipo: las mismas fuentes de verdad y las mismas reglas de cierre en todo el flujo de trabajo.

## Fuentes de verdad operativas

| Fuente | Rol | Enlace canónico |
|--------|-----|-----------------|
| **Repositorio Git** | Código, configuración, pruebas, documentación técnica versionada | [https://github.com/2310-dot/vet-es](https://github.com/2310-dot/vet-es) |
| **Proyecto y tablero Jira (Vet-es)** | Alcance por ticket, criterios de aceptación, estado del trabajo, historial de decisión | [https://eliuperez4.atlassian.net/jira/software/projects/VE](https://eliuperez4.atlassian.net/jira/software/projects/VE) |

Cualquier otra copia (chat, correo, notas) es **derivada**. Si hay conflicto entre canales, prevalece lo acordado en **repo + Jira**.

## Obligación de incluir repo y tablero en el contexto de trabajo

En todo trabajo que implique implementación, revisión o decisión técnica, el contexto debe referenciar de forma explícita:

1. **El repositorio** (rama, PR o ruta relevante), y  
2. **El tablero o el issue de Jira** (clave `VE-xxx`, enlace al issue o al tablero del proyecto).

Esto aplica como mínimo a:

- **Prompts y asistentes de IA** (p. ej. Cursor): indicar repo clonado y ticket Jira activo cuando exista.  
- **Pull requests**: título o descripción deben enlazar el issue Jira correspondiente; la descripción debe permitir validar los criterios de aceptación.  
- **Decisiones de alcance**: registrar en el issue de Jira (comentario o actualización de campos) si cambia el entendimiento respecto al ticket.

Objetivo: que cualquier revisor o compañero pueda ir de **ticket → código → ticket** sin adivinar dónde quedó registrado el trabajo.

## Regla de cierre de trabajo (sin ambigüedad)

**No está permitido dar por cerrada una implementación asociada a un ticket de Jira únicamente con cambios locales, merges internos o mensajes en herramientas de chat.**

Se considera **cerrada** una implementación ligada a un issue **solo si**, de forma **visible en Jira**, se cumple **todo** lo siguiente:

1. **El código o la documentación** está en el repositorio remoto de forma trazable (por lo general: PR abierto o fusionado en la rama acordada del proyecto).  
2. **El issue en Jira se ha actualizado** con al menos: un comentario que enlace el PR o describa el entregable, y la **transición de estado** que el equipo use para “revisión” o “hecho”, según el flujo del tablero.  
3. Los **criterios de aceptación** del ticket han sido comprobados y, si alguno no aplica, queda **indicado en el issue** con breve motivo.

Si falta cualquiera de los tres puntos anteriores, el trabajo **no** se considera cerrado a efectos de SDD, aunque el desarrollador o el asistente lo marque como completado en otro canal.

## Cómo usar este documento

- Antes de empezar una tarea: abre el issue en Jira y clona/actualiza el repo.  
- Durante la tarea: mantén el issue al día (bloqueos, cambios de alcance).  
- Al terminar: PR + comentario en Jira + transición de estado; revisa la checklist de criterios de aceptación en la descripción del PR o en el propio issue.

Con esto el equipo puede aplicar las normas **sin información crítica adicional**: enlaces canónicos arriba, obligación de contexto en la sección 2, y definición operativa de “cerrado” en la sección 3.
