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

## Phase 9 生产验收、恢复与日常运行

1. 购买 VPS 后安装 Docker Engine 与 Compose，克隆仓库并仅在服务器保存 `.env.production`。
2. 配置 PostgreSQL、Redis、`API_FOOTBALL_KEY`，以及需要生成报告时的 `LLM_BASE_URL`、`LLM_API_KEY`、`LLM_MODEL`；不要提交该文件。
3. 执行 `docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build`。API 容器会运行 `alembic upgrade head`；也可手动执行该命令确认迁移。
4. 访问 `/health`、`/database-health`、`/worker-health` 和 `/scheduler-health`。Beat 至少运行一次后，scheduler health 才会是 ok。
5. 在 `/api/v1/providers/status` 检查 API-Football；未配置 key 的 `unavailable` 是预期安全状态。配置真实 key 后再执行一次受控的比赛同步。
6. 使用 `/api/v1/dashboard/admin` 查看只读运营概览；报告正文可从报告 API 复制，PNG 可从海报 API 的 `image_url` 下载。系统没有第三方平台自动发布功能。
7. 使用 `scripts/backup_postgres.sh` 备份。恢复时先停写入服务，再用受保护的 `pg_restore` 恢复到目标数据库，运行 `alembic upgrade head`，最后重启 stack 并复查四个健康端点。
