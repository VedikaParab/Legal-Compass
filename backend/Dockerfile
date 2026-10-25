FROM python:3.13-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
# data/ (classifier + case index built from IL-TUR) is mounted at runtime, never baked into the image
ENV LCAPP_DATA=/srv/data
EXPOSE 8100
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]
