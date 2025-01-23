## Запуск в докере
Тесты
```
make tests
```
Запуск сервера
```
make run_server
```

## Запуск без докера
* При запуске берутся реквизиты сервера redis из .env-файла

Установка зависимостей с помощью poetry
```
pip install poetry && poetry install --with dev
```
Запуск тестов
```
dotenv run poetry run pytest
```

Запуск сервера с указанием лог-файла
```
dotenv run python -m scoring.api --log scoring_log.txt
```

Запуск сервера без указания лог-файла (логирование в stdout)
```
dotenv run python -m scoring.api
```
