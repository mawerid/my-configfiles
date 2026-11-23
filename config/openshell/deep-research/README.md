# Deep research OpenShell image

Uses `nvcr.io/nvidia/pytorch:26.03-py3` (Ubuntu 24.04, Python 3.12,
CUDA 13.2) for both architectures. [NVIDIA release notes](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-26-03.html)

| Host | Image | Compute |
| --- | --- | --- |
| Ubuntu AMD64 + NVIDIA | `deep-research:cuda` | GPU |
| macOS M4 / Linux ARM64 | `deep-research:cpu` | CPU |

The image includes the C++/ROS tools, OpenCV, Ceres, Python research tools,
Codex, Claude Code, and the OpenShell policy. The base image supplies PyTorch
and torchvision. The build installs the CPU or GPU variant of ONNX Runtime.
See [requirements.txt](requirements.txt).

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

On Docker Desktop, enable host networking for the OpenShell supervisor.
Compose publishes the gateway API on the host loopback address and persists
its database and supervisor signing keys in the gateway volume.
[OpenShell Docker driver](https://github.com/NVIDIA/OpenShell/blob/main/crates/openshell-driver-docker/README.md)

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

ROS commands use Ubuntu's Python environment. Research libraries are installed
into the image's default Python environment. The local gateway owns the Docker
socket. The sandbox runs as a non-root user with no host project mount, and
private files and credentials stay on the host unless imported. Hosted agent
requests send context to the provider, where retention depends on the provider
and account controls.

Stop the gateway with `docker compose ... stop`.
