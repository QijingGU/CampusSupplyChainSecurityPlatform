# Docker 傻瓜部署教程（推仓库 + 别人拉取使用）

本文说明：**如何把项目打成镜像、推到你自己的 Docker 仓库**，以及 **别人如何只拉镜像就跑完整服务**；并说明 **密钥不写进镜像、默认关闭需 API 的大模型研判**。

---

## 一、你需要准备什么

1. 已安装 **Docker Desktop**（Windows）或 Docker Engine（Linux），命令行能执行 `docker` / `docker compose`。
2. 一个 **镜像仓库账号**，任选其一：
   - **Docker Hub**：https://hub.docker.com 注册
   - **阿里云 ACR**、**腾讯云** 等私有仓库（公司常用）
3. 项目根目录即本仓库根目录（含 `docker-compose.yml`、`backend/`、`frontend/`）。

---

## 二、密钥安全原则（必读）

| 原则 | 说明 |
|------|------|
| **不要**把真实密钥写进 `Dockerfile` 或提交到 Git | 镜像里不应出现明文 Key。 |
| **运行时注入** | 用「环境变量」或「服务器上的 `.env` 文件」在 **启动容器时** 传入 `SECRET_KEY`、可选的 `LLM_API_KEY` 等。 |
| **本仓库的默认策略** | `docker-compose.yml` 中 **`IDS_AI_ANALYSIS` 默认为 `false`**：未配置大模型时，**不会**去调外部 LLM API，IDS 仍用**规则引擎**，避免无密钥时误配。 |
| **JWT 密钥** | 部署前务必把 `SECRET_KEY` 改成随机长字符串（见下文命令）。 |

---

## 三、第一次：在本机构建并推送到你的仓库

### 1. 登录镜像仓库

**Docker Hub：**

```powershell
docker login
```

**阿里云（示例）：**

```powershell
docker login registry.cn-hangzhou.aliyuncs.com
```

### 2. 在网页上创建两个空仓库（Docker Hub）

名称需与下面脚本一致（或你改脚本里的镜像名）：

- `你的用户名/campus-supply-backend`
- `你的用户名/campus-supply-frontend`

### 3. 一键构建并推送（项目根目录）

把 `你的DockerHub用户名` 换成你的 Hub 用户名；私有仓库用 `-Registry`（见脚本内注释）。

```powershell
cd D:\04_Project\CampusSupplyChainSecurityPlatform
.\scripts\push-docker.ps1 -DockerUser "你的DockerHub用户名"
```

Linux / macOS 可用：

```bash
export DOCKER_USER=你的DockerHub用户名
export TAG=latest
./scripts/push-docker.sh
```

推送成功后，别人即可使用：

- `你的DockerHub用户名/campus-supply-backend:latest`
- `你的DockerHub用户名/campus-supply-frontend:latest`

---

## 四、别人（或你的服务器）如何只拉镜像就跑

**不要在公网仓库里写密钥。** 对方在服务器上新建一个文件夹，例如 `campus-scsp`，放入两个文件。

### 1. 新建 `.env`（不要提交到 Git）

复制下面内容，**务必修改 `SECRET_KEY`**，其它可按需改：

```env
# 镜像名（改成你推送时用的用户名/命名空间）
BACKEND_IMAGE=你的DockerHub用户名/campus-supply-backend:latest
FRONTEND_IMAGE=你的DockerHub用户名/campus-supply-frontend:latest

# JWT 必改：随机字符串（示例生成一条）
# PowerShell: 无 openssl 时可网上找随机串，或：
#   python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=这里换成至少32字节的随机字符串

# 默认关闭大模型 API 研判（无 LLM 密钥时保持 false 即可）
IDS_AI_ANALYSIS=false

# 若以后要接大模型，再改为 true，并填写下面几项（不要泄露给他人）
# LLM_PROVIDER=ollama
# LLM_BASE_URL=http://宿主机可访问的ollama地址:11434
# LLM_API_KEY=
# LLM_MODEL=qwen2:7b
```

### 2. 新建 `docker-compose.yml`（只拉镜像、不 build）

```yaml
services:
  backend:
    image: ${BACKEND_IMAGE}
    volumes:
      - supply_chain_data:/data
    environment:
      - DATABASE_URL=sqlite:////data/supply_chain.db
      - SECRET_KEY=${SECRET_KEY}
      - IDS_AI_ANALYSIS=${IDS_AI_ANALYSIS:-false}
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - LLM_BASE_URL=${LLM_BASE_URL:-}
      - LLM_API_KEY=${LLM_API_KEY:-}
      - LLM_MODEL=${LLM_MODEL:-qwen2:7b}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8166/api/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 15s

  frontend:
    image: ${FRONTEND_IMAGE}
    ports:
      - "8080:8080"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  supply_chain_data:
```

### 3. 启动

```powershell
docker compose pull
docker compose up -d
```

浏览器访问：**`http://服务器IP:8080`**（演示账号见项目 `init_db`，默认密码常见为 `123456`，以你项目说明为准）。

---

## 五、本仓库根目录 `docker-compose.yml` 与推送脚本的关系

- **开发/自己构建**：根目录 `docker compose up -d --build` 会用本地 `backend/`、`frontend/` 构建镜像。
- **推送**：`push-docker.ps1` 会设置 `BACKEND_IMAGE` / `FRONTEND_IMAGE` 后 `build` + `push`。
- **环境变量模板**：见 **`docker.env.example`**（镜像名）；密钥与 LLM 说明可结合根目录 **`.env` 示例**（复制为 `.env` 后仅本机使用，勿提交）。

根目录 `docker-compose.yml` 已支持通过环境变量传入 `SECRET_KEY`、`IDS_AI_ANALYSIS`、LLM 相关变量，**与镜像分离，密钥不会打进镜像层**。

---

## 六、常见问题

**Q：别人能看到我镜像里的 API Key 吗？**  
A：只要你**不要**把 Key 写进 Dockerfile / 不要提交含真 Key 的文件，镜像里就没有。运行时只在服务器 `.env` 或 `docker compose` 环境里存在。

**Q：不想用大模型，只想演示 IDS 规则？**  
A：保持 **`IDS_AI_ANALYSIS=false`**（默认），不配 `LLM_*` 即可。

**Q：端口想改？**  
A：改 `docker-compose` 里 `frontend` 的 `"8080:8080"` 左侧宿主机端口，例如 `"9000:8080"`。

---

## 七、命令速查

| 目的 | 命令 |
|------|------|
| 本机构建并启动 | `docker compose up -d --build` |
| 推送到你的仓库 | `.\scripts\push-docker.ps1 -DockerUser "用户名"` |
| 仅拉镜像并启动 | `docker compose pull && docker compose up -d` |
| 停止 | `docker compose down` |

完成以上步骤后，即可实现：**镜像在仓库里共享，别人拉取后配合自己的 `.env` 跑全套服务，且密钥不随镜像泄露。**
