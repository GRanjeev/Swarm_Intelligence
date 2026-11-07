FROM python:3.12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends netcat-openbsd curl procps iproute2 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -u 1000 agent \
 && mkdir -p /home/agent/work /home/agent/private \
 && chown -R agent:agent /home/agent
USER agent
WORKDIR /home/agent/work
