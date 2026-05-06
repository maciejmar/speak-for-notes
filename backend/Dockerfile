FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry==1.8.4 && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./
RUN poetry install --without dev --no-root

COPY backend/ ./backend/
COPY run.py ./

RUN mkdir -p data

CMD ["python", "run.py"]
