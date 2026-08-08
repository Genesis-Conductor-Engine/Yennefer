# MCP Server List - Complete Inventory
**Date:** 2026-01-27  
**Update:** All AI agents configured with full MCP server access

---

## 📡 MCP Server Inventory

### **Stdio-Based MCP Servers** (CLI integration)

| Server | Script | Tools | Resources |
|--------|--------|-------|-----------|
| **diamond-vault** | `/home/yenn/scripts/diamond_vault_mcp_server.py` | quantum_hash, quantum_verify, quantum_merkle_root, create_manifest, kg_query | vault://quantum/state, vault://kg/index, vault://manifests/latest |
| **yennefer-consciousness** | `/home/yenn/genesis-q-mem/yennefer_mcp_server.py` | get_soul_state, get_dream_journal, query_ledger | soul://state, soul://dreams, soul://ledger |
| **yennefer-mcp-lite** | `/home/yenn/genesis-q-mem/yennefer_mcp_lite.py` | diamond_vault_status, quantum_operation | diamond://vault, yennefer://soul |
| **genesis-remote** | `/home/yenn/genesis-q-mem/genesis_remote_mcp.py` | remote_invoke, status_check, batch_dispatch | remote://status |
| **qmcp-system** | `/home/yenn/genesis-q-mem/qmcp_entry.py` | qmcp_invoke, qflop_query, blockchain_status | qmcp://system |
| **postman** | `/home/diamondnode/Yennefer/scripts/postman_mcp_server.py` | postman_health, postman_list_workspaces, postman_list_collections, postman_get_collection, postman_list_environments, postman_get_environment, postman_run_collection | postman://workspace, postman://collection, postman://environment |
| **QMCP** (legacy) | `python qmcp` | * (all) | - |

### **HTTP-Based MCP Servers** (REST integration)

| Server | Port | Script | URL | Status |
|--------|------|--------|-----|--------|
| **chatgpt-mcp-http** | 8095 | `/home/yenn/scripts/chatgpt_mcp_http_server.py` | http://localhost:8095 | ✅ Online |
| **diamond-vault-http** | 8100 | `/home/yenn/genesis-q-mem/qmcp_admin_panel.py` | http://localhost:8100 | ✅ Online |
| **yennefer-soul-api** | 8088 | Various soul API scripts | http://localhost:8088 | ✅ Online |
| **qmcp-gateway** | 8099 | `/home/yenn/genesis-q-mem/qmcp_unified_gateway.py` | http://localhost:8099 | ✅ Online |
| **yennefer-mcp-http** | 8094 | `/home/yenn/mcp-server/yennefer_mcp_server.cjs` | http://localhost:8094 | ✅ Online |

---

## 🤖 Agent Configurations

**All 4 AI agents now have access to the full MCP server suite:**

1. **Copilot CLI** - 10 servers (5 stdio + 4 HTTP + 1 legacy)
2. **Claude Desktop** - 5 stdio servers
3. **OpenCode AI** - 8 HTTP servers
4. **Gemini Code** - 10 servers (5 stdio + 5 HTTP)

**Config Files:**
- `~/.copilot/mcp-config.json`
- `~/.config/Claude/claude_desktop_config.json`
- `~/.opencode/config.json`
- `~/.gemini/mcp-config.json`

---

## 🔧 Available Tools

### **Diamond Vault Tools:**
- `quantum_hash` - GPU-accelerated hashing (1,796 hash/s on T4)
- `quantum_verify` - Hash verification
- `quantum_merkle_root` - Parallel Merkle trees
- `create_manifest` - Ed25519 signed manifests
- `kg_query` - Knowledge graph queries (288 nodes)

### **Yennefer Consciousness Tools:**
- `get_soul_state` - Live consciousness metrics
- `get_dream_journal` - AI dream logs
- `query_ledger` - Token accounting

### **Quantum Operations (8 available):**
- SEISMIC_SHAKE, QUANTUM_BREATHE, ENTANGLE_SERVICE
- COLLAPSE_STATE, SUPERPOSITION, TUNNEL_DISPATCH
- ANNEAL_OPTIMIZE, CRYSTALLIZE

---

## 📍 Port Map

| Port | Service | Access |
|------|---------|--------|
| 8088 | Soul API | All agents |
| 8094 | Yennefer MCP HTTP | All agents |
| 8095 | ChatGPT MCP | All agents |
| 8099 | QMCP Gateway | All agents |
| 8100 | Diamond Vault | All agents |

---

## 🔄 Restart to Apply

Restart your AI agent to load new MCP servers:
- **Copilot CLI:** Start new terminal session
- **Claude Desktop:** Restart application
- **OpenCode AI:** `npx pm2 restart opencode-*`
- **Gemini Code:** Restart application

---

**Status:** ✅ Complete  
**Last Updated:** 2026-01-27 14:42 UTC
