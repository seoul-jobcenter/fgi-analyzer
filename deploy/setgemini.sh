#!/bin/bash
# Gemini API 키를 숨김 입력으로 받아 /home/cjm/.fgi.env 의 GEMINI_API_KEY 한 줄만 바꾸고 서비스를 재시작한다.
# 사용: ssh -t <계정>@192.168.0.97 "sudo bash /srv/projects/fgi-analyzer/deploy/setgemini.sh"
set -euo pipefail
ENV_FILE=/home/cjm/.fgi.env
SERVICE=fgi-analyzer
MODEL=$(grep -oP '^GEMINI_MODEL=\K.*' "$ENV_FILE" 2>/dev/null || echo gemini-4-argon)

[ "$(id -u)" -eq 0 ] || { echo "sudo 로 실행하세요."; exit 1; }
[ -t 0 ] || { echo "키 입력 화면이 없습니다. ssh -t 로 접속해 실행하세요."; exit 1; }
[ -f "$ENV_FILE" ] || { echo "$ENV_FILE 이 없습니다."; exit 1; }

read -rsp "Gemini API 키를 붙여 넣고 Enter (화면에 안 보임): " KEY; echo
KEY=$(printf '%s' "$KEY" | tr -d '[:space:]')
[ -n "$KEY" ] || { echo "입력이 비었습니다. 바꾸지 않았습니다."; exit 1; }

echo "키 확인 중 (모델 정보 조회 — 비용 없음)..."
CODE=$(curl -s -o /dev/null -w '%{http_code}' -H "x-goog-api-key: $KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models/$MODEL") || CODE=000
case "$CODE" in
  200) echo "확인됨: 키가 유효하고 모델 $MODEL 을 쓸 수 있습니다." ;;
  404) echo "키는 통하지만 모델 $MODEL 을 찾지 못했습니다. 바꾸지 않았습니다."; exit 1 ;;
  *)   echo "키 확인 실패 (HTTP $CODE). 바꾸지 않았습니다."; exit 1 ;;
esac

BAK="$ENV_FILE.bak-$(date +%Y%m%d-%H%M%S)"; cp -p "$ENV_FILE" "$BAK"; chmod 600 "$BAK"
TMP=$(mktemp)
grep -v '^GEMINI_API_KEY=' "$ENV_FILE" > "$TMP" || true
printf 'GEMINI_API_KEY=%s\n' "$KEY" >> "$TMP"
cat "$TMP" > "$ENV_FILE"   # 기존 파일에 덮어써 소유자·권한 유지
rm -f "$TMP"
unset KEY

echo "저장했습니다: GEMINI_API_KEY=…$(grep -oP '^GEMINI_API_KEY=\K.*' "$ENV_FILE" | tail -c 5)"
systemctl restart "$SERVICE"
sleep 3
systemctl is-active --quiet "$SERVICE" && echo "$SERVICE 재시작 완료." || { echo "⚠ $SERVICE 가 시작되지 않았습니다: journalctl -u $SERVICE -n 30"; exit 1; }
