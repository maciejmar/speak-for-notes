FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry==1.8.4

COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --without dev --without-hashes -o requirements.txt && \
    pip install -r requirements.txt

COPY backend/ ./backend/
COPY run.py ./

RUN mkdir -p data

CMD ["python", "run.py"]
