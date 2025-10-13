# 🐳 Open-LLM-VTuber Docker 构建指南

## 关于我们的docker团队
我们在 docker hub 成立了[openllmvtuber团队](https://hub.docker.com/orgs/openllmvtuber/members)，目前docker镜像由[@Harry_Y](https://github.com/Harry-Yu-Shuhang)维护。

## 📁 构建目录
进入 Docker 构建目录：
```
cd dockerfiles
```

---

## 🏗️ 本地多架构构建

> ⚠️ 注意：`--load` 只会将当前主机架构（如 amd64）加载到本地 Docker。  
> 若要推送完整的多架构镜像到 Docker Hub，请使用下方的 `--push` 命令。

```
docker buildx build --platform linux/amd64,linux/arm64 -t <你的DockerHub用户名>/<镜像名>:latest -f dockerfile ../ --load
```

请替换以下内容：
- `<你的DockerHub用户名>` → 你的 Docker Hub 用户名或组织名  
- `<镜像名>` → 你想使用的镜像名称  

示例：
```
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --load
```

---

## ☁️ 推送镜像（仅限 Docker Hub 组织成员）
```
docker push openllmvtuber/open-llm-vtuber:latest
```

---

## 🚀 一步构建并推送（推荐, 仅限 Docker Hub 组织成员）
> 该命令同时构建 amd64 与 arm64 架构镜像，并直接推送到 Docker Hub。
```
cd dockerfiles
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --push
```

---

## 🔍 验证多架构镜像
推送完成后验证镜像架构：
```
docker buildx imagetools inspect openllmvtuber/open-llm-vtuber:latest
```

期望输出中应包含：
```
linux/amd64
linux/arm64
```
