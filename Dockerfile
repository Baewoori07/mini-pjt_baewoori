# SwimCoach - 클린 환경 재현용 이미지
#   docker build -t swimcoach .
#   docker run --rm -p 8000:8000 --env-file .env swimcoach
# AWS 자격증명은 이미지에 넣지 않고 실행 시 --env-file 로 전달합니다.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY static/ static/
COPY data/ data/
COPY evaluation/ evaluation/
COPY tests/ tests/
COPY pyproject.toml run.sh ./

EXPOSE 8000
CMD ["uvicorn", "src.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
