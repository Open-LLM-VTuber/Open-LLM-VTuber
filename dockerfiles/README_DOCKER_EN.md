# 🐳 Open-LLM-VTuber Docker Build Guide

:::note About Our Docker Team
We have established the [openllmvtuber team](https://hub.docker.com/orgs/openllmvtuber/members) on Docker Hub.  
The Docker images are currently maintained by [@Harry_Y](https://github.com/Harry-Yu-Shuhang).  
:::

## 📁 Build Context
Enter the Docker build directory:
```
cd dockerfiles
```

---

## 🏗️ Build (Local Multi-Arch Image)

> ⚠️ Note: `--load` only loads the current host architecture (e.g., amd64) into your local Docker.  
> To push a full multi-arch image to Docker Hub, use the `--push` command below.

```
docker buildx build --platform linux/amd64,linux/arm64 -t <your_dockerhub_username>/<your_image_name>:latest -f dockerfile ../ --load
```

Replace:
- `<your_dockerhub_username>` → your Docker Hub username or organization name  
- `<your_image_name>` → your preferred image name  

Example:
```
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --load
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
