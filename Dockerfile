FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY . .
CMD ["python", "main.py"]