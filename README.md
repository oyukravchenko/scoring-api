Запустить тесты
```
python -m unittest discover -s tests
```

Запуск сервера с указанием лог-файла
```
python -m scoring.api --log scoring_log.txt
```

Запуск сервера без указания лог-файла (логирование в stdout)
```
python -m scoring.api
```
