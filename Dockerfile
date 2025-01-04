FROM python:3.12-slim

WORKDIR /app

COPY ./scoring ./scoring
COPY ./tests ./tests
COPY ./pyproject.toml .

RUN pip install poetry && poetry install --with dev

ENTRYPOINT ["poetry", "run"]
