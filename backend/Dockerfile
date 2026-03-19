FROM python:3.11-slim
WORKDIR /app
RUN mkdir -p /app/data
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8166
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8166", "--workers", "1"]
