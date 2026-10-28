# FGI 질적연구 AI 코딩 분석 (fgi-analyzer)

> 공통 규칙: /srv/projects/CLAUDE.md | 소유자: 최진명 <choi0127@jobcenter.or.kr> | 최종 갱신: 2026-10-28

## 목적
FGI 전사본을 Braun & Clarke 주제분석 1~5단계(개방 코딩 → 코드북 → 주제 묶기 → 원자료 검토 → 보고서 초안)로 AI 보조 분석하는 Streamlit 앱. 음성 파일 → 글(서버 GPU), 개인정보 가리기 포함. **`https://scv.job.or.kr/fgi/`** (nginx `snippets/scv-front-443.conf` 의 `/fgi/` 묶음 → 127.0.0.1:5190, 사내 /23 + VPN). 직접 주소 `http://192.168.0.97:5190/fgi/` 도 됨(하위 경로는 `.streamlit/config.toml` baseUrlPath).

## 구조
- `app.py` — 앱 전체. 위쪽 `PROVIDERS` 에서 AI 선택지(Claude·Gemini)와 모델을 정한다. 단계마다 쓴 AI 를 `stageN_model` 에 기록해 화면·다운로드에 표시.
- `extract.py` — 올린 파일(txt·md·hwpx·docx·doc)에서 글자 추출. .doc 는 LibreOffice(soffice)로 변환, 파일은 저장하지 않음.
- `stt.py` — 음성 → 글: ffmpeg 16kHz → GPU whisper `/opt/whisper-cuda`(large-v3-turbo, 한국어). 한 번에 하나(`/tmp/fgi-whisper.lock`), 임시 파일 삭제. 속도 약 녹음 길이의 1/4(3분 → 49초).
- `mask.py` — 개인정보 가리기: 참여자 이름 목록(P1…, '이름=바꿀 말', '민수 씨'처럼 호칭 붙은 이름만 부름도) + pii-cleaner 자동 찾기(코드·모델 `/srv/projects/pii-cleaner/repo` 를 읽기만, 환경변수 `PII_CLEANER_REPO`, 인터넷 끔). 표로 확인·수정 후 적용. 자동 찾기는 띄어 쓴 이름·두 글자 이름·동 이름을 놓침(2026-10-23·28 시험).
- `.streamlit/config.toml` — baseUrlPath `fgi`, 올리기 500MB(음성), nginx `/fgi/` 도 500m.
- `deploy/setgemini.sh` — Gemini 키 숨김 입력(확인 조회 → 한 줄 교체 → 재시작).
- 저장소 `seoul-jobcenter/fgi-analyzer` (2026-10-28 `choi0127` 에서 이관).

## 운영
- 운영본 `/home/cjm/fgi-analyzer` (cjm 계정 git 작업본, venv 포함), systemd `fgi-analyzer`(User=cjm, :5190).
- 비밀값 `/home/cjm/.fgi.env` (systemd EnvironmentFile): `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`. 선택 `CLAUDE_MODEL`(기본 claude-opus-4-8)·`GEMINI_MODEL`(기본 gemini-4-argon)·`DEFAULT_PROVIDER`(기본 Claude).
- 배포(이 폴더에서 main 커밋·push 후):
  ```
  sudo -u cjm git -C /home/cjm/fgi-analyzer pull --ff-only
  sudo -u cjm /home/cjm/fgi-analyzer/venv/bin/pip install -r /home/cjm/fgi-analyzer/requirements.txt
  sudo systemctl restart fgi-analyzer
  ```
- Gemini 키: `ssh -t <계정>@192.168.0.97 "sudo bash /srv/projects/fgi-analyzer/deploy/setgemini.sh"`
- Gemini 는 **결제 연결된 유료 등급 키**만 쓴다 — 무료 등급은 입력·응답을 Google 제품 개선에 쓰고 사람이 검토할 수 있다(Gemini API 추가 약관, 2026-04-28 갱신본 확인).

## 진행 상태
- 2026-10-28 (claudework, pbk 지시): 저장소 이관 후 Claude/Gemini 선택 기능 추가. 운영본에만 있던 커밋 0580ff2(9-21 UI 개편)를 GitHub 에 함께 올림. 화면에서 입력한 키가 다음 동작 때 사라지던 문제 수정. Gemini 키는 pbk 가 입력함.
- 2026-10-28 오후: https `scv.job.or.kr/fgi/` 경로, 첫 화면 개편(머리 한 줄·단계 표시·파일|글 나란히·끝난 단계 접기), 파일 입력(txt·md·hwpx·docx·doc), AI 호출 실패 안내. 프롬프트 5개는 옛 코드와 조합 결과 동일 확인.
- 2026-10-28 저녁: 음성 → 글 대화 상자(끌어 놓기·찾아보기, 진행 막대, 끝나면 가리기/바로 분석/칸에 넣기), 개인정보 가리기 대화 상자(이름 목록 + 자동 찾기, 표 확인 후 적용, 가리고 바로 분석), 1단계 시작 버튼 항상 보이게(붙여넣기 뒤 바로 눌러도 반영). requirements 에 CPU torch·schift-ko-pii 추가(venv 약 1.5GB).
