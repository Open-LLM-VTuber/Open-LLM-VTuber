# PostgreSQL 与 Redis

本地服务：`docker compose --env-file infra/.env -f infra/compose.yaml up -d --wait`

运行应用：`uv run python scripts/run_with_services.py`。直播可加 `VTUBER_LIVE_MODE=1`。infra/.env 是本机随机密码文件，不提交版本库。

PostgreSQL 保存结构化记忆（偏好、事实、进度、待办、经历），提供连接池、事务、版本替换、有效期和停止召回。私人/直播记忆以 scope 前缀隔离，角色再按 conf_uid 隔离。目前没有多用户账户隔离。local_memory 工具可列出、更新和遗忘记忆；遗忘为停止召回，历史版本仍在数据库中。模型写入依据仍需用户检查，不等同已完成事实核验。

Redis 是可丢失的目录缓存，TTL 2 秒；故障时跳过缓存直接扫描。直播资源白名单不缓存。Redis 尚未承担任务队列。多个安装共享 Redis 时须使用不同 Redis DB，避免目录混用。

未配置 VTUBER_DATABASE_URL 时继续使用本地 SQLite。启用 PostgreSQL 不会自动搬迁 SQLite 或聊天 JSON，聊天历史 RAG 仍读取 JSON。数据库不可用时记忆访问报错，不悄悄切换数据库以免产生两套冲突记忆。

Kafka 暂不加入：当前没有独立部署的生产者/消费者和大量事件回放需求。未来将书籍索引、音视频转写拆成 worker 后，再选 Redis Streams 或 Kafka，并实现幂等、重试、死信与监控。

停止服务：`docker compose --env-file infra/.env -f infra/compose.yaml stop`。PostgreSQL 数据留在 Docker 卷中。
