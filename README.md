# 校园物资供应链安全健康监测平台

采购 → 仓储 → 配送 → 溯源 → 预警 → AI 智能体

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue 3 + Vite + Element Plus + Pinia + TypeScript |
| 后端 | FastAPI + SQLAlchemy + JWT |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 智能体 | 规则引擎 + 可选 LLM（Ollama/OpenAI） |

## 快速启动

### 1. 后端

```bash
cd backend
pip install -r requirements.txt
python init_db.py
uvicorn app.main:app --reload --host 127.0.0.1 --port 8166
```

### 2. 前端

```bash
cd frontend
npm install
npm run dev
```

### 3. 访问

- 前端：http://localhost:5173
- 后端文档：http://localhost:8166/docs

### 演示账号

| 用户名 | 密码 | 角色 |
|--------|------|------|
| logistics_admin | 123456 | 后勤管理员 |
| warehouse_procurement | 123456 | 仓储采购员 |
| campus_supplier | 123456 | 校园合作供应商 |
| counselor_teacher | 123456 | 辅导员教师 |

角色职责与权限见：`docs/角色与权限交互矩阵.md`

### AI 智能体

- 输入「现在什么物资可能短缺？需要补货吗？」体验完整闭环
- 可选：配置 `LLM_BASE_URL` 启用 Ollama，接入真实大模型

- IDS 演示启动时可直接选择 `deepseek` / `kimi` 并输入 API Key，系统会自动补全连接地址和默认模型名

## Windows Quick Start

Run `start-ids-dev.bat` from the repository root, or execute:

```powershell
powershell -ExecutionPolicy Bypass -File .\start-ids-dev.ps1
```

The quick-start launcher opens backend and frontend in separate windows,
auto-selects backend port `8166` or `8167`, initializes
`backend/supply_chain.db` if needed, asks the AI launch choice before the
backend window starts, and starts the frontend on `5173` or `5174`.

For local browser development, the frontend now auto-probes backend
`8166/8167` directly even when Vite runs on `5173/5174`, so the stack still
comes up when the preferred port is occupied.

When quick start launches the stack it also records the wrapper PowerShell PIDs
into `.ids-dev-processes.json`, so the stop script can close the exact windows
and their child processes instead of guessing by port only.

For the IDS upload audit flow:

- no API key configured at startup => static audit mode
- configure credentials at startup => AI mode becomes active
- supported providers for local demo are `deepseek` and `kimi`
- in quick start you only need to choose `deepseek` or `kimi` and paste the API key;
  the base URL and default model name are auto-filled
