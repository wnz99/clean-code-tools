# Shared MCP installation

One local HTTP service serves every repository and agent session. Clients use
`http://127.0.0.1:8765/mcp` directly, so opening another task does not start a
Python server or proxy. The service uses stateless HTTP to avoid accumulating
idle MCP sessions.

## Install and connect

From the clean-code-tools checkout:

```bash
python3 scripts/install_codex_skill.py --agent codex --project /path/to/repo --replace
python3 scripts/install_codex_skill.py --agent claude --project /path/to/repo --replace
```

Select the agents you use. The installer creates the isolated runtime and index
under `${CLEAN_CODE_TOOLS_HOME:-~/.clean-code-tools}`, starts the HTTP service,
then registers the client. An identical installed runtime and index are reused
for subsequent projects. The server continues after the installer exits.

Restart agents and verify `clean_code_index_info`, then call
`search_clean_code_patterns` with a narrow query and check it returns patterns.
`CLEAN_CODE_MCP_PORT` changes the port; use the same value for the server and
every client installation.

## Existing clients

Replace old stdio registrations in Codex configuration with:

```toml
[mcp_servers.clean-code-tools]
url = "http://127.0.0.1:8765/mcp"
```

For Claude Code, the `.mcp.json` server entry is:

```json
{"mcpServers":{"clean-code-tools":{"type":"http","url":"http://127.0.0.1:8765/mcp"}}}
```

Remove that entry's old `command`, `args`, and `env`. Preserve all other MCP
entries. The installer migrates its own managed Codex blocks and refuses to
overwrite unmanaged entries. Put the URL in global agent configuration when
all repositories should inherit it; update repo overrides and aliases too.
Already-running agents keep their old connections until restarted.

## Startup and lifecycle

After a reboot, start or reuse the installed service with:

```bash
~/.clean-code-tools/.venv/bin/python ~/.clean-code-tools/runtime/scripts/start_shared_mcp.py
```

The starter checks service identity and runtime home, waits for readiness, and
fails explicitly if startup fails. It never starts a private server per client.
Logs go to `~/.clean-code-tools/shared-server.log`.

For automatic login startup, use launchd on macOS or a user systemd service on
Linux. Its executable and arguments must be absolute paths to:

```text
~/.clean-code-tools/.venv/bin/python
~/.clean-code-tools/runtime/scripts/clean_code_mcp_server.py
--shared
```

Expand `~` in service files. Set `CLEAN_CODE_TOOLS_HOME` and the working directory
to that absolute home. Shared mode sets absolute index/custom-store defaults,
binds to `127.0.0.1`, rejects unrelated HTTP Host/Origin headers, and holds a
lifetime lock against duplicate launches. Stop it through the manager that
started it. This service is for trusted local agents, not remote network access.

## Paths, updates, and rollback

The default custom store is `<runtime home>/data/custom-clean-code-patterns.jsonl`.
Use repository namespaces for custom IDs. Explicit paths resolve on the server,
not in the client's working directory, and existing path restrictions remain.
Custom-store mutations hold a lock through index synchronization and rollback.

Stop the service before updating its files or rebuilding the index. The skill
installer holds startup and lifetime locks throughout file replacement,
dependency installation, and indexing, independent of the service port. It
overlays runtime files to retain user stores and refreshes the index without
resetting custom entries. Both historical defaults (`runtime/data` and `data`
under the runtime home) are merged into the shared `data` store. Conflicting
records with the same ID stop ingestion before changing either store; reconcile
those records and rerun installation. Legacy files remain available. Retain custom
records and the existing index; restart after upgrading and verify lookup/search.
To roll back a client, restore its previous configuration and restart the agent.
The original stdio command is still supported.
