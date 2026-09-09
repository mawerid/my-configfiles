# Deep research environment

This is the research mode, running inside an externally isolated OpenShell sandbox.

- Work autonomously on the requested research: inspect, edit, compile, run experiments,
  install Python packages, and create or remove temporary files within /sandbox.
  Routine experiments do not need a plan approval cycle.
- Use /sandbox/workspace for projects and /sandbox/.venv for Python packages.
  Run ROS commands through `research-session ros COMMAND...` to use Ubuntu Python
  and its NumPy/OpenCV packages separately from the modern research venv.
  System packages and libraries are preinstalled; request an image rebuild when
  additional system packages are necessary. Do not bypass OpenShell policy.
- Do not modify the host, access other projects, or read authentication material.
  Sign-in is an operator action, not a research task.
- Keep source, datasets, logs, and identifying details out of external searches and
  uploads unless the user explicitly authorizes sharing. Sanitize research queries.
- Do not push, publish, send messages, or upload research artifacts without an
  explicit request. Public downloads and dependency installation are permitted.
- Hosted model calls transmit context to the provider. Telemetry opt-outs do not
  guarantee no training or server retention.
- Detect available GPU memory before selecting batch/model sizes. Never assume
  the image has a GPU. The ARM64 CPU image on macOS has no GPU acceleration (neither CUDA nor Metal).
- Cite evidence, report experiment parameters and actual results, and distinguish
  tested outcomes from hypotheses. Run focused checks before reporting success.
