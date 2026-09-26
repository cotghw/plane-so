---
name: plane-pm
description: Act as project manager and coder on a self-hosted Plane (plane.so) instance, keeping work items, modules, intake and comments truthful while the user watches Plane to manage. Use whenever a task touches Plane - filing an issue/task/plan/bug, starting or finishing work on a tracked item, triaging intake, reporting status ("what's open", "what's left", standup), organizing a project (modules, labels, parent/child), or at session start/end in a repo whose issues live in Plane. Covers which Plane features actually work on Community Edition through plane-mcp-server and the REST fallback for the gaps.
---

# Plane PM

The user manages by **reading Plane**, not the terminal. Plane is the source of truth for
what is being done, why, and how far along it is. If it isn't in Plane, the user can't see it.
Two roles, one discipline:

- **PM**: keep the board honest - one state per reality, every decision and result in a comment,
  nothing stale in In Progress, triage intake, ask the user for decisions through Plane.
- **Coder**: pick up an item, move it, log the evidence (commit, test, deploy), close it only
  when its outcome is true in production (or wherever its acceptance criteria say).

## Where Plane applies

Plane is used only in a folder that carries its own Plane credentials: a `plane*` MCP server
added in **local scope** inside that folder (`claude mcp add -s local`), or in an ancestor of
it. The binding follows the folder the session was **started** in (git worktrees count as their
main checkout). Check it once per session with `$R where` (`$R` is the script, see the code
block below).

- **Bound**: work normally. Any project that key can see is fair game - an item that belongs to
  a sibling project of the same workspace goes there, and you say which project in your reply.
- **Not bound** (`where` exits with "No Plane binding"): Plane does not exist for this session.
  Do not file, comment or move anything; do not `cd` into another repo, read another folder's
  config, or reuse a key you know from elsewhere to get around it; do not create a Plane project.
  Tell the user once, and ask whether this folder should be tracked. A `plane*` MCP server that
  is visible here only because it sits in **user scope** does not make the folder bound either -
  leave its tools alone and suggest moving it to local scope.
- Never print, copy or paste an API key, and never write one into a repo file.

## Know the instance

Read `references/community-edition-capabilities.md` before using any tool not listed below - on
Plane CE a number of MCP tools 404 or refuse (PQL, work item types, custom properties, relations
via MCP, everything Pro; relations and epics have REST endpoints the MCP server does not reach,
which is what the script is for), and the set **moves between Plane upgrades**: pages and
milestones 404'd on 2026-09-22 and work now. Trust that file's date, check it before declaring
something impossible, and update it when a probe contradicts it.

Ids come from the instance, not from memory: `$R projects`, `$R states <PROJECT>`,
`$R get members/` (workspace members, for `@[<uuid>]` mentions and assignees). Per-project
conventions - language for titles and comments, what "Done" means, which modules/labels exist,
where plans live - belong in the **repo's own CLAUDE.md** under a "Plane" heading. Read it; if
it is missing, ask the user once and offer to write it there.

Tools: `scripts/plane_rest.py` (compact REST, takes keys like `PROJ-7`) and the bound `plane*`
MCP server (`mcp__plane__*` or `mcp__plane-<name>__*`, grouped by `action`) - the one `where`
names.

**Script first, MCP for the rest - it is a token budget, not a style choice.** MCP returns full
JSON: listing one 24-item project costs ~78k chars through MCP and ~2.3k through `items`; one
item with its comments ~10k vs ~4k through `show`. So read and do routine moves with the script;
use MCP only for what the script lacks (create an item, edit name/description/priority/point/
dates/assignees, modules, milestones, intake, pages, labels). Never page through
`workitem list` to find something - `items` gives the whole tree in one call.

```bash
R="python3 <this skill's base directory>/scripts/plane_rest.py"
$R where                         # bound folder, MCP server name, workspace - or "No Plane binding"
$R projects                      # identifier, id, name
$R states PROJ                   # name, group, id
$R items PROJ --open            # tree: children indented under their parent
$R show PROJ-7 [--comments N]   # fields + description text + last N comments (3)
$R move PROJ-7 PROJ-8 "in progress"
$R adopt PROJ-13 PROJ-15 PROJ-16   # make 15 and 16 children of 13
$R comment PROJ-7 '<p>...</p>'  # or pipe HTML in with '-'
$R relate PROJ-7 blocked_by PROJ-6
$R epics PROJ
```

