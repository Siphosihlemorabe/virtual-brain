# Virtual Brain: one container serving the web app and the agents.
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY samples samples
RUN useradd --create-home vb && mkdir -p data && chown vb data
USER vb
# The model key (GEMINI_API_KEY) is injected at run time, never baked into the image.
ENV VB_LLM=gemini PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/samples', timeout=3)"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
