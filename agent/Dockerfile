FROM debian:bookworm-slim

# Install system packages (include jq which the livekit install script needs).
# Use --no-install-recommends to keep image smaller and clean apt lists afterwards.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      python3 python3-pip curl jq ca-certificates \
      tar gzip gnupg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python deps (use pip cache mount in buildkit as you had)
COPY req.txt /app/req.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip3 install -r /app/req.txt --break-system-packages

# Install LiveKit CLI (now jq is available)
RUN curl -sSL https://get.livekit.io/cli | bash

# Copy app files
COPY dispatch-rule.json /app
COPY inbound-trunk.json /app
COPY .env.local /app
COPY main.py /app
COPY setup.sh /app

RUN chmod +x /app/setup.sh
RUN python3 main.py download-files

# IMPORTANT: don't run long-running or network-heavy one-off runtime tasks here in build
# (e.g. "python3 agent.py download-files") — run them at container runtime or in an init step.
# If you must run a quick setup during build, prefer short, deterministic commands.

CMD ["python3", "main.py", "dev"]
