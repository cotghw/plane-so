# Plane Community Edition: what works through the API

Probed live on a self-hosted instance, **Plane CE v1.4.2**, plane-mcp-server 0.3.3 (plane-sdk 0.3.1); re-probed 2026-09-23
(pages, milestones and `retrieve_by_identifier` had 404'd on 2026-09-22 and now work - the
instance moved under us, so trust the date on this table).
Re-probe after a Plane upgrade (`curl -s https://<host>/api/instances/` shows `current_version`
and `edition`). Official docs describe Pro/Business features as if always present - trust this
table over them for this instance.

| Feature | MCP tool | Status on CE 1.4.2 | Workaround |
|---|---|---|---|
| Work items CRUD, parent/child, assignees, labels, priority, dates | `workitem` | Works. The parent field is `parent`, **not** `parent_id` - a wrong name comes back as plain text (`does not take: parent_id`) with no error flag | - |
| Archive a work item | `workitem archive` / `list_archived` | **404** - no v1 route for `work-items/<id>/archive/` or `archived-work-items/` | User archives in the UI; `project archive` works |
| PQL filters (`pql=`) | `workitem list/count` | **Refused** ("not supported on this edition") | List all, filter client-side; `plane_rest.py items --open` |
| Workspace-scope `list` (no `project_id`) | `workitem` | Paid-edition feature | `search`, or `list` per project |
| `workitem count` | `workitem` | Works with `group_by` from its fixed list | - |
| `retrieve_by_identifier` (PROJ-12) | `workitem` | **Works** (2026-09-23). Takes `workitem_identifier="PROJ-1"` and **no** `project_id` | - |
| States | `state` | Works (project scope) | - |
| Labels | `label` | Works | - |
| Modules + module items | `module` | Works where the project's module feature is on | - |
| Cycles | `cycle` | API works; cycles are a per-project toggle (`cycle_view`), often off | Enable in project settings (user's call) |
| Intake (triage) | `intake` | Works | - |
| Comments (with `@[uuid]` mentions) | `workitem_comment` | Works | - |
| Activity history | `workitem_activity` | Works | - |
| Relations list/create | `workitem_relation` | **404** - the MCP tool calls `/work-item-relations/` and `/dependencies/`, neither of which CE serves | `plane_rest.py relations` / `relate`. CE serves `work-items/<id>/relations/` with **GET + POST only**. Kinds: `blocking`, `blocked_by`, `duplicate`, `relates_to`, `start_after`, `start_before`, `finish_after`, `finish_before` |
| Relation remove | - | **No DELETE** on that endpoint | User removes in UI |
| Links on work items (write) | `workitem_link` | Works (`url` + `title`), verified 2026-09-23 | - |
| Relation definitions (custom) | `workitem_relation list_definitions` | 404 (Pro+) | Built-in types only |
| Project pages | `page` | **Works** (2026-09-23): `list`, `retrieve`, `create`, `update`, `archive`, `delete` - `project_id` **required** | - |
| Workspace-level pages | `page` without `project_id` | 400 `workspace_pages_unsupported` | Put the page in a project |
| Pages ↔ collections / work items | `page set_collection`, `attach_to_workitem`, `detach_from_workitem`, `list_workitem_pages` | Not available | Link the page URL with `workitem_link` |
| Epics | none (no MCP tool) | **Exist on CE** (verified 2026-09-23): REST `projects/<id>/epics/` does GET/POST/DELETE, the Epic type is assigned automatically, and child counters roll up | `plane_rest.py epics` / `epic-new`; attach children with `plane_rest.py adopt <epic key> CHILD...` |
| Work item types (list/create types) | `workitem_type` | **404** (Pro+) | Epics via REST as above; otherwise a plain parent item |
| Custom properties | `workitem_property` | Needs types → unavailable | Labels / description |
| Milestones | `milestone` | **Works** (2026-09-23): `list`, `retrieve`, `create`, `update`, `delete`, `list_workitems`, `manage_workitems` (`add_ids`/`remove_ids`). Create takes `title`, **not** `name` | - |
| Estimates | `project_estimate` | Works | - |
| Views (saved filters) | none | No API tool | User creates in UI; suggest filters |
| Project feature toggles | `project get_features/update_features` | 404 | Project settings in UI |
| Initiatives, releases (+ labels/tags), customers (+ properties/requests), templates, collections, work logs (`worklog_summary`), teamspaces | `initiative`, `release*`, `customer*`, `template`, `collection`, `work_log`, `worklog_summary` | Pro/Business/Enterprise - **do not call**, they 404 | - |

## Concepts (from Plane docs, for reasoning about the board)

- **State groups** are fixed: backlog, unstarted, started, completed, cancelled. Custom state
  names live inside them; reports and "open/closed" logic key on the group.
- **Cycles** = time boxes (sprints). An item is in at most one cycle at a time; at the end the
  unfinished items are transferred to the next cycle (`cycle transfer_workitems`, only after
  the source cycle has ended). Cycles in a project cannot overlap unless parallel cycles (Pro)
  are enabled.
- **Modules** = scope slices (feature area / sub-project) with lead, members, dates, status
  (backlog, planned, in-progress, paused, completed, cancelled) and a progress bar. An item can
  be in several modules. Module status is set by hand - update it when its items move.
- **Views** = saved filter + grouping + layout (list, kanban, calendar, spreadsheet, gantt),
  public to the project or private. They hold no data.
- **Pages** = wiki docs with realtime collaborative editing (live server). Project-scoped only
  through the API here. `delete` refuses until the page is archived: `archive` then `delete`.
- **Epics** = a work item of the Epic type; children are ordinary work items pointing at it with
  `parent`. Deleting the epic **does not delete its children** - they survive with `parent: null`
  (verified 2026-09-23), so an epic can be dissolved without losing work.
- **Relations are two-sided**: POSTing `blocked_by` on A also makes B show `blocking` A. Create
  each relation once, from either end. `GET relations/` returns only `{project_id, issue_id}`
  per entry - no title, no key - which is why `plane_rest.py relations` resolves the ids.
- **Milestones** = a dated checkpoint inside a project, with its own item count / progress. A
  work item belongs to **at most one** milestone - `manage_workitems add_ids` on a second
  milestone *moves* the item, it does not put it in both.
- **Intake** = triage inbox. Guests/outsiders submit; members accept (becomes a real work item),
  decline, mark duplicate, or snooze. The sidebar count is pending items.
- **Archiving** (probed 2026-09-23): work items **cannot be archived through the API** -
  `work-items/<id>/archive/` and `archived-work-items/` both 404, so MCP `workitem archive`
  and `list_archived` are unusable; archiving an item is a UI-only action. `project archive`
  does work (204). Projects can also auto-archive/auto-close completed/cancelled items on a
  timer via `archive_in` / `close_in` (months), done by a background job rather than the API.
- Official Claude integrations: `makeplane/plane-mcp-server` (API key, any instance - what we
  use) and `makeplane/plane-claude-plugin` (OAuth, **Plane Cloud only** - not usable here).

## When a call fails

| Symptom | Cause / what to do |
|---|---|
| 401 | `PLANE_API_KEY` wrong, missing, or the token was revoked |
| 403 | The token's user is not a member of that project, or is a Guest |
| 404 on a whole tool | Paid-edition feature (see the table) or an id from another project |
| 429 | Over `API_KEY_RATE_LIMIT` - 60 requests/min per key. Batch reads, never poll |
| 502 on a page body edit | Plane's live server is down. Nothing is written **partially** - retry once it is back |
| "not supported on this edition" | PQL or a workspace-scope list. Filter client-side |
| Nothing connects | Tunnel/Caddy or the API stack is down: `curl -s https://<host>/api/v1/users/me/ -H "X-API-Key: <key>"` |
| `manage_label` returns OK but no label appears | Parameters are `add_label_id` / `remove_label_id`. Any other name is **silently ignored** and still reports success |

MCP config for a self-hosted instance - never `https://mcp.plane.so/...`, that is Cloud only.
Run it **inside the folder** that should use Plane; local scope keeps the key in
`~/.claude.json` under that folder, out of the repo and out of every other folder:

```bash
claude mcp add plane -s local \
  -e PLANE_BASE_URL=https://<host> \
  -e PLANE_WORKSPACE_SLUG=<workspace-slug> \
  -e PLANE_API_KEY=<api-key> \
  -- uvx plane-mcp-server stdio
```
