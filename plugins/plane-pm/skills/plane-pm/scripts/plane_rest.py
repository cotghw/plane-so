#!/usr/bin/env python3
"""Compact Plane REST client for Plane Community Edition - prefer it over MCP reads.

Output is terse plain text (one line per item, HTML flattened, UTF-8 kept as-is) so reading
the board costs a fraction of the tokens of MCP's full JSON. It also covers what
plane-mcp-server cannot do on CE: relations (the MCP tool 404s) and epics.

Credentials are bound to a folder. They come only from a `plane*` MCP server configured in
local scope (`claude mcp add -s local`, stored in ~/.claude.json under that folder) for the
folder this Claude Code session was started in, or its nearest ancestor. A `cd` inside a Bash
call does not change that folder; user-scope servers and environment variables are ignored.
So a session opened in an untracked folder cannot reach Plane by borrowing another folder's
key. Any project the bound key can see may be used - cross-project work in one workspace is fine.

PROJECT is an identifier (PROJ) or a project uuid; KEY is PROJ-7.
With several plane* servers bound to the same folder, pick one with --server NAME.

Usage:
  plane_rest.py where                            folder, server and workspace this session is bound to
  plane_rest.py projects                         identifier, id, name of every project the key sees
  plane_rest.py states PROJECT                   state name, group, id
  plane_rest.py items PROJECT [--open] [--ids]  tree of items: KEY state prio pts name
  plane_rest.py show KEY [--comments N]          one item: fields, description text, last N comments (3)
  plane_rest.py move KEY STATE [KEY...]          set state by name (case-insensitive), e.g. "in progress"
  plane_rest.py adopt PARENT_KEY CHILD_KEY...    set the parent of each child
  plane_rest.py comment KEY HTML|-               add a comment; "-" reads the HTML from stdin
  plane_rest.py relations KEY
  plane_rest.py relate KEY TYPE OTHER_KEY...
        TYPE: blocking blocked_by relates_to duplicate start_before start_after finish_before finish_after
        (Removing a relation has no public endpoint on CE 1.4.2 -- ask the user to do it in the UI.)
  plane_rest.py activity KEY                     field changes, oldest first
  plane_rest.py epics PROJECT                    id, done/total, priority, name (no MCP tool for these)
  plane_rest.py epic-new PROJECT NAME            create an epic; attach children with `adopt`
  plane_rest.py get PATH                         raw GET under /api/v1/workspaces/<slug>/
"""
import html, json, os, re, subprocess, sys, urllib.request, urllib.error


def session_folder():
    """Folder the Claude Code session was started in, independent of the shell's cwd."""
    pid = os.environ.get("CLAUDE_PID")
    if pid:
        try:
            return os.readlink(f"/proc/{pid}/cwd")
        except OSError:
            pass
        try:  # macOS has no /proc; lsof prints the cwd as an "n<path>" line.
            out = subprocess.run(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
                                 capture_output=True, text=True, timeout=5).stdout
            for line in out.splitlines():
                if line.startswith("n/"):
                    return line[1:]
        except (OSError, subprocess.SubprocessError):
            pass
    return os.getcwd()  # run by hand, outside Claude Code


