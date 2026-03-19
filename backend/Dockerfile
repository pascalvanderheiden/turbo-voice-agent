FROM python:3.12-slim AS base

# Install system deps: ffmpeg + Node.js 20 + Playwright browser deps
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
      | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
      > /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies from pyproject.toml
COPY pyproject.toml ./
RUN python3 -c "import tomllib, pathlib; \
    deps = tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; \
    pathlib.Path('/tmp/reqs.txt').write_text('\n'.join(deps))" && \
    pip install --no-cache-dir -r /tmp/reqs.txt

# Install Playwright Chromium browser (used by dev pipeline test stage)
RUN playwright install --with-deps chromium

# Copy app source (`.build-stamp` file changes each deploy to bust cache)
COPY . .

# Verify critical route modules are importable (fail fast if not)
RUN python3 -c "from app.utils.openspec_parser import parse_openspec_folder; print('openspec_parser OK')"

RUN mkdir -p /mnt/data /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
