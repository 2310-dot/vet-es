# Implement workflow (Jira ticket → PR)

Use this workflow when the user asks to **implement** a Jira ticket (e.g. "implement PROJ-123", "run implement for JIRA-456"). Execute phases in order. Use the **backend-langchain-vet** subagent for backend development in Phase 4 when the ticket changes application code (see **Skills, subagents, and related commands** below).

---

## Skills, subagents, and related commands (BE / FE / PM)

Use this table so a new contributor knows **which skill to read** and **which Cursor subagent** (Task tool) fits each kind of work. Paths are relative to the repo root.

| Area | Skill (follow during implementation) | Subagent (`Task`) | When to use |
| ---- | ------------------------------------ | ----------------- | ----------- |
| **PM / spec** | `.cursor/skills/product-manager-ticket-enrichment/SKILL.md` | **`product-manager`** | Vague tickets: run **[`enrich.md`](enrich.md)** first to harden AC, risks, and dependencies. Optional if the ticket is already dev-ready. |
| **Backend** (Python, LangChain, FastAPI, clinic bot) | `.cursor/skills/langchain-vet-chatbots/SKILL.md` | **`backend-langchain-vet`** | **Phase 4** when changing backend code, prompts, tools, RAG, memory, or API behavior. |
| **Frontend** (UI, channel client) | **None in-repo yet** — add `.cursor/skills/<frontend>/SKILL.md` when the channel is fixed; then reference it here. | **`generalPurpose`** (or a future FE subagent) | **Phase 4** for UI or client-only tickets until a frontend skill exists. |

**Agent personas** (used with the subagents above): `.cursor/agents/backend-langchain-vet.md`, `.cursor/agents/product-manager.md`.

**Docs-only tickets** (commands, README, pure documentation): the **parent agent** may implement without **`backend-langchain-vet`**; still use Phase 6 PR structure and run **tests** whenever code paths change.

---

## Entry criteria (start)

- You have a **Jira key** or spec from which AC can be derived, or you will run **[`enrich.md`](enrich.md)** first.
- **user-Atlassian** MCP is available if you will read or transition Jira issues from this workflow.

## Exit criteria (“implemented”)

The ticket is **implemented** for this workflow when:

1. **Build:** Changes match the ticket AC (and tests pass where applicable).
2. **PR:** A pull request is open to **`2310-dot/vet-es`** / **`main`** (never upstream `kuuli/enae-vet-es`).
3. **Traceability:** PR body includes Jira link, summary, AC checklist, and testing notes (Phase 6).
4. **Board:** Jira reflects active work (**In Progress**) and, after the PR exists, **In Review** or your team’s equivalent; if the board has no review column, use a PR comment plus **Done** after merge (see Phase 7).

---

## PR and review checklist (aligned with Phase 6)

**Author**

- [ ] PR targets **`2310-dot/vet-es`**, base **`main`**.
- [ ] Branch name includes the ticket key when applicable.
- [ ] Title and body reference Jira; body has an **AC checklist**.
- [ ] **Testing** section documents commands run (e.g. `pytest`) or states **N/A** for docs-only.
- [ ] No secrets committed; new env vars documented in **README** / `.env.example` if needed.

**Reviewer**

- [ ] AC satisfied or gaps explicitly called out.
- [ ] Vet/clinic behavior matches `docs/` where relevant; no invented diagnoses or dosages.

---

## Prerequisites

- **Jira ticket key**: User provides it (e.g. `PROJ-123`). If missing, ask.
- **Jira MCP**: Use the **user-Atlassian** MCP server. For any Jira call you need `cloudId` and `issueIdOrKey`. Get `cloudId` first via `getAccessibleAtlassianResources` (no args); then use the returned cloud ID with the issue key for `getJiraIssue`, `getTransitionsForJiraIssue`, and `transitionJiraIssue`.

---

## Phase 1: Read the ticket

1. Call **getAccessibleAtlassianResources** (user-Atlassian) to obtain `cloudId`.
2. Call **getJiraIssue** (user-Atlassian) with `cloudId` and `issueIdOrKey` (the ticket key). Prefer `responseContentFormat: "markdown"` for readable description.
3. Summarize for the user: **title**, **description**, **Acceptance Criteria (AC)**. Extract every AC item as a discrete task (these drive the plan and the PR description).

---

## Phase 2: Create a plan

1. From the AC, create a **todo list** (use the Todo tool): one todo per AC item or logical implementation step.
2. Order steps so dependencies are respected (e.g. tests before implementation if TDD).
3. Show the plan to the user and confirm before starting development (unless the user has already approved).

---

## Phase 3: Ask questions if needed

