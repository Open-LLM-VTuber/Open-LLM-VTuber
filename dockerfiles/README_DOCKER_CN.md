# 🐳 Open-LLM-VTuber Docker 构建指南

## 关于我们的docker团队
我们在 docker hub 成立了[openllmvtuber团队](https://hub.docker.com/orgs/openllmvtuber/members)，目前docker镜像由[@Harry_Y](https://github.com/Harry-Yu-Shuhang)维护。

## 📁 进入构建目录
连接到您的Linux服务器并git clone
```
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git
```

然后进入 Docker 构建目录：
```
cd dockerfiles
```

---

## 准备工作
```
chmod +x setup_config_cn.sh
sudo ./setup_config_cn.sh
```

---

## 🏗️ 本地多架构构建

> ⚠️ 注意：`--load` 只会将当前主机架构（如 amd64）加载到本地 Docker。  
> 若要推送完整的多架构镜像到 Docker Hub，请使用下方的 `--push` 命令。

> ⚠️ 注意: 如果需要多平台构建，请参考[docker官方的多平台构建文档](https://docs.docker.com/build/building/multi-platform/)，修改配置。以下命令都是多平台的，如果单平台构建，修改--platform参数即可。

```
docker buildx build --platform linux/amd64,linux/arm64 -t <你的DockerHub用户名>/<镜像名>:latest -f dockerfile ../ --load
```

请替换以下内容：
- `<你的DockerHub用户名>` → 你的 Docker Hub 用户名或组织名  
- `<镜像名>` → 你想使用的镜像名称  

示例：
```
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:1.2.1 -f dockerfile ../ --load
```

然后用docker compose启动

```
docker-compose up -d
```

---

## ☁️ 推送镜像（仅限 Docker Hub 组织成员）
```
docker push openllmvtuber/open-llm-vtuber:1.2.1
```

---

## 🚀 一步构建并推送（推荐, 可以打包跨平台镜像，仅限 Docker Hub 组织成员）
> 该命令同时构建 amd64 与 arm64 架构镜像，并直接推送到 Docker Hub。
```
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:1.2.1 -f dockerfile ../ --push
```
建议推送到版本号的tag，用户只需拉取latest。

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

---

## 清空数据
```
docker system prune -a --volumes
```
