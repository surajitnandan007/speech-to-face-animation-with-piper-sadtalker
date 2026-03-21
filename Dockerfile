FROM runpod/pytorch:2.0.1-py3.10-cuda11.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_HOME=/app \
    SADTALKER_HOME=/opt/SadTalker \
    MODEL_HOME=/opt/models \
    PIPER_HOME=/opt/piper

WORKDIR ${APP_HOME}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel && \
    python -m pip install -r requirements.txt

ARG SADTALKER_REPO_URL=https://github.com/OpenTalker/SadTalker.git
ARG SADTALKER_REPO_REF=main

RUN git clone --depth 1 --branch ${SADTALKER_REPO_REF} ${SADTALKER_REPO_URL} ${SADTALKER_HOME}

RUN python -m pip install -r ${SADTALKER_HOME}/requirements.txt

COPY app ./app
COPY handler.py ./handler.py
COPY test_input.json ./test_input.json
COPY models ${MODEL_HOME}

RUN mkdir -p /app/storage/uploads /app/storage/results

ENV SADTALKER_REPO_PATH=${SADTALKER_HOME} \
    SADTALKER_PYTHON_EXECUTABLE=python \
    SADTALKER_CHECKPOINT_DIR=${MODEL_HOME}/checkpoints \
    PIPER_VOICE=en_US-lessac-medium \
    PIPER_DATA_DIR=${PIPER_HOME}/data \
    PIPER_DOWNLOAD_DIR=${PIPER_HOME}/downloads \
    UPLOAD_DIR=/app/storage/uploads \
    RESULTS_DIR=/app/storage/results

CMD ["python", "-u", "handler.py"]
