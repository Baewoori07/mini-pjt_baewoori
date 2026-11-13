#!/usr/bin/env bash
# SwimCoach 실행 스크립트
#   ./run.sh serve        웹앱 + API 서버 (http://127.0.0.1:8000, 표준 API: POST /query)
#   ./run.sh test         자동 테스트 (Bedrock 모킹, 실제 호출 없음)
#   ./run.sh eval N       인-아웃 세트 자체 평가 라운드 N 실행 (실제 Bedrock 호출)
# 필요: .env 에 AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
# 모델 변경: BEDROCK_MODEL_ID / JUDGE_MODEL_ID 환경변수 (기본 global.anthropic.claude-sonnet-4-6)
set -euo pipefail
cd "$(dirname "$0")"

if command -v uv >/dev/null 2>&1; then
  RUN="uv run"
else
  RUN=""   # pip install -r requirements.txt 로 설치한 환경
fi

case "${1:-serve}" in
  serve)
    $RUN uvicorn src.main:create_app --factory --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
    ;;
  test)
    $RUN pytest -q
    ;;
  eval)
    $RUN python -m evaluation.run --round "${2:?라운드 번호를 주세요: ./run.sh eval 1}" ${3:+--changes "$3"}
    ;;
  *)
    echo "usage: $0 [serve|test|eval N [changes.md]]" >&2
    exit 1
    ;;
esac
