# One container for the online demo: mapping API (internal) + assistant backend (public).
# Used by Render (render.yaml). OCR runs in the visitor's browser, so no OCR software is installed here.
FROM python:3.13-slim
WORKDIR /srv
COPY mapping_api/requirements-api.txt /tmp/req-api.txt
COPY backend/requirements.txt /tmp/req-app.txt
COPY deploy/constraints.txt /tmp/constraints.txt
RUN pip install --no-cache-dir -c /tmp/constraints.txt -r /tmp/req-api.txt -r /tmp/req-app.txt
COPY mapping_api /srv/mapping_api
COPY backend/app /srv/backend/app
COPY deploy/start.sh /srv/start.sh
ENV PYTHONUTF8=1 SERVER_OCR=0
EXPOSE 8100
CMD ["sh", "/srv/start.sh"]