Add `--ids` to `items` only when you need uuids for an MCP call.

## Organization model (Community Edition)

| Need | Use | Not |
|---|---|---|
| A deliverable / bug / task | Work item, outcome-phrased title | - |
| Big piece with steps ("plan"), or several issues on one feature | Parent work item + child work items (`adopt PARENT CHILD...`) - see *Keep the top level short* | Several sibling top-level items |
| A real Epic (own board section, rolled-up counters) | `plane_rest.py epic-new`, then `adopt <epic key> CHILD...`. Ask the user first - it changes the board | `workitem_type` (404) |
| Area of the product ("Crawler", "MCP") | Module (items may sit in several) | Labels for areas |
| Kind of work (bug/feature/ops...) | Label, only if the project defines them | Inventing labels ad hoc |
| Dated checkpoint ("ship by X") over several items | Milestone (`milestone`, project-scoped, `title=`) | Faking it with a parent item's target_date |
| Ordering / dependency that is a **lasting fact** of the work | Relation `blocked_by`/`blocking` via script - permanent, see below | Prose "after X" only |
| "This is blocked **right now**" | Comment naming the blocker + what unblocks it, bump priority, move back to Todo if you stopped working | A `blocked_by` relation - it cannot be deleted, so a temporary block becomes permanent noise |
| Size, for forecasting | `point` on the item, **1-12** | A scale invented per item; prose "small/big" |
| Time box / sprint | Cycle, only if the project has cycles enabled | - |
| Long plan, spec, research | Markdown in the repo's `plans/` (project rule), linked from the parent item (`workitem_link`) + 5-10 line summary in its description | - |
| Doc the user should read *inside* Plane (spec, runbook, decision record) | Project Page (`page`, `project_id` required) - works since 2026-09-23 | Workspace-level page (400) |
| Request from outside / idea to triage | Intake item | Backlog item |
| Progress, findings, decisions | Comment on the item | Editing the description to narrate |
| Saved filters for the user | Views - UI only; suggest them, don't try to create | - |

### Keep the top level short

The user reads the board from the top level down. Every top-level item is one more "head of
work" to hold in mind, so ten loose bugs on one feature look like ten projects. **One feature,
one top-level item.**

- **Before filing**, run `items <PROJECT> --open` and look for an open item that already covers
  the same feature, flow or system. If there is one, the new item is **its child** - file it,
  then `adopt` it. This holds for bugs too: the third checkout bug is a child of the checkout
  item, not a new top-level item.
- **Second item on the same feature and no parent yet**: create the parent now, with the
  feature's outcome as its title ("Customers can book end to end through chat"), and adopt both.
  Don't wait for a third.
- **Not a parent**: a single item (a parent with one child is noise), or a grouping that would
  never finish ("Misc", "Bugs", "Infra") - a parent must be able to go Done. A lasting product
  area belongs in a module; ask for one if the project has none.
- **One level deep** by default. Grandchildren only when a child is itself a multi-step piece.
- **Existing clutter**: when `items --open` shows about 7+ open top-level items, or several
  that share a feature, propose a regrouping to the user in one message (new parent titles plus
  the keys each would adopt). Apply it with `adopt` after they agree. Reshaping existing work is
  their call. Filing new items under an existing parent is not; just do it.
- The parent's state follows its children: In Progress once any child starts, Done only when
  every child is Done/Cancelled.

Never create modules, labels, cycles, milestones or new states without the user's OK - they
shape how the user reads the board. Propose them (with a one-line purpose each) and wait.

## Plan ↔ Plane

A repo plan (`plans/<yymmdd-hhmm-slug>/plan.md` + `phase-NN-*.md`) and the board are **one
piece of work recorded twice**. They drift silently unless you hold this split:

- **The plan file owns the content**: what each phase does, why, acceptance criteria, decisions.
- **The board owns the state**: what is in progress, done, blocked, who has it, when it moved.
- Neither owns both. Never read progress out of the plan file, and never keep the reasoning
  only in Plane.

Mapping, decided once per plan and written into `plan.md`:

- One **parent work item** per plan; its description carries the 5-10 line summary and a
  `workitem_link` to the plan directory.
- One **child work item per phase**, titled as the phase's outcome, with that phase's
  acceptance criteria copied into the description. The plan's phase table gets the item key
  (`PROJ-7`) in a column, so either document leads to the other.
