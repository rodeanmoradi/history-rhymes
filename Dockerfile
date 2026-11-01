FROM python:3.12-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app app
COPY static static

# Lessons are cached in SQLite; mount a volume here to keep them across deploys.
ENV DATA_DIR=/srv/data
VOLUME /srv/data
EXPOSE 8000
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
