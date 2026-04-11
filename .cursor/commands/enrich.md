# Enrich workflow (Jira ticket → phased refinement)

Use this workflow when the user asks to **enrich**, **groom**, or **refine** a Jira ticket (e.g. "enrich VETES-1", "/enrich PROJ-123", "improve this ticket: …"). The goal is to improve the issue in **phases** using product-management best practices, then optionally publish back to Jira **only with explicit user approval**.

---

## Prerequisites

- **Jira ticket key** or URL: User provides it (e.g. `VETES-1`). If missing, ask.
- **Atlassian MCP**: Same as the implement workflow. Obtain `cloudId` via **getAccessibleAtlassianResources**; use **getJiraIssue** with `cloudId`, `issueIdOrKey`, and `responseContentFormat: "markdown"` when supported.
- **Skill**: `.cursor/skills/product-manager-ticket-enrichment/SKILL.md` (and `reference.md` in that folder for the output template).
- **Product manager persona**: `.cursor/agents/product-manager.md`.

---

## Delegation model (product manager)

Phases **2–5** require deep product thinking. **Delegate** that work so the PM methodology stays consistent:

1. Use the **Task** tool with **`subagent_type`: `generalPurpose`** (unless a dedicated `product-manager` subagent is available in your environment).
2. In the task prompt, instruct the subagent to:
   - Read **`.cursor/agents/product-manager.md`** and follow it as its role definition.
   - Apply **`.cursor/skills/product-manager-ticket-enrichment/SKILL.md`** phases **A–E** (Diagnose → Structure → AC hardening → Delivery readiness → Quality gate).
   - Use the **reference template** in `.cursor/skills/product-manager-ticket-enrichment/reference.md` for the consolidated output.
3. Pass the subagent: full **ticket title and description** (markdown), any **labels**, **issue type**, **status**, and **links** from Phase 1; plus **repo context** (e.g. `CLAUDE.md` / `docs/` paths) if enrichment should align with this codebase.

The **parent agent** keeps responsibility for Jira API calls, user approval, and optional Jira updates (Phases 1, 6–7).

---

## Phase 1: Ingest the ticket

1. Call **getAccessibleAtlassianResources** to obtain `cloudId`.
2. Call **getJiraIssue** with `cloudId`, `issueIdOrKey`, and readable description format (`responseContentFormat: "markdown"` when available).
3. Capture: **summary**, **description**, **acceptance criteria** (if embedded), **issue type**, **status**, **labels**, **parent/epic** if visible, and **issue links** if relevant.
4. Give the user a **one-paragraph** restatement of what the ticket is trying to achieve (no solutions yet).

---

## Phase 2: Diagnose (delegated)

Run the **Task** (`generalPurpose`) PM delegation described above. Request **Phase A output only**:

- Maturity classification.
- Gap list and contradictions.
- Assumptions to validate.

Present this to the user briefly. If **blocking ambiguities** exist, **ask the user** targeted questions before Phase 3.

---

## Phase 3: Structure (delegated)

Same PM delegation. Request **Phase B output**:

- Problem / opportunity, desired outcome.
- In scope / out of scope.
- User scenarios (if applicable).
- Constraints.

Show the user the structured draft. Incorporate user corrections if they reply.

---

## Phase 4: Acceptance criteria hardening (delegated)

Same PM delegation. Request **Phase C output**:

- Numbered, testable AC.
- Negative paths and validation.
- Edge cases that change behavior.
- NFRs only when justified.

**Do not** proceed to Phase 5 until AC are clearly testable or explicitly flagged as subjective with an owner.

---

## Phase 5: Delivery readiness (delegated)

Same PM delegation. Request **Phase D + E**:

- Dependencies, risks & mitigations, open questions (must-before-dev vs defer).
- Metrics / signals (if any).
- Optional subtask breakdown.
- Quality gate checklist result (pass/fail with fixes applied).

---

## Phase 6: Consolidate

1. Merge Phase 2–5 results into **one** markdown document using **`reference.md`** as the skeleton.
2. Propose an improved **title** only if the current title is misleading; otherwise keep the original and note the suggestion in **Changelog vs original ticket**.
3. Present the full **Enriched ticket** to the user for review.

---

## Phase 7: Publish (user must choose)

**Never** overwrite the Jira description without explicit user confirmation.

Offer three options:

| Option | Action |
|--------|--------|
| **A — Chat only** | User copies from chat; no Jira write. |
| **B — Comment** | Call **addCommentToJiraIssue** with `contentFormat: "markdown"`. Use a short top summary plus the full enriched body (if too long, split: summary comment + "continued in next comment" or attach per team practice). |
| **C — Replace description** | Only if the user explicitly approves. Call **editJiraIssue** with `fields` including the description in markdown and `contentFormat: "markdown"` if supported. Warn that history/audit may make rollback harder. |

After publishing, optionally add a one-line comment: e.g. "Ticket enriched via Cursor enrich workflow (date)."

---

## Checklist (agent self-verify)

- [ ] Ticket ingested; user got a concise restatement.
- [ ] Phases A–E executed via **PM delegation** (skill + agent file).
- [ ] Final artifact uses the **reference template** and passes the skill **quality gate**.
- [ ] User approved **how** to publish (A / B / C) before any **editJiraIssue**.
- [ ] Domain alignment: no invented vet/clinical rules; `docs/` conflicts called out.

---

## Invocation

User says e.g.:

- "Enrich VETES-1"
- "/enrich PROJ-123"
- "Groom this Jira ticket: https://…/browse/KEY"

Then follow this document from Phase 1.

---

## Relation to **implement**

- **enrich** improves the **spec**; **implement** builds from it. After enrich, suggest running **implement** only when AC are stable and open questions are resolved or explicitly deferred.
