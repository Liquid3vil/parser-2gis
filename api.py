from fastapi import FastAPI
from pydantic import BaseModel
import subprocess
import tempfile
import os

app = FastAPI()

class ParseRequest(BaseModel):
    url: str
    output_format: str = "json"
    max_records: int = 100

@app.post("/parse/")
def parse_2gis(request: ParseRequest):
    try:
        output_file = tempfile.NamedTemporaryFile(delete=False, suffix=f".{request.output_format}")
        output_path = output_file.name
        output_file.close()

        command = [
            "python", "parser-2gis",
            "-i", request.url,
            "-o", output_path,
            "-f", request.output_format,
            "--parser.max-records", str(request.max_records)
        ]

        subprocess.run(command, check=True)

        with open(output_path, "r", encoding="utf-8") as file:
            result = file.read()

        os.unlink(output_path)
        return {"status": "success", "data": result}

    except Exception as e:
        return {"status": "error", "message": str(e)}
