FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py store.py ./
RUN useradd -r -u 10001 reader && mkdir -p /data && chown reader:reader /data
USER reader
ENV READING_DB_PATH=/data/books.sqlite3
EXPOSE 8000
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
