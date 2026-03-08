FROM python:3.12-slim AS base

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies from pyproject.toml (extract deps to avoid needing source)
COPY pyproject.toml ./
RUN python3 -c "import tomllib, pathlib; \
    deps = tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']; \
    pathlib.Path('/tmp/reqs.txt').write_text('\n'.join(deps))" && \
    pip install --no-cache-dir -r /tmp/reqs.txt

COPY . .

RUN mkdir -p /mnt/data /app/uploads

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