- If the ticket or AC is ambiguous, missing environment details, or conflicts with the codebase, **ask the user** before coding.
- Do not assume: clarify API contracts, config, or product expectations when unclear.

---

## Phase 4: Develop the code

1. **Add a comment on the Jira ticket** so there is a reference when development started. Call **addCommentToJiraIssue** (user-Atlassian) with `cloudId`, `issueIdOrKey`, and a `commentBody` in markdown (use `contentFormat: "markdown"`). The comment should include:
   - A short line that implementation has started (e.g. "Implementation started via Cursor implement workflow.")
   - Optional: current date/time or a one-line summary of the plan (e.g. "Plan: [AC1], [AC2], …"). Keep it concise so the ticket has a clear "work started" reference.
2. **Delegate development** (Task tool) using the **Skills, subagents** table:
   - **Backend / LangChain / API** work → **`backend-langchain-vet`** with `.cursor/skills/langchain-vet-chatbots/SKILL.md`.
   - **Frontend-only** work (until a FE skill exists) → **`generalPurpose`** with ticket AC and repo conventions.
   - **Docs-only** → parent agent may implement directly.
   Pass: ticket key and title, AC / todos, file paths, Phase 3 clarifications.
3. After delegation (or parent-agent work for docs-only): run tests when code changed, fix failures, and ensure the outcome matches the AC. Update todos as steps are completed.

---

## Phase 5: Move ticket from To Do → In Progress

1. Call **getTransitionsForJiraIssue** (user-Atlassian) with `cloudId` and `issueIdOrKey` to list available transitions.
2. Find the transition that moves the issue **to "In Progress"** (or your board’s equivalent; transition names are project-specific). Use the transition’s `id`.
3. Call **transitionJiraIssue** with `cloudId`, `issueIdOrKey`, and `transition: { "id": "<transitionId>" }`.
4. If the user’s board uses different status names, pick the transition that corresponds to “work started” and document the choice briefly.

---

## Phase 6: Create a PR with a good description

1. Create a branch from the default branch (e.g. `main`/`master`), name it by ticket and short slug (e.g. `PROJ-123-add-patient-lookup-tool`).
2. Commit changes with a message that references the ticket (e.g. `PROJ-123: Add patient lookup tool and tests`).
3. Push the branch and open a **Pull Request** (via Git + GitHub MCP or `gh` CLI if available).
   IMPORTANT: This repo is a fork. PRs MUST target `2310-dot/vet-es`, never upstream `kuuli/enae-vet-es`. Always pass `--repo 2310-dot/vet-es` (or use the GitHub MCP with owner=`2310-dot`, repo=`vet-es`).
   `gh pr create --repo 2310-dot/vet-es --base main --head <branch> --title "<title>" --body "<body>"`
4. **PR description** must include:
   - **Jira ticket**: link or key (e.g. `[PROJ-123](url)`).
   - **Summary**: 1–2 sentences on what this change does.
   - **Acceptance criteria**: Checklist of AC items, with checkboxes (e.g. `- [x] AC1: ...`).
   - **Testing**: How to run tests and what was verified.
   - **Notes**: Breaking changes, config, or follow-ups if any.

---

## Phase 7: Move ticket from In Progress → In Review

1. Call **getTransitionsForJiraIssue** again for the same issue to get current transitions.
2. Find the transition that moves the issue **to "In Review"** (or equivalent, e.g. "Code Review").
3. Call **transitionJiraIssue** with that transition `id`.
4. Optionally add a short **comment** on the Jira issue (e.g. "PR opened: <link>") using **addCommentToJiraIssue** if the team expects it.

If your board has **no In Review** status (only e.g. To Do / In Progress / Done), leave the issue **In Progress** until the PR is merged, add a PR link in a comment, then transition to **Done** per team practice.

---

## Checklist (agent self-verify)

- [ ] Ticket read and AC extracted.
- [ ] Plan created and (if needed) confirmed with user.
- [ ] Ambiguities clarified before coding.
- [ ] Comment added on Jira ticket at start of development (reference for "work started").
- [ ] Development done via the right **subagent** (see Skills table) or parent agent for docs-only; tests pass when code changed.
- [ ] Ticket moved To Do → In Progress.
- [ ] PR created with ticket ref, summary, AC checklist, and testing notes.
- [ ] Ticket moved In Progress → In Review; comment added if desired.

---

## Invocation

User says e.g.:

- "Implement PROJ-123"
- "Run the implement workflow for JIRA-456"
- "Implement the ticket in this link: …"

Then follow this document from Phase 1.

---

## Relation to **enrich**

- **[`enrich.md`](enrich.md)** sharpens the **spec** (PM skill, phased refinement).
- **This document** ships **code** and a **PR** from dev-ready AC.
