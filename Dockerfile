#################################################################################
# STAGE - BUILD
#################################################################################
FROM python:3.12-slim AS build

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1
# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY . /app

#################################################################################
# STAGE - TESTS
#################################################################################
FROM build AS tests

RUN python -m pip install --no-cache-dir --disable-pip-version-check -r requirements-dev.txt

#################################################################################
# STAGE - RUNTIME
#################################################################################
FROM python:3.12-slim AS runtime

ENV PYTHONUNBUFFERED=1
ENV PORT=5001

WORKDIR /app
COPY --from=build /app /app
COPY --from=build /usr/local /usr/local

CMD ["sh", "-c", "uvicorn spliceai_api.app:app --host 0.0.0.0 --port $PORT --root-path /spliceai/api/v1"]
