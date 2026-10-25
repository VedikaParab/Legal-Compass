FROM python:3.12-slim
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt
COPY src/ src/
COPY data/ data/
ENV PYTHONPATH=/app/src
ENV PYTHONUTF8=1
EXPOSE 8000
CMD ["uvicorn", "sb_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