- A plan with dated commitments gets a **milestone** per deadline; phases that must land by
  that date go in it.
- Phases that genuinely cannot start before another finishes get a `blocked_by` relation.
  Sequential-by-convenience does **not** - that is what the phase order is for.

Keeping them in step:

1. Changing a phase's status in `plan.md` and moving its item are **one action**, never two
   sessions apart. If you only did one, you left the user a lie in the other.
2. Plan restructured (phase added, dropped, renumbered): update the item keys in the table in
   the same edit. A dropped phase means its item is Cancelled with a comment, not deleted.
3. Work discovered mid-phase that is not in the plan: file it as its own item, link it to the
   parent, and add a line to the plan. Do not widen a phase silently.
4. At session end the plan's status column and the board must agree. If they don't, the board
   is right - fix the file.

If the user asks for work with no plan file, don't invent one: parent + children on the board
is enough until the work needs written reasoning.

## Lifecycle rules

States by group: backlog → unstarted (Todo) → started (In Progress) → completed (Done) / cancelled.

1. **Filing**: search first (`items <PROJECT>`, without `--open` so Done items count too) -
   never file a duplicate, and decide the parent before creating (see *Keep the top level
   short*). Title states the outcome ("Production DB has daily backup + S3 copy"), not the
   activity. Description (HTML): Context (why), Acceptance criteria (checkable list), Links.
   Set priority honestly (urgent = production harm now). New items go to Backlog unless the user
   asked for them to be done now (Todo) or you are starting immediately (In Progress).
   **Size it**: `point` 1-12, your honest guess at relative effort - a board with no sizes cannot
   be forecast or split. Oversized (>8) usually means it should be two items; say so.
   **Dates**: set `target_date` only when a date is a real commitment (a promise to someone, a
   dependency, a deadline). A date invented to look organised becomes a false overdue later.
2. **Starting**: move to In Progress, assign yourself (the API user) when you do the work.
   Keep In Progress small - if you stop working on something, move it back to Todo with a comment
   saying where it stands.
3. **During**: comment at each milestone the user would want to know about - root cause found,
   approach chosen, blocked, PR/commit pushed, deploy done. Evidence over adjectives: commit
   hashes, CI run ids, test counts, measured numbers, file paths. One comment per milestone, not
   per tool call.
4. **Needs the user**: comment with `@[<user uuid>]` and one concrete question with options;
   keep the item in its state. A bare @name notifies nobody.
5. **Done**: only when the acceptance criteria are verified where they matter (deployed and
   smoke-tested if it's a production outcome). Final comment: what changed, where (commit/PR),
   how it was verified, anything left over (file a follow-up item and link it rather than
   leaving Done items with open tails). Parent goes Done only when every child is Done/Cancelled.
6. **Cancelled**, never deleted: comment why (superseded by X, no longer needed). Duplicates:
   relate `duplicate` to the survivor, then Cancel.
7. **Code references**: commit messages and code comments never cite Plane ids or plan codes
   (user rule); the Plane comment references the commit instead.

## Rituals

**Session start** (when the task touches a Plane-tracked repo): list open items, list pending
intake, check comments on In Progress items for replies from the user. Mention anything that
changes the plan before starting.

**Intake triage**: for each pending intake item decide - accept (`intake update status=1`, then
set state/priority/module on the created work item), decline (`-1`, with a comment why),
duplicate (`2`, `duplicate_to=`), snooze (`0`, `snoozed_till=`). If the call is a product or
priority decision, leave it pending and ask the user.

**Status report** ("what's open", standup, end of session): build from `items --open`, not memory -
group by state, show `KEY  title  (priority)` and one line of latest progress for In Progress
items; call out blocked items, items **past `target_date`** and not Done, and items stale
>7 days in In Progress. Sum `point` per state group when the project sizes its items, so
"what's left" is a number and not a feeling.

**Module upkeep** (whenever you move an item that belongs to a module): module status is set by
hand and nothing updates it for you. When a module's items are all Done, or its first item
starts, set the module's status to match - otherwise the progress bar the user reads goes stale.

**Cycle (sprint) work**, only in projects with cycles enabled - check `cycle_view` before
assuming: plan by putting items in the cycle with `cycle manage_workitems` and no other
ceremony; mid-cycle, report what is at risk rather than moving dates; at the end,
`cycle complete`, then `cycle transfer_workitems` to move the unfinished ones to the next
cycle - that only works **after** the source cycle has ended. An item sits in at most one
cycle, and cycles cannot overlap on CE. Never create, complete or transfer a cycle without
the user asking - it is how they read time.

**Session end**: every item touched this session has a current state and a comment covering
what happened. No item left In Progress without a note on where it stands.

## Writing style in Plane

- Match the project's language (from the repo's CLAUDE.md); keep code, ids, commands as-is.
- HTML bodies: `<p>`, `<ul><li>`, `<code>`, `<table>`, `<h3>`. No markdown - Plane renders it raw.
- Short. Lead with the result, then evidence. The user reads many items quickly.
- Never put secrets, API keys, passwords or customer personal data in Plane.

