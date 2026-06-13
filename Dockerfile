# Minimal image for the Lumi web demo (FastAPI). Deliberately installs ONLY the
# Lumi runtime deps (web + azure extras) and NOT the acoustic base dependencies
# (TensorFlow, sounddevice, ...): the `lumi` package is isolated from the
# acoustic experiment, so the demo runs without them and the image stays small.
FROM python:3.12-slim

WORKDIR /app

# Lumi runtime deps only (mirror of the [web] + [azure] extras in pyproject).
# jinja2 is required at import time: adapters/reports/__init__ eagerly imports the
# report renderer (pdf.py imports jinja2). weasyprint stays out — its import is
# lazy and the web demo renders the report as HTML, not PDF.
RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn[standard]>=0.30" \
    "python-dotenv>=1.0" \
    "openai>=1.42" \
    "azure-identity>=1.17" \
    "pydantic>=2.8" \
    "jinja2>=3.1"

# Just the Lumi package (includes api/static/index.html). No data/, models/, tests/.
COPY src/lumi ./lumi

ENV PYTHONPATH=/app \
    LUMI_WEB_HOST=0.0.0.0 \
    LUMI_WEB_PORT=8000 \
    LUMI_DEMO_AI=1

EXPOSE 8000

CMD ["python", "-m", "lumi.api.web"]
