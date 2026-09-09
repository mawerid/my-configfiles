# Deep research OpenShell image

Uses `nvcr.io/nvidia/pytorch:26.08-py3` (Ubuntu 24.04, Python 3.12,
CUDA 13.4.1) for both architectures:

| Host | Image | Compute |
| --- | --- | --- |
| Ubuntu AMD64 + NVIDIA | `deep-research:cuda` | GPU |
| macOS M4 / Linux ARM64 | `deep-research:cpu` | CPU |

The image includes the C++/ROS tools, OpenCV, Ceres, Python research tools,
Codex, Claude Code, and the OpenShell policy. The base image supplies PyTorch,
torchvision, and ONNX Runtime. See [requirements.txt](requirements.txt).

## Build

Prerequisites: Docker, Compose, OpenShell CLI. GPU hosts also need NVIDIA
Container Toolkit/CDI and a compatible driver.

```bash
export COMPUTE=cpu                         # use cuda on Ubuntu NVIDIA
docker build --build-arg COMPUTE="$COMPUTE" \
  --tag "deep-research:$COMPUTE" config/openshell/deep-research
```

CUDA requires Linux AMD64. The context excludes host projects and credentials.

## Local gateway and sandbox

```bash
export DEEP_RESEARCH_GATEWAY_DATA="$PWD/.openshell-runtime"
docker compose --env-file /dev/null \
  -f config/openshell/deep-research/gateway-compose.yaml up -d
openshell gateway add http://127.0.0.1:8080 --local --name deep-research-local

openshell --gateway-endpoint http://127.0.0.1:8080 sandbox create \
  --name deep-research --from "docker.io/library/deep-research:$COMPUTE" \
  --policy config/openshell/deep-research/policy.yaml --no-auto-providers \
  --cpu 4 --memory 8Gi --detach -- /bin/bash -l
```

For CUDA, add `--gpu 1` before `-- /bin/bash -l`. Then open a shell:

```bash
openshell --gateway-endpoint http://127.0.0.1:8080 sandbox exec \
  --name deep-research --workdir /sandbox/workspace --tty -- research-session shell
```

Inside the sandbox:

```bash
codex login --device-auth
claude auth login
codex                                      # or claude
research-session check                     # add --gpu on Ubuntu NVIDIA
research-session ros ros2 topic list
```

ROS commands use Ubuntu's Python environment. Research Python uses
`/sandbox/.venv`. The local gateway owns the Docker socket; the sandbox is
non-root and receives no host project mount. Private files and credentials are
not imported automatically. Hosted agent requests still send context to the
provider, and telemetry opt-outs do not guarantee zero retention.

Stop the gateway with `docker compose ... stop`.
