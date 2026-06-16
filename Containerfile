# Multi-stage build. This is the key trick for running a real framework
# (FastAPI) on a distroless Hummingbird image: install the dependencies in a
# builder stage, then copy them into the final image, which has no pip.

# --- build stage: install dependencies ---
FROM registry.access.redhat.com/hi/python:3.11-builder AS build
USER root
WORKDIR /app
COPY requirements.txt .
RUN mkdir -p /app/deps && pip install --target=/app/deps -r requirements.txt

# --- final stage: distroless, just the app and its deps ---
FROM registry.access.redhat.com/hi/python:3.11
WORKDIR /app
COPY --from=build /app/deps /app/deps
COPY app/ /app/
ENV PYTHONPATH=/app/deps
USER 65532
EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
