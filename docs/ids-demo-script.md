# IDS Security Center Demo Script

Spec reference: `specs/010-ids-strict-ai-log-audit/`

## Demo Goal

Show one real operator chain:

1. 匿名上传先经过审计，再决定是否放行。
2. 正常文件可以被放行，恶意文件会被扣留到沙箱。
3. 高危事件会进入 IDS，并触发管理员专属弹窗与预警音。
4. IDS、沙箱、日志审计三条线可以互相跳转并交叉核验。
5. 静态规则库会真实拦截恶意请求并返回 `403`。
6. 配置模型密钥后，可以对拦截事件和沙箱样本发起真实 AI 研判。

## Demo Setup

- Windows 推荐直接在仓库根目录运行 `start-ids-dev.bat`
- 或运行 `powershell -ExecutionPolicy Bypass -File .\start-ids-dev.ps1`
- 快捷启动会：
  - 分别打开后端和前端窗口
  - 自动选择后端端口 `8166` 或 `8167`
  - 自动选择前端端口 `5173` 或 `5174`
  - 启动前询问是否启用 AI 模式
  - 只让演示者选择 `deepseek` 或 `kimi` 并输入 API Key，其余 base URL 和默认模型名自动补全
- 停止演示时运行 `stop-ids-dev.bat`

## Required Tabs

- `/upload`
- `/security/ids`
- `/security/sandbox`
- `/security/log-audit`
- `/security/situation`

## Demo Materials

- 正常文件：`tmp/codex-note.txt`
- 恶意文件：`tmp/codex-webshell.php`
- 可选自定义预警音：任意短音频，例如 `output/ids-alert-test.wav`
- 管理员账号：`system_admin / 123456`

## Important Prep Note

- 先用 `system_admin` 打开 `/security/ids`
- 如果要演示自定义预警音，先在页面里的“管理员预警声音”面板导入音频并点一次“试听当前声音”
- 这一页首次打开时会把当前已有的高危未归档事件记成基线，不会把历史 backlog 当成新攻击反复弹窗
- 之后只有新产生的高危事件才会触发管理员弹窗

## Scene 0 - Choose Static Or AI Mode

**Action**

- 启动快捷脚本
- 观察脚本在启动前询问是否启用 AI
- 如果选择启用，选择 `deepseek` 或 `kimi` 并输入 API Key
- 如果不启用，直接以静态模式启动

**What To Say**

“这里不是假 AI。没配密钥时，系统走静态审计模式；配了密钥后，系统才会启用真实 AI 研判。两种模式都会明确写在结果里，不会混着说。”

**Expected Result**

- `/api/health` 能看出当前是否启用 AI
- 上传、IDS 事件、沙箱报告里都能看到当前模式是 `static_only` 或 `llm_assisted`

## Scene 1 - Arm The Admin Alert Flow

**Action**

- 登录 `system_admin`
- 进入 `/security/ids`
- 指给观众看管理员专属的“管理员预警声音”面板
- 演示：
  - 开关声音
  - 调整音量
  - 导入自定义音频
  - 点击“试听当前声音”

**What To Say**

“管理员现在不仅能收到高危事件弹窗，还能自定义预警音。这个声音不是写死的，每次新的高危事件弹出时都会真实播放。”

**Expected Result**

- 只有 `system_admin` 能看到这个声音面板
- 自定义音频可以导入、保存、试听、恢复默认音
- 当前页建立好弹窗基线后，接下来只对新攻击弹一次

## Scene 2 - Upload A Benign File

**Action**

- 打开 `/upload`
- 上传 `tmp/codex-note.txt`

**What To Say**

“先看正常链路。系统不是一刀切拦所有文件，低风险文件会被正常放行。”

**Expected Result**

- 页面显示放行结果
- 返回公开访问地址
- 文件不会出现在沙箱里
- 不会触发管理员高危弹窗

## Scene 3 - Upload A Malicious File And Trigger Admin Alert

**Action**

- 再上传 `tmp/codex-webshell.php`
- 保持管理员的 `/security/ids` 标签页处于打开状态

**What To Say**

“这次样本包含明显的 WebShell 信号，所以它不会被公开放行，而是直接被扣留到沙箱，并同步生成真实 IDS 事件。”

**Expected Result**

- 上传页显示文件已被扣留或隔离
- 不会再出现同一次上传既被扣留又额外冒出假网络错误面板的情况
- `system_admin` 会收到一次高危弹窗，并播放预警音
- 非管理员账号不会收到这个弹窗
- 如果当前管理员已经在 `/security/ids`
  - 弹窗动作按钮应显示为 `定位当前事件`
  - 点击后留在 `/security/ids`
  - 只在页内打开该事件详情
  - 不再跳到 `?report=1`
  - 不会因此重复触发报告生成或再次分析
