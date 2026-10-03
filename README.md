# plane-so

Claude Code plugin marketplace for a self-hosted Plane (plane.so) instance.

## Install

```bash
claude plugin marketplace add cotghw/plane-so
claude plugin install plane-pm@plane-so
```

Inside a Claude Code session the same works as `/plugin marketplace add cotghw/plane-so`, then
`/plugin install plane-pm@plane-so`.

## plane-pm

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
- Check that your home folder has no stray `.git` directory before binding. Claude Code treats
  the nearest `.git` as the project root, so a leftover one in `~` makes every non-git folder
  share one config, and a local-scope binding then covers the whole home folder. Check the
  result with `claude mcp list` in an unrelated folder.
- Per-project conventions (language, what "Done" means, modules) go in that repo's `CLAUDE.md`
  under a "Plane" heading, not in the plugin.

Limit: the binding check is a guard against mistakes, not a sandbox. Anything that can read
`~/.claude.json` can read the keys stored there.
