FROM nvcr.io/nvidia/pytorch:26.03-py3

ARG COMPUTE=cpu
ENV DEBIAN_FRONTEND=noninteractive

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV ROS_DISTRO=jazzy

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

ENV UV_SYSTEM_PYTHON=TRUE
ENV UV_BREAK_SYSTEM_PACKAGES=TRUE

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg locales software-properties-common \
    build-essential gcc g++ clang cmake ninja-build gdb lldb clang-format \
    clang-tidy libopencv-dev python3-opencv libceres-dev libyaml-cpp-dev \
    libeigen3-dev libpcl-dev \
    git gh ripgrep fd-find htop nvtop jq tmux vim git-lfs pkg-config \
    nodejs npm unzip patch openssh-client openssh-sftp-server \
    iproute2 iptables nftables dnsutils iputils-ping netcat-openbsd procps \
    && rm -rf /var/lib/apt/lists/*

# Install ROS 2 Jazzy
RUN add-apt-repository -y universe && \
    curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu noble main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null && \
    apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-ros-base ros-jazzy-cv-bridge ros-jazzy-pcl-ros \
    python3-colcon-common-extensions python3-rosdep python3-vcstool \
    && rm -rf /var/lib/apt/lists/* && rosdep init

# Install OpenShell dependencies
RUN groupadd -r supervisor && useradd -r -g supervisor -s /usr/sbin/nologin supervisor
RUN groupadd -r sandbox && useradd -r -g sandbox -d /sandbox -s /bin/bash sandbox
RUN mkdir -p /sandbox /etc/openshell && ln -s /usr/bin/fdfind /usr/local/bin/fd

# Install Python dependencies
RUN pip install uv
COPY requirements.txt /tmp/requirements.txt
RUN if [ "$(dpkg --print-architecture)" = arm64 ]; then \
        git clone --depth 1 --branch v2.6 https://github.com/cvg/pyceres.git /tmp/pyceres && \
        uv pip install /tmp/pyceres && \
        rm -rf /tmp/pyceres; \
    fi
RUN uv pip install -r /tmp/requirements.txt
RUN if [ "$COMPUTE" = cuda ]; then \
        uv pip install onnxruntime-gpu; \
    else \
        uv pip install onnxruntime; \
    fi

# Install OpenAI Codex and Claude
RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh && \
    cp -L /root/.local/bin/codex /usr/local/bin/codex && \
    chmod 755 /usr/local/bin/codex
RUN curl -fsSL https://claude.ai/install.sh | sh && \
    cp -L /root/.local/bin/claude /usr/local/bin/claude && \
    chmod 755 /usr/local/bin/claude

# Setup env
ENV HOME=/sandbox
ENV CODEX_HOME=/sandbox/.codex
ENV CLAUDE_CONFIG_DIR=/sandbox/.claude

COPY codex.toml /sandbox/.codex/config.toml
COPY claude.json /sandbox/.claude/settings.json
COPY instructions.md /sandbox/AGENTS.md
COPY instructions.md /sandbox/.claude/CLAUDE.md
COPY policy.yaml /etc/openshell/policy.yaml

ENV CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-}
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV TORCH_FORCE_CPU_FALLBACK=1
ENV LD_LIBRARY_PATH=/usr/local/mpi/lib:/opt/hpcx/ucx/lib:${LD_LIBRARY_PATH}

# Test, remove it
COPY --chmod=755 research-session /usr/local/bin/research-session
COPY smoke/ /opt/deep-research-smoke/
RUN mkdir -p /sandbox/workspace /sandbox/.cache /dev/shm && \
    chown -R sandbox:sandbox /sandbox

USER sandbox
WORKDIR /sandbox/workspace

RUN /usr/local/bin/research-session check

CMD ["bash"]