- 如果连续制造两次高危攻击
  - 每个新事件各弹一次
  - 关闭或定位当前弹窗后，下一个队列事件立即出现
  - 第二个弹窗会再次播放预警音

## Scene 4 - Show The Sandbox Report

**Action**

- 切换到 `/security/sandbox`
- 找到刚刚被扣留的样本
- 打开报告，或点击“重新分析”

**What To Say**

“这里读的是后端真实落盘的样本和报告，不是前端临时拼出来的演示文本。为什么被拦、命中了什么、风险等级是多少，都能在这里看到。”

**Expected Result**

- 样本出现在沙箱列表中
- 报告里能看到：
  - 风险等级
  - 置信度
  - SHA-256
  - 命中的静态指标
  - 持有原因
  - 当前分析模式
  - 推荐处置动作
- 如果启用了 AI，可继续发起真实 AI 分析

## Scene 5 - Show The IDS Event Detail

**Action**

- 回到 `/security/ids`
- 打开刚才那条上传关联事件

**What To Say**

“现在 IDS 不是只有一条告警标题。这里能直接看到攻击类型、命中证据、上传审计链路、攻击包和规则来源，事件与沙箱是串起来的。”

**Expected Result**

- 事件详情里能看到上传证据链
- 上传类事件能直接跳回对应沙箱报告
- 如果事件来自请求拦截，还能看到：
  - `Matched Static Rules`
  - `Attack Packet`
  - `Decision Source`
  - 可选 AI 研判结果

## Scene 6 - Show The Log Audit Trail

**Action**

- 打开 `/security/log-audit`
- 用 `ids_upload_quarantine`、`ids_upload_release`、`ids_sandbox_analyze` 或 `saved_as` 搜索

**What To Say**

“这里是 IDS 独立日志审计面。上传放行、上传扣留、沙箱分析、规则源同步、事件处置，都会留下真实审计记录。”

**Expected Result**

- 能查到刚才上传和沙箱分析对应的操作日志
- 能看到谁做的、做了什么、什么时候做的
- 日志和 IDS 事件、沙箱样本能互相对上

## Scene 7 - Explain The Situation Screen Boundary

**Action**

- 打开 `/security/situation`

**What To Say**

“这个页面还是偏展示和态势观察，它不是这轮收口的重点。真正落地的内容在上传、IDS、沙箱、日志审计这几条线里。”

**Expected Result**

- 能看到真实事件驱动的计数和近期攻击卡片
- 演示时明确说明该页是观察视图，不是这轮验收重点

## Extension A - Show Static Rule Blocking With 403

### Action

- 在终端执行下面任意一个探针：
  - `curl "http://127.0.0.1:8166/.env"`
  - `curl "http://127.0.0.1:8166/login?user=%24%7Bjndi%3Aldap%3A%2F%2Fdemo%2Fa%7D"`
  - `curl --path-as-is "http://127.0.0.1:8166/proxy.php?url=%3Cscript%3Ealert(1)%3C%2Fscript%3E"`
- 如果本机后端跑在 `8167`，把端口替换成 `8167`
- 然后回到 `/security/ids` 打开最新事件

### What To Say

“这里不是自己重写一套玩具规则，而是接入了实际启用的静态规则包。恶意请求会被真实拦截成 `403`，并把命中的规则、攻击包和处置依据完整记下来。”

### Expected Result

- 请求直接返回 `403`
- 最新 IDS 事件里能看到：
  - `detector_name=suricata-web-prod`
  - 匹配到的规则 ID 或规则名
  - `Attack Packet`
  - 静态规则命中链
- 如果配置了 AI，还可以在该事件上继续发起真实 AI 研判

## Extension B - Show Real Source Sync

### Action

- 留在 `/security/ids`
- 找到 `Suricata Web Prod`
- 点击同步或打开历史

### What To Say

“这里不是元数据摆设。规则源同步会真正读取本地 manifest 和规则文件，算出版本、规则条数、文件大小和 SHA-256，并留下同步审计。”

### Expected Result

- 源行里能看到 `sync_endpoint`
- 同步结果里能看到版本、规则数、哈希摘要
- 历史里能看到 `Sync Audit`

## Backup Talking Points

- 没配模型密钥时，系统仍然可演示静态规则、文件拦截、403 阻断、日志审计和事件闭环
- 配了模型密钥后，再演示 IDS 事件 AI 研判和沙箱 AI 分析
- 管理员弹窗是管理员专属能力，不会广播给普通角色
- 弹窗不是定时轮播旧数据，而是只对新事件触发
- 如果已经在 `/security/ids`，弹窗动作是页内定位，不是重复跳转和重复分析
- 自定义预警音是持久化的，刷新页面后仍然保留