def main_checkout(folder):
    """Main working tree when folder is a git worktree - Claude Code shares its config with worktrees."""
    try:
        common = subprocess.run(["git", "-C", folder, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    return os.path.dirname(common) if os.path.basename(common) == ".git" else None


def bound_servers(projects, path):
    return {n: s.get("env", {}) for n, s in projects.get(path, {}).get("mcpServers", {}).items()
            if n.startswith("plane") and s.get("env", {}).get("PLANE_API_KEY")}


def load_config(server=None):
    folder = session_folder()
    try:
        projects = json.load(open(os.path.expanduser("~/.claude.json"))).get("projects", {})
    except (OSError, ValueError):
        projects = {}
    for path in filter(None, [folder, main_checkout(folder)]):
        while True:  # the nearest ancestor with a binding wins
            servers = bound_servers(projects, path)
            if servers:
                if server:
                    servers = {n: e for n, e in servers.items() if n == server}
                if len(servers) != 1:
                    sys.exit(f"Plane servers bound to {path}: {', '.join(sorted(bound_servers(projects, path)))}"
                             " - pick one with --server NAME")
                name, env = next(iter(servers.items()))
                base = env.get("PLANE_BASE_URL") or env.get("PLANE_API_HOST_URL")
                if not base or not env.get("PLANE_WORKSPACE_SLUG"):
                    sys.exit(f"MCP server {name} bound to {path} lacks a base URL or PLANE_WORKSPACE_SLUG")
                return {"folder": path, "server": name, "base": base,
                        "slug": env["PLANE_WORKSPACE_SLUG"], "key": env["PLANE_API_KEY"]}
            if os.path.dirname(path) == path:
                break
            path = os.path.dirname(path)
    sys.exit(f"No Plane binding for this session's folder ({folder}).\n"
             "Plane is not used here. Do not cd into another repo or reuse another folder's key - tell the "
             "user, and ask whether this folder should be tracked in Plane (bound by running "
             "`claude mcp add -s local ...` inside it).")


SERVER = None
if "--server" in sys.argv[:-1]:
    i = sys.argv.index("--server")
    SERVER = sys.argv[i + 1]
    del sys.argv[i:i + 2]
CFG = load_config(SERVER)
BASE = f"{CFG['base'].rstrip('/')}/api/v1/workspaces/{CFG['slug']}/"
UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def call(method, path, body=None):
    req = urllib.request.Request(BASE + path.lstrip("/"), method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header("X-API-Key", CFG["key"])
    req.add_header("Content-Type", "application/json")
    # Cloudflare in front of an instance can reject urllib's default UA with 403 "error code: 1010".
    req.add_header("User-Agent", "curl/8.5.0")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {method} {path}: {e.read()[:300].decode(errors='replace')}")


def paged(path):
    cursor = None
    while True:
        sep = "&" if "?" in path else "?"
        page = call("GET", f"{path}{sep}per_page=100" + (f"&cursor={cursor}" if cursor else ""))
        yield from page.get("results", [])
        if not page.get("next_page_results"):
            return
        cursor = page["next_cursor"]


def text(h, limit=None):
    """Flatten Plane HTML to readable text: block tags become newlines, list items get '- '."""
    t = re.sub(r"<li[^>]*>", "\n- ", h or "")
    t = re.sub(r"</t[dh]>", " | ", t)
    t = re.sub(r"<(br|/p|/h\d|/tr|/div|/li|/ul|/ol)[^>]*>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"\n\s*\n+", "\n", re.sub(r"[ \t]+", " ", t)).strip()
    return t if not limit or len(t) <= limit else t[:limit] + " …"


def project(ref):
    if UUID.match(ref):
        return call("GET", f"projects/{ref}/")
    for p in paged("projects/"):
        if p["identifier"].upper() == ref.upper():
            return p
    sys.exit(f"no project with identifier {ref}")


def item(key):
    return call("GET", f"work-items/{key.upper()}/")


def states(pid):
    return {s["id"]: s for s in paged(f"projects/{pid}/states/")}


def items(ref, open_only=False, ids=False):
    proj = project(ref)
    st = states(proj["id"])
    rows = list(paged(f"projects/{proj['id']}/work-items/"))
    by_id = {r["id"]: r for r in rows}
    kids = {}
    for r in rows:
        kids.setdefault(r["parent"] if r.get("parent") in by_id else None, []).append(r)

    def show(r, depth):
        s = st.get(r["state"], {})
        if open_only and s.get("group") in ("completed", "cancelled") and not any_open(r):
            return
        cols = [f"{'  ' * depth}{proj['identifier']}-{r['sequence_id']}", s.get("name", "?"), r["priority"],
                str(r.get("point") or "-"), r["name"]] + ([r["id"]] if ids else [])
        print("\t".join(cols))
        for c in sorted(kids.get(r["id"], []), key=lambda c: c["sequence_id"]):
            show(c, depth + 1)

    def any_open(r):
        # A closed parent still prints under --open when a child is open, so the tree stays whole.
        return any(st.get(c["state"], {}).get("group") not in ("completed", "cancelled") or any_open(c)
                   for c in kids.get(r["id"], []))

    for r in sorted(kids.get(None, []), key=lambda r: r["sequence_id"]):
        show(r, 0)


def show_item(key, n_comments=3):
    r = item(key)
    pid = r["project"]
    s = states(pid).get(r["state"], {})
    parent = call("GET", f"projects/{pid}/work-items/{r['parent']}/") if r.get("parent") else None
    ident = key.upper().rsplit("-", 1)[0]
    ptxt = f"{ident}-{parent['sequence_id']}" if parent else "-"
    print(f"{key.upper()}  {r['name']}")
    print(f"state={s.get('name', '?')}  priority={r['priority']}  point={r.get('point') or '-'}  "
          f"target={r.get('target_date') or '-'}  parent={ptxt}  updated={r['updated_at'][:10]}  id={r['id']}")
    desc = text(r.get("description_html"))
    if desc:
        print("---\n" + desc)
    comments = list(paged(f"projects/{pid}/work-items/{r['id']}/comments/"))
    if comments and n_comments:
        print(f"--- comments ({len(comments)}, last {min(n_comments, len(comments))})")
        for c in sorted(comments, key=lambda c: c["created_at"])[-n_comments:]:
            print(f"[{c['created_at'][:16]}] {text(c['comment_html'], 1200)}")


def move(state_name, keys):
    for key in keys:
        r = item(key)
        match = [s for s in states(r["project"]).values() if s["name"].lower() == state_name.lower()]
        if not match:
            sys.exit(f"no state '{state_name}' in {key}'s project")
        call("PATCH", f"projects/{r['project']}/work-items/{r['id']}/", {"state": match[0]["id"]})
        print(f"{key.upper()} -> {match[0]['name']}")


def adopt(parent_key, child_keys):
    p = item(parent_key)
    for key in child_keys:
        c = item(key)
        call("PATCH", f"projects/{c['project']}/work-items/{c['id']}/", {"parent": p["id"]})
        print(f"{key.upper()} -> parent {parent_key.upper()}")


def main(argv):
    if len(argv) < 2 or (len(argv) < 3 and argv[1] not in ("where", "projects")):
        sys.exit(__doc__)
    cmd, a = argv[1], argv[2:]
    if cmd == "where":
        print(f"folder={CFG['folder']}  server={CFG['server']}  workspace={CFG['slug']}  host={CFG['base']}")
    elif cmd == "projects":
        for p in paged("projects/"):
            print(f"{p['identifier']}\t{p['id']}\t{p['name']}")
    elif cmd == "states":
        for st in states(project(a[0])["id"]).values():
            print(f"{st['name']}\t{st['group']}\t{st['id']}")
    elif cmd == "items":
        items(a[0], "--open" in a, "--ids" in a)
    elif cmd == "show":
        show_item(a[0], int(a[a.index("--comments") + 1]) if "--comments" in a else 3)
    elif cmd == "move":
        move(a[-1], a[:-1])
    elif cmd == "adopt":
        adopt(a[0], a[1:])
    elif cmd == "comment":
        r = item(a[0])
        body = sys.stdin.read() if a[1] == "-" else a[1]
        c = call("POST", f"projects/{r['project']}/work-items/{r['id']}/comments/", {"comment_html": body})
        print(f"comment {c['id']} on {a[0].upper()}")
    elif cmd == "relations":
        r = item(a[0])
        groups = call("GET", f"projects/{r['project']}/work-items/{r['id']}/relations/")
        ident = a[0].upper().rsplit("-", 1)[0]
        for kind, entries in groups.items():
            for e in entries:
                o = call("GET", f"projects/{e['project_id']}/work-items/{e['issue_id']}/")
                print(f"{kind}\t{ident}-{o['sequence_id']}\t{o['name']}")
    elif cmd == "relate":
        r = item(a[0])
        others = [item(k)["id"] for k in a[2:]]
        call("POST", f"projects/{r['project']}/work-items/{r['id']}/relations/",
             {"relation_type": a[1], "issues": others})
        print(f"{a[0].upper()} {a[1]} {' '.join(k.upper() for k in a[2:])}")
    elif cmd == "activity":
        r = item(a[0])
        for x in paged(f"projects/{r['project']}/work-items/{r['id']}/activities/"):
            if x.get("field"):
                print(f"{x['created_at'][:16]}\t{x['field']}\t{x.get('old_value')} -> {x.get('new_value')}")
    elif cmd == "epics":
        # `/epics/` exists on CE even though the MCP workitem_type tool 404s.
        for e in paged(f"projects/{project(a[0])['id']}/epics/"):
            print(f"{e['id']}\t{e['completed_issues']}/{e['total_issues']}\t{e['priority']}\t{e['name']}")
    elif cmd == "epic-new":
        e = call("POST", f"projects/{project(a[0])['id']}/epics/", {"name": a[1]})
        print(f"epic {e['id']}\t{e['name']}")
    elif cmd == "get":
        print(json.dumps(call("GET", a[0]), indent=1, ensure_ascii=False))
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