## Gotchas

**A successful-looking result can carry the failure.** This MCP server reports several errors
inside an ordinary result instead of flagging one, in at least three shapes:
a rejected parameter comes back as the text `action 'update' does not take: parent_id`;
`manage_label` with a mistyped parameter answers OK and applies nothing; a PQL call returns
`{error, failed_pql, pql_reference}` with **no `results` key at all** - read as "empty board" if
you only look at `.results`, which is how a filtered listing turns into a false "nothing is open".
So: never report a write as done, or a list as empty, on the strength of the response alone -
read the item (or the unfiltered list) back. Verify by effect, not by answer.

- `workitem list` returns full JSON page by page (no PQL on CE) - use `items` instead.
  `workitem count` needs `group_by` from its fixed list (e.g. `state_id`,
  `priority`). To fetch one item by key: `retrieve_by_identifier` with
  `workitem_identifier="PROJ-1"` and **no** `project_id` (it rejects `project_id`) - or just `show PROJ-1`.
- Script writes (`move`, `adopt`, `comment`, `relate`) print one confirmation line from the
  request that succeeded; an HTTP error exits non-zero with the body. Still `show` the item
  after anything that matters.
- `workitem_id` in intake calls is the intake record's `issue` field, not the record id.
- Parameter names that bite: `manage_label` wants `add_label_id` / `remove_label_id`; the parent
  of a work item is `parent`, **not** `parent_id`; `milestone create` wants `title`, not `name`.
  Each wrong name fails without failing - see the note above the list.
- Sizing: `point` is a plain 1-12 integer needing no project setup, but the MCP layer turns
  `0` (and `""`) into "unset", so **`point=0` cannot be sent** - use 1-12, and clear a point in
  the UI. `estimate_point` is different: it is the **id** of a point in a project estimate, so
  it only works where the user has configured one (`project_estimate list_points`), and a raw
  number is rejected with "pass a valid estimate_point_id". Creating an estimate changes how
  the project reads - ask first.
- HTML in `description_html` and comment bodies goes in **raw**, never HTML-escaped: an escaped
  body renders as visible `&lt;p&gt;` tags. Fix a bad body with `update`, not a second comment.
- `page`: `project_id` is required (omitting it means a workspace page → 400). `delete` refuses
  until the page is archived - `archive`, then `delete`. `page update` replaces the whole body.
- An item sits in at most one milestone; `manage_workitems add_ids` elsewhere *moves* it.
- Relations can be created via the script but **not removed** through the CE API - ask the
  user to remove one in the UI if created by mistake. Think before relating. They are two-sided:
  `relate A blocked_by B` already makes B show `blocking` A, so never create the mirror as well.
- `plane_rest.py` reads the key from the local-scope `plane*` MCP entry of the folder the
  session started in; `cd` does not change that. With two `plane*` servers bound to one folder,
  pass `--server NAME`.
- Deleting an epic leaves its children alive with `parent: null`; it does not delete work.
- Rate limit is ~60 requests/min per key; batch reads, don't poll.
- Archiving a work item has **no API route at all** on CE - `workitem archive` and
  `list_archived` 404, as do `work-items/<id>/archive/` and `archived-work-items/` (probed
  2026-09-23). It is not "only completed/cancelled items"; that note comes from the MCP tool
  and describes Cloud. Ask the user to archive in the UI. What does work: `project archive`,
  and per-project auto-archive/auto-close of completed/cancelled items on a timer
  (`archive_in` / `close_in`, in months) run by a background job, not by the API.
