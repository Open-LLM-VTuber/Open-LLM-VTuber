# 🐳 Open-LLM-VTuber Docker 构建指南（中文）

## 📁 构建目录
进入 Docker 构建目录：
```
cd dockerfiles
```

---

## 🏗️ 本地多架构构建

> ⚠️ 注意：`--load` 只会将当前主机架构（如 amd64）加载到本地。  
> 若要推送完整的多架构镜像，请使用下方的 `--push`。

```
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t <你的DockerHub用户名>/<镜像名>:latest \
  -f dockerfile ../ --load
```

示例：
```
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --load
```

---

## ☁️ 推送镜像（仅组织成员）
```
docker push openllmvtuber/open-llm-vtuber:latest
```

---

## 🚀 构建并推送（推荐）
> 一步完成 amd64 + arm64 架构构建与推送。
```
cd dockerfiles
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t openllmvtuber/open-llm-vtuber:latest \
  -f dockerfile ../ --push
```

---

## 🔍 验证多架构镜像
推送完成后验证：
```
docker buildx imagetools inspect openllmvtuber/open-llm-vtuber:latest
```

期望输出中应包含：
```
linux/amd64
linux/arm64
```
