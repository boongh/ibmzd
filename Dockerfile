# Backend image for LinuxONE (s390x)
#
# The base is the LinuxONE Community Cloud JupyterLab image: its /opt/venv has the torch 2.11.0+cpu,
# torch-nnpa 1.5.0, transformers 5.19.0 and zDNN setup verified by LFM25-PII-Hybrid-Summary.ipynb.
# Those packages are left untouched; uv only adds the backend's own dependencies (pinned by uv.lock).
FROM registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN /opt/venv/bin/python -m pip install --no-cache-dir uv \
 && /opt/venv/bin/uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/requirements.txt \
 && /opt/venv/bin/uv pip install --no-cache --python /opt/venv/bin/python -r /tmp/requirements.txt \
 && /opt/venv/bin/python -c "import torch, torch_nnpa, transformers; \
assert torch.__version__ == '2.11.0+cpu' and transformers.__version__ == '5.19.0', 'verified versions changed'"

COPY main.py ./
COPY src ./src

# Mounts: /app/config.toml (read only), /data for the database and the Hugging Face cache.
# The base image's entrypoint (tini) is kept, so signals reach uvicorn.
CMD ["/opt/venv/bin/python", "main.py"]
