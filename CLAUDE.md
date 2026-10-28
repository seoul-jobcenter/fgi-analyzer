# FGI 질적연구 AI 코딩 분석 (fgi-analyzer)

> 공통 규칙: /srv/projects/CLAUDE.md | 소유자: 최진명 <choi0127@jobcenter.or.kr> | 최종 갱신: 2026-10-28

## 목적
FGI 전사본을 Braun & Clarke 주제분석 1~5단계(개방 코딩 → 코드북 → 주제 묶기 → 원자료 검토 → 보고서 초안)로 AI 보조 분석하는 Streamlit 앱. **`https://scv.job.or.kr/fgi/`** (nginx `snippets/scv-front-443.conf` 의 `/fgi/` 묶음 → 127.0.0.1:5190, 사내 /23 + VPN). 직접 주소 `http://192.168.0.97:5190/fgi/` 도 됨(하위 경로는 `.streamlit/config.toml` baseUrlPath).

## 구조
- `app.py` — 앱 전체. 위쪽 `PROVIDERS` 에서 AI 선택지(Claude·Gemini)와 모델을 정한다. 단계마다 쓴 AI 를 `stageN_model` 에 기록해 화면·다운로드에 표시.
- `extract.py` — 올린 파일(txt·md·hwpx·docx·doc)에서 글자 추출. .doc 는 LibreOffice(soffice)로 변환, 파일은 저장하지 않음.
- `.streamlit/config.toml` — baseUrlPath `fgi`, 올리기 20MB.
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
