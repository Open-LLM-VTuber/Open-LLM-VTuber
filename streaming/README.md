# Streaming Utilities

This folder contains helper scripts for livestreaming to multiple platforms.

## multistream.py

Use `multistream.py` to forward a single video input to multiple RTMP
endpoints using `ffmpeg`. This can be used to save resources when streaming to
several services simultaneously.

### Example

```bash
python multistream.py video.mp4 --rtmp rtmp://a.example/live/streamkey \
    rtmp://b.example/app/key
```

`ffmpeg` must be installed and available on your `PATH`.
