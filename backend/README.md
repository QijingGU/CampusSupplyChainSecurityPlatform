# 校园物资供应链 - 后端 API

## 技术栈

- FastAPI
- SQLAlchemy + SQLite（开发）/ PostgreSQL（生产）
- JWT 认证
- Pydantic

## 快速启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库（创建表 + 演示数据）
python init_db.py

# 3. 启动服务
uvicorn app.main:app --reload --host 127.0.0.1 --port 8166
```

## 演示账号

| 用户名     | 密码   | 角色   |
|------------|--------|--------|
| admin      | 123456 | 管理员 |
| procurement| 123456 | 采购员 |
| supplier1  | 123456 | 供应商 |
| teacher1   | 123456 | 教师   |

## API 文档

启动后访问：http://localhost:8166/docs

## 前端代理

前端 `vite.config.ts` 已配置代理到 `http://127.0.0.1:8166`。
