# PCEF web app: CPU-only image with the embedding model downloaded at build time.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/hf

WORKDIR /app

# CPU-only PyTorch keeps the image far smaller than the default CUDA build
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml requirements-app.txt ./
COPY src ./src
RUN pip install ".[sbert]" -r requirements-app.txt

# The exact model revision used for every reported result
ARG MODEL_ID=sentence-transformers/all-mpnet-base-v2
ARG MODEL_REVISION=e8c3b32edf5434bc2275fc9bab85f82640a19130
RUN python -c "from huggingface_hub import snapshot_download; \
snapshot_download('${MODEL_ID}', revision='${MODEL_REVISION}', \
ignore_patterns=['*.bin', '*.h5', '*.msgpack', '*.ot', 'onnx/*', 'openvino/*'])"

COPY . .

ENV HOST=0.0.0.0 \
    PORT=8000 \
    HF_HUB_OFFLINE=1 \
    PCEF_MODEL_REVISION=${MODEL_REVISION} \
    PCEF_OPEN_BROWSER=0

EXPOSE 8000
CMD ["python", "-m", "app.server"]
