from fastapi import FastAPI, UploadFile
from fastapi.responses import FileResponse
from pathlib import Path
import tempfile, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'windows_app'))
from vectorfont.pipeline import Pipeline, PipelineConfig

app = FastAPI()

@app.post('/vectorize')
async def vectorize(file: UploadFile, scale: float = 2.0, threshold: int = 180, chars: str = 'A'):
    tmp = Path(tempfile.mkdtemp())
    src = tmp/'in.png'; src.write_bytes(await file.read())
    ttf, svg = Pipeline(PipelineConfig(upscale=scale, threshold=threshold, chars=chars)).run(src, tmp/'out')
    return FileResponse(ttf, media_type='font/ttf', filename='vectorfont.ttf')
