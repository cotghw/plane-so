# cotghw-plugins

Personal Claude Code plugin marketplace.

## Install

```bash
claude plugin marketplace add cotghw/claude-plugins
claude plugin install plane-pm@cotghw-plugins
```

The repo is private, so the machine needs git access to it (`gh auth login`).

## Plugins

### plane-pm

Project manager + coder discipline for a self-hosted Plane (Community Edition).

The plugin carries **no credentials and no instance data**. Plane is used only in folders that
hold their own credentials. Bind a folder by running this inside it:

```bash
claude mcp add plane -s local \
  -e PLANE_BASE_URL=https://<host> \
  -e PLANE_WORKSPACE_SLUG=<workspace-slug> \
  -e PLANE_API_KEY=<api-key> \
  -- uvx plane-mcp-server stdio
```

- Local scope stores the key in `~/.claude.json` under that folder only. Subfolders and git
  worktrees of it are bound too; every other folder is not.
- A session started in an unbound folder gets no Plane access from the plugin's script, and the
  skill tells Claude to ask instead of borrowing another folder's key.
- Do not add Plane servers in **user scope** (`-s user`): their tools then appear in every folder.
- Do not put keys in a committed `.mcp.json`.
- Per-project conventions (language, what "Done" means, modules) go in that repo's `CLAUDE.md`
  under a "Plane" heading, not in the plugin.

Limit: the binding check is a guard against mistakes, not a sandbox. Anything that can read
`~/.claude.json` can read the keys stored there.
