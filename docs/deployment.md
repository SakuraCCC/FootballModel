# 部署指南

## 本地开发

复制 `.env.example` 为 `.env`，填入数据源和可选 LLM 配置，然后执行：

```bash
docker compose up --build
```

本地 API 为 `http://localhost:8000`，健康检查为 `/health`、`/database-health` 和 `/worker-health`。

## VPS 部署

1. 在 VPS 安装 Docker Engine 与 Compose 插件，克隆仓库。
2. 复制 `.env.production.example` 为 `.env.production`，为 PostgreSQL 密码、API-Football Key 与 LLM Key 填入真实值；该文件不得提交。
3. 启动生产栈：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

Nginx 对外暴露 `NGINX_PORT`。API、worker、beat、PostgreSQL、Redis 和 Nginx 运行在同一 Compose 网络；海报目录以共享 volume 提供给 API 和 Nginx。

## 数据库迁移与备份

API 容器启动时执行 `alembic upgrade head`。手动执行：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production exec api alembic upgrade head
```

备份前导出生产环境变量，再运行：

```bash
set -a && . ./.env.production && set +a
./scripts/backup_postgres.sh
```

将该脚本放入 VPS 的受控定时任务，并把备份同步到独立、加密的位置。

## 自动化与交付

Celery Beat 每日扫描 24–72 小时内的已入库比赛，依次执行预测、报告和海报任务。它不会登录或发布到小红书等平台。通过 `GET /api/v1/reports/{report_id}` 复制小红书文案，通过 `GET /api/v1/posters/{poster_id}` 获得 PNG URL；部署后 URL 可直接在浏览器打开或下载。
