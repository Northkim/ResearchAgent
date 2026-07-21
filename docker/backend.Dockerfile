FROM mambaorg/micromamba:2.8.1-debian13-slim

COPY --chown=$MAMBA_USER:$MAMBA_USER environment.yml /tmp/environment.yml
RUN micromamba create --yes --file /tmp/environment.yml \
    && micromamba clean --all --yes

WORKDIR /workspace
COPY --chown=$MAMBA_USER:$MAMBA_USER . /workspace

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD ["micromamba", "run", "--no-capture-output", "-n", "reagent-dev", "uvicorn", "backend.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
