# One image per release: API code + the model trained for that release.
# Stages: base -> test (unit tests), base -> train (model + metrics.json), base + model -> final image.
FROM python:3.11.11-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY VERSION .
COPY ml/ ml/
COPY app/ app/

FROM base AS test
RUN pip install --no-cache-dir pytest==8.3.4 httpx==0.27.2
COPY scripts/ scripts/
COPY tests/ tests/
RUN python -m pytest -q tests

FROM base AS train
# Failure demo 1: set to "--degrade" to train a weak model that the accuracy gate rejects.
ARG TRAIN_ARGS=""
RUN python -m ml.train $TRAIN_ARGS

FROM base
COPY --from=train /app/model model/
# Failure demo 2: set to "fast" to ship a serving tokenizer that does not match training.
ARG TOKENIZER=standard
ENV TOKENIZER=$TOKENIZER
USER nobody
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
