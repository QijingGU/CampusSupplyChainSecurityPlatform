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
