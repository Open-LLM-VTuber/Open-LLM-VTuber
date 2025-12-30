# 🐳 Open-LLM-VTuber Docker Build Guide

## About Our Docker Team
We have established the [openllmvtuber team](https://hub.docker.com/orgs/openllmvtuber/members) on Docker Hub.  
The Docker images are currently maintained by [@Harry_Y](https://github.com/Harry-Yu-Shuhang).  

## 📁 Build Context
Connect to your Linux server and git clone the repository:
```
git clone https://github.com/Open-LLM-VTuber/Open-LLM-VTuber.git
```

Enter the Docker build directory:
```
cd dockerfiles
```

---

## Preparations
```
chmod +x setup_config_en.sh
sudo ./setup_config_en.sh
```

---

## 🏗️ Build (Local Multi-Arch Image)

> ⚠️ Note: `--load` only loads the current host architecture (e.g., amd64) into your local Docker.  
> To push a full multi-arch image to Docker Hub, use the `--push` command below.

> ⚠️ Note: If you need to perform multi-platform builds, please refer to the [official Docker multi-platform build documentation](https://docs.docker.com/build/building/multi-platform/) and adjust your configuration accordingly.
> All the following commands are configured for multi-platform builds; if you want to build for a single platform, simply modify the `--platform` parameter.

```
docker buildx build --platform linux/amd64,linux/arm64 -t <your_dockerhub_username>/<your_image_name>:latest -f dockerfile ../ --load
```

Replace:
- `<your_dockerhub_username>` → your Docker Hub username or organization name  
- `<your_image_name>` → your preferred image name  

Example：
```
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:localtest -f dockerfile ../ --load
```

And then start with `docker compose`
```
docker-compose up -d
```
---

## ☁️ Push (Only for Docker Hub Members)
```
docker push openllmvtuber/open-llm-vtuber:latest
```

---

## 🚀 Build and Push Together (Recommended, only for Docker Hub Members)
> This builds for both amd64 and arm64 and pushes to Docker Hub directly.
```
cd dockerfiles
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --push
```

---

## 🔍 Verify the Multi-Arch Build
After pushing, verify architectures:
```
docker buildx imagetools inspect openllmvtuber/open-llm-vtuber:latest
```

Expected output includes both:
```
linux/amd64
linux/arm64
```

---

## Clear all data
```
docker system prune -a --volumes
```