- to stop the quick-started stack cleanly, run `stop-ids-dev.bat` or:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop-ids-dev.ps1
```

## IDS Security Center

The security-center upload, IDS, log-audit, sandbox, and situation pages now drive real IDS work instead of demo-only copy.

- Public uploads run the AI audit gate in `backend/app/api/upload.py`. Safe files are stored under `uploads/accepted`, while review/quarantine verdicts keep the file in `quarantine_uploads` plus a JSON audit report in `upload_reports` that feeds the UI.
- The public upload page now shares the same dynamic dev-time backend resolution as the authenticated frontend API client, so a Vite session on `5174` can post directly to the live `8167/8166` backend instead of falling back to a stale `/api` proxy target.
- The public upload page now keeps a single consistent final state for each request: released, quarantined, or rejected. Closing the quarantine dialog no longer rewrites the same request into a fake “network error”.
- `/security/ids` now stays on real incidents, trusted-source sync state, package activation state, and upload evidence. Event reports include `Upload Audit Trace`, and upload-gated incidents can jump directly back into the matching sandbox report.
- Suspicious samples show up in `/security/sandbox` via `GET /api/upload/quarantine`, and `POST /api/upload/quarantine/analyze` reruns the real analysis on the persisted file so the drawer displays the verdict, risk, confidence, SHA-256, the indicator list, and the same persisted report after refresh.
- `/security/log-audit` is the dedicated IDS audit trail. It links upload gate actions, sandbox actions, source sync history, and incident follow-up into one traceable review surface.
- Startup now bootstraps the bundled `suricata-web-prod` manifest plus rule artifact into the IDS source/package registry, and that bundle is generated from the official ET Open Suricata archive via `backend/app/data/ids_source_sync/sync_suricata_web_prod.py`.
- The request-side runtime matcher now treats activated trusted `web` packages as the real static interception source. The bundled ET Open subset currently validates `.env` disclosure probes, cookie-based `UNION SELECT`, `${jndi:ldap://...}` log4j payloads, XSS probes such as `/proxy.php?url=<script>...`, and path-traversal/file-disclosure requests such as `fetchLogFiles` / `../`.
- Matching requests persist detector provenance, matched-rule detail, rule id/name/version, and a sanitized `Attack Packet` view, then return real HTTP `403` responses when the ET Open rule weight crosses `IDS_BLOCK_THRESHOLD`.
- Blocked request events can run optional AI analysis when AI is configured. The event detail/report surface now separates `Matched Static Rules`, `Attack Packet`, `Decision Source`, and AI analysis mode instead of presenting one blended demo summary.
- `system_admin` now receives an admin-only global high-risk IDS popup whenever a new blocked, unarchived event scores `>= 80`, including upload quarantine incidents. Existing backlog is baselined when the admin page first opens, each new event is shown once, queued alerts advance immediately after the current popup closes, the popup watermark now survives browser refreshes while also recovering correctly after local database resets or `init_db.py` reinitialization, the frontend now persists the authenticated user profile and rehydrates it on startup so a browser refresh does not silently disable admin-only IDS polling, `/security/ids` now includes an admin-only warning-sound panel for enable/disable, volume, custom audio import, test playback, and reset-to-default, and if the operator is already on `/security/ids` the popup action focuses the current event in-place instead of changing route or forcing a new report run. Non-admin roles still do not receive the popup.
- Sandbox reports now explain why a file was held, which static indicators matched, whether the decision came from static rules or `llm_assisted` mode, which IDS event it linked to, and what follow-up actions the reviewer should take.
- The sandbox analysis produces IDS metrics that the situation page consumes through `GET /api/ids/situation`, so `/security/situation` renders counters, recent incident cards, and IP-derived map arcs instead of random animation data.
- IDS source operations on `/security/ids` now use a real local-manifest sync path instead of the old metadata-only stub. Each sync-backed source stores `sync_endpoint`, and `POST /api/ids/sources/{id}/sync` reads the bundled manifest/rule artifact, computes version, rule count, artifact path, and SHA-256, then records both Sync Audit and package-intake history for the UI.
- Activated `web` source packages now feed the runtime matcher in `backend/app/services/ids_engine.py`. Matching requests preserve `detector_name=source_key`, `source_version=package_version`, and `source_rule_id=sid` from the activated ET Open package.
- The repo includes a deterministic fixture for local IDS sync review at `backend/app/data/ids_source_sync/suricata-web-prod.manifest.json` and `backend/app/data/ids_source_sync/suricata-web-prod.rules`.
- These flows were validated on 2026-04-05 by uploading `tmp/codex-note.txt` (pass, released to the public path) and `tmp/codex-webshell.php` (quarantined, visible in the sandbox, and reflected as a real incident on the situation page).
  On 2026-04-06 the same security-center slice was extended so `/security/ids` shows the sync endpoint, imported package version, rule-count/hash summary, and Sync Audit history for `suricata-web-prod`.
  On 2026-04-07 the bootstrapped `suricata-web-prod` package was regenerated from the official ET Open archive and revalidated at runtime through request probes such as `GET /.env`, cookie-based `UNION SELECT`, `GET /login?user=${jndi:ldap://...}`, and XSS/path-traversal payloads, all of which now return `403` with visible matched-rule and attack-packet data.
  On 2026-04-08 the admin-only popup flow was revalidated again with two new quarantined upload incidents: `/security/ids` showed event `#117`, the popup played the imported custom audio, the in-page focus action kept the URL on `/security/ids`, opened the event detail drawer instead of forcing a report route, and the next queued popup for event `#116` appeared immediately with a second audio alert. `logistics_admin` still remains outside the popup path.
