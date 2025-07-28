# server/mcp-model/Dockerfile

# Base image with uv and Python
FROM ghcr.io/astral-sh/uv:0.6.14-python3.10-bookworm-slim

# Set the working directory inside the container to /app
WORKDIR /app

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv uv sync --no-dev --no-editable

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Expose the ports that the server will run on
EXPOSE 8000 8001-8003

# Default command to run the server
CMD ["uv", "run", "server.py", "--port", "8091"]
