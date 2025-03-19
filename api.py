import subprocess
import tempfile
import os
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "2GIS Parser API is running"}

@app.post("/parse/")
def parse_2gis(url: str, output_format: str = "json", max_records: int = 100):
    try:
        # Создаём временный файл для результата
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{output_format}")
        output_path = output_file.name
        output_file.close()

        # Формируем команду запуска парсера
        command = [
            "python", "parser-2gis",
            "-i", url,
            "-o", output_path,
            "-f", output_format,
            "--parser.max-records", str(max_records)
        ]

        # Запускаем парсер
        subprocess.run(command, check=True)

        # Читаем результат
        with open(output_path, "r", encoding="utf-8") as file:
            result = file.read()

        # Удаляем временный файл
        os.unlink(output_path)

        return {"status": "success", "data": result}

    except Exception as e:
        return {"status": "error", "message": str(e)}
