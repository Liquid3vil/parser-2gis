from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import subprocess
import tempfile
import os
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

class ParseRequest(BaseModel):
    url: str
    output_format: str = "json"
    max_records: int = 100

@app.post("/parse/")
def parse_2gis(request: ParseRequest):
    try:
        # Создание временного файла
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{request.output_format}") as output_file:
            output_path = output_file.name

        # Формирование команды
        command = [
            "python3", # Используем python3, чтобы быть уверенными в версии
            "/opt/render/project/src/parser-2gis.py",
            "-i", request.url,
            "-o", output_path,
            "-f", request.output_format,
            "--parser.max-records", str(request.max_records)
        ]

        logging.info(f"Выполняемая команда: {command}") # Логируем команду

        # Запуск парсера и получение результатов
        process = subprocess.run(command, capture_output=True, text=True)

        # Логирование вывода парсера
        logging.info(f"Стандартный вывод парсера: {process.stdout}")
        logging.error(f"Стандартная ошибка парсера: {process.stderr}")

        # Проверка кода возврата
        if process.returncode != 0:
            logging.error(f"Парсер вернул код ошибки: {process.returncode}")
            raise HTTPException(status_code=400, detail=f"Парсер вернул код ошибки: {process.returncode}, {process.stderr}")

        # Чтение результата из файла
        with open(output_path, "r", encoding="utf-8") as file:
            result = file.read()

        # Удаление временного файла
        os.unlink(output_path)

        return {"status": "success", "data": result}

    except HTTPException as http_exception:
        return {"status": "error", "message": str(http_exception.detail)}
    except FileNotFoundError:
        return {"status": "error", "message": "parser-2gis не найден. Убедитесь, что он установлен и доступен."}
    except Exception as e:
        logging.exception("Произошла ошибка при выполнении парсера:")
        return {"status": "error", "message": str(e)}
