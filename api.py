from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import subprocess
import tempfile
import os
import logging
import uuid
from datetime import datetime, timedelta
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

# Директория для загрузки файлов
UPLOAD_DIRECTORY = "uploads"
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

# Хранилище информации о файлах
file_storage = {}

class ParseRequest(BaseModel):
    url: str
    output_format: str = "json"
    max_records: int = 100

class FileInfo(BaseModel):
    filename: str
    url: str
    expires_at: datetime

async def delete_file(file_id: str):
    file_info = file_storage.get(file_id)
    if file_info:
        try:
            os.remove(os.path.join(UPLOAD_DIRECTORY, file_info.filename))
            del file_storage[file_id]
            logging.info(f"Файл {file_info.filename} удалён.")
        except Exception as e:
            logging.error(f"Ошибка при удалении файла {file_info.filename}: {e}")

async def schedule_deletion(file_id: str, expires_at: datetime):
    delay = (expires_at - datetime.utcnow()).total_seconds()
    await asyncio.sleep(delay)
    await delete_file(file_id)

@app.post("/parse/")
def parse_2gis(request: ParseRequest):
    try:
        # Создание временного файла
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{request.output_format}") as output_file:
            output_path = output_file.name

        # Формирование команды
        command = [
            "python3",
            "/opt/render/project/src/parser-2gis",
            "-i", request.url,
            "-o", output_path,
            "-f", request.output_format,
            "--parser.max-records", str(request.max_records)
        ]

        logging.info(f"Выполняемая команда: {command}")

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

@app.post("/upload/")
async def upload_file(file: UploadFile):
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.{file.filename.split('.')[-1]}"
    file_path = os.path.join(UPLOAD_DIRECTORY, filename)

    try:
        with open(file_path, "wb") as f:
            while contents := await file.read(1024):
                f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {e}")

    expires_at = datetime.utcnow() + timedelta(days=1)
    file_storage[file_id] = FileInfo(filename=filename, url=f"/files/{file_id}", expires_at=expires_at)

    asyncio.create_task(schedule_deletion(file_id, expires_at))

    return {"file_id": file_id, "url": f"/files/{file_id}", "expires_at": expires_at}

@app.get("/files/{file_id}")
async def get_file(file_id: str):
    file_info = file_storage.get(file_id)
    if not file_info:
        raise HTTPException(status_code=404, detail="Файл не найден")

    return FileResponse(os.path.join(UPLOAD_DIRECTORY, file_info.filename), filename=file_info.filename)
