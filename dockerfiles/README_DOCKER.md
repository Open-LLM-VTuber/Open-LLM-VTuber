# Build

```bash
cd dockerfiles
```
You should user your user name instead of openllmvtuber and your image name instead of open-llm-vtuber:latest
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --load
```

# Push (only for docker hub organization members)
```bash
docker push openllmvtuber/open-llm-vtuber:latest
```

# Build and Push
```bash
cd dockerfiles
```
```bash
docker buildx build --platform linux/amd64,linux/arm64 -t openllmvtuber/open-llm-vtuber:latest -f dockerfile ../ --push
```