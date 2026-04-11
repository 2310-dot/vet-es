# Implement workflow (Jira ticket → PR)

Use this workflow when the user asks to **implement** a Jira ticket (e.g. "implement PROJ-123", "run implement for JIRA-456"). Execute phases in order. Use the **backend-langchain-vet** subagent for the development phase.

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
2. **Delegate development to the backend-langchain-vet subagent** (Task tool). Invoke it with a clear prompt that includes:
   - The ticket key and title
   - The AC items / todo list
   - Relevant file paths or modules
   - Any clarifications from Phase 3
3. The subagent follows `.cursor/skills/langchain-vet-chatbots/SKILL.md` and project rules (e.g. TDD, Python, LangChain). Do not duplicate that guidance here.
4. After the subagent completes: run tests, fix any failures, and ensure the implementation matches the AC. Update todos as steps are completed.

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

---

## Checklist (agent self-verify)

- [ ] Ticket read and AC extracted.
- [ ] Plan created and (if needed) confirmed with user.
- [ ] Ambiguities clarified before coding.
- [ ] Comment added on Jira ticket at start of development (reference for "work started").
- [ ] Development done via **backend-langchain-vet** subagent; tests pass.
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
