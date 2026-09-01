# User configuration

This directory is mounted into the container at `/app/conf` by `docker-compose.yml`.

The image entrypoint **requires** `conf/conf.yaml` and exits with an error without it:

```sh
cp ../config_templates/conf.default.yaml conf.yaml
```

Then edit `conf.yaml` — at minimum set your LLM backend and API key under
`character_config.agent_config`, and set `system_config.host` to `0.0.0.0`
so the server is reachable from outside the container.

`conf.yaml` is gitignored, so your keys are never committed.

The entrypoint also symlinks these in if present, letting you override them
without rebuilding the image:

- `model_dict.json`
- `live2d-models/`
- `characters/`
- `avatars/`
- `backgrounds/`
