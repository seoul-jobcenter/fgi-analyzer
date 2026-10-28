import os
import html
import streamlit as st
import anthropic
from datetime import datetime
from extract import ACCEPT, extract_text

st.set_page_config(page_title="FGI 질적연구 AI 코딩 분석", page_icon="🔍", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
[data-testid="stHeader"] { display: none; }
.block-container { padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1280px; }
.fgi-head h1 { font-size: 1.45rem; font-weight: 700; margin: 0; padding: 0; line-height: 1.3; }
.fgi-sub { font-size: 0.8rem; line-height: 1.5; opacity: 0.62; }
.fgi-status { display: inline-flex; align-items: center; justify-content: center; height: 2.25rem; width: 100%; font-size: 0.82rem; font-weight: 600; border-radius: 0.5rem; white-space: nowrap; }
[data-testid="stMarkdownContainer"]:has(> .fgi-status), [data-testid="stMarkdownContainer"]:has(> .fgi-steps) { margin-bottom: 0 !important; }
.fgi-on { background: rgba(33,195,84,0.14); color: #1a7f37; border: 1px solid rgba(33,195,84,0.35); }
.fgi-off { background: rgba(255,170,0,0.16); color: #96590d; border: 1px solid rgba(255,170,0,0.40); }
.fgi-steps { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.2rem 0 0.1rem; }
.fgi-step { font-size: 0.8rem; padding: 0.25rem 0.7rem; border-radius: 999px; border: 1px solid rgba(128,128,128,0.35); opacity: 0.6; }
.fgi-step.done { background: rgba(33,195,84,0.14); border-color: rgba(33,195,84,0.4); color: #1a7f37; opacity: 1; }
.fgi-step.now { border-color: #ff4b4b; color: #ff4b4b; font-weight: 600; opacity: 1; }
.fgi-stage { font-size: 1.02rem; font-weight: 700; }
.fgi-model { font-size: 0.78rem; font-weight: 400; opacity: 0.6; margin-left: 0.5rem; }
</style>
""", unsafe_allow_html=True)

# AI 선택지: 이름 → (키 환경변수, 모델, 키 예시)
PROVIDERS = {
    "Claude": ("ANTHROPIC_API_KEY", os.environ.get("CLAUDE_MODEL", "claude-opus-4-8"), "sk-ant-..."),
    "Gemini": ("GEMINI_API_KEY", os.environ.get("GEMINI_MODEL", "gemini-4-argon"), "AIza..."),
}

def load_key(env_name):
    key = os.environ.get(env_name, "")
    if not key:
        try:
            key = st.secrets.get(env_name, "")
        except Exception:
            key = ""
    return key or st.session_state.get(f"key_saved_{env_name}", "")

def save_key(env_name):
    # 입력칸이 사라지면 위젯 값도 지워지므로 따로 보관한다
    st.session_state[f"key_saved_{env_name}"] = st.session_state.get(f"key_input_{env_name}", "")

def load_file():
    # 올린 파일의 글자를 전사본 칸에 채운다(칸에서 바로 고칠 수 있다)
    f = st.session_state.get("upload")
    if f is None:
        return
    try:
        st.session_state.transcript = extract_text(f.name, f.getvalue())
        st.session_state.upload_msg = ("ok", f"{f.name} 불러옴")
    except Exception as e:
        st.session_state.upload_msg = ("err", f"{f.name}: {e}")

# 단계별 지시문 — 내용을 바꿀 때는 연구 방법(Braun & Clarke) 담당자와 상의
PROMPT1 = "당신은 질적 코딩을 돕는 보조자다. 자료에 없는 해석이나 추론은 하지 않는다.\n\n다음 전사본에 개방코딩을 하라.\n\n[규칙]\n- 의미 단위마다 코드를 부여한다.\n- 각 코드는 자료에 밀착한 짧은 분석적 표지로 작성한다.\n- 코드마다 근거가 된 원문 문장을 함께 제시한다.\n- 자료에 없는 감정, 의도, 원인을 추정하지 않는다.\n- 코드명과 정의는 한국어로 작성하고, 인용은 원문 그대로 제시한다.\n\n[출력형식]\n| 의미 단위 | 코드 | 근거 문장 | 분석 메모 |\n\n[전사본]\n"
PROMPT2 = "당신은 질적 코딩을 돕는 보조자다. 제공된 코드와 자료 안에서만 작성한다.\n\n코드북 초안을 작성하라.\n각 코드: 코드명, 정의, 포함 기준, 제외 기준, 예시 인용문\n\n[제약]\n- 예시 인용문은 새로 만들지 않는다.\n- 유사 코드 통합 시 근거를 메모로 남긴다.\n\n[출력형식]\n| 코드명 | 정의 | 포함 기준 | 제외 기준 | 예시 인용문 | 화자 |\n\n[1단계 결과]\n"
PROMPT3 = "당신은 질적 코딩을 돕는 보조자다. 자료 범위를 넘어 과장하지 않는다.\n\n코드를 의미가 비슷한 것끼리 묶어라.\n\n[요청]\n- 유사 코드를 묶어 하위주제 후보를 찾는다.\n- 하위주제를 포괄하는 상위주제를 구성한다.\n- 각 주제에 분석적 명칭을 제안한다.\n- 각 주제가 어떤 코드와 인용문에 근거하는지 표시한다.\n- 경계가 모호한 코드는 별도로 표시한다.\n- 주제명은 동사, 관계, 과정이 드러나게 작성한다.\n\n[2단계 결과]\n"
PROMPT4 = "당신은 질적 코딩을 돕는 보조자다. 이 결과는 후보안이며 최종 결정은 연구자가 한다.\n\n주제 후보를 전사본과 대조하여 검토하라.\n\n[규칙]\n- 내적 일관성 확인\n- 외적 구별성 확인\n- 미코딩 발화 중 관련 내용 찾아 표시\n- 패턴 혼재 시 분리, 겹치면 통합, 빈약하면 폐기 제안\n- 자료에 없는 해석 금지\n\n[출력형식]\n| 주제명 | 검토 의견(유지/분리/통합/폐기) | 판단 근거(원문 인용) | 미비점 |\n\n[주제 후보]\n"
PROMPT5 = "당신은 질적 코딩을 돕는 보조자다. 유지 판정된 주제에 한해 설명문을 작성한다.\n\n유지 판정된 주제로 보고서 초안을 작성하라.\n\n[구조]\n① 자료 근거\n② 해석\n③ 의미\n\n[출력형식]\n| 주제명 | 자료 근거(코드·인용문) | 해석 | 의미 |\n\n[4단계 결과]\n"

STAGE_KEYS = ["stage1", "stage2", "stage3", "stage4", "stage5"]
STAGE_TITLES = ["개방 코딩", "코드북 초안", "주제 묶기", "원자료 검토", "최종 보고서 초안"]

for s in STAGE_KEYS:
    if s not in st.session_state:
        st.session_state[s] = None
    if f"{s}_model" not in st.session_state:
        st.session_state[f"{s}_model"] = None

if "provider" not in st.session_state:
    st.session_state.provider = os.environ.get("DEFAULT_PROVIDER", "Claude")
provider = st.session_state.provider
key_env, model_name, key_hint = PROVIDERS[provider]
api_key = load_key(key_env)
model_label = f"{provider} ({model_name})"

# ── 머리: 제목 | AI 선택 · 연결 상태 · 처음부터 ──
head_left, head_right = st.columns([1.5, 1], vertical_alignment="center")
with head_left:
    st.markdown(
        '<div class="fgi-head"><h1>🔍 FGI 질적연구 AI 코딩 분석</h1>'
        '<div class="fgi-sub">서울특별시장애인일자리센터 | Braun &amp; Clarke 분석법 | 2~5단계 AI 보조'
        ' / 제작자 : 최진명(choi0127@jobcenter.or.kr)</div></div>',
        unsafe_allow_html=True,
    )
with head_right:
    pick_col, status_col, reset_col = st.columns([1.5, 1, 1], vertical_alignment="center")
    with pick_col:
        st.radio(
            "분석에 쓸 AI",
            list(PROVIDERS),
            key="provider",
            horizontal=True,
            label_visibility="collapsed",
            help="단계마다 바꿀 수 있습니다. 결과에는 단계별로 어느 AI가 분석했는지 표시됩니다.",
        )
    with status_col:
        if api_key:
            st.markdown(f'<div class="fgi-status fgi-on">✅ {provider} 연결됨</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="fgi-status fgi-off">⚠️ {provider} 미연결</div>', unsafe_allow_html=True)
    with reset_col:
        if st.button("🔄 처음부터", use_container_width=True, help="전사본과 분석 결과를 모두 지웁니다"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

note = f"모델 {model_name}"
if provider == "Gemini":
    note += " · Gemini API 는 결제가 연결된 유료 등급 키에서만 입력·응답을 Google 제품 개선에 쓰지 않습니다(무료 등급은 개선에 쓰고 사람이 검토할 수 있음)."
st.caption(note)

if not api_key:
    st.text_input(f"🔑 {provider} API 키", type="password", placeholder=key_hint, key=f"key_input_{key_env}", on_change=save_key, args=(key_env,))
    st.info(f"{provider} API 키를 입력하면 분석을 시작할 수 있습니다.")
    st.stop()

def run(prompt):
    if provider == "Gemini":
        from google import genai
        client = genai.Client(api_key=api_key)
        for chunk in client.models.generate_content_stream(model=model_name, contents=prompt):
            if chunk.text:
                yield chunk.text
        return
    client = anthropic.Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model_name,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            yield text

# ── 진행 단계 표시 ──
done = sum(1 for s in STAGE_KEYS if st.session_state[s])
steps = "".join(
    f'<span class="fgi-step {"done" if i < done else "now" if i == done else ""}">'
    f'{"✓ " if i < done else ""}{i + 1} {t}</span>'
    for i, t in enumerate(STAGE_TITLES)
)
st.markdown(f'<div class="fgi-steps">{steps}</div>', unsafe_allow_html=True)

# ── 전사본: 파일 올리기 | 붙여넣기 ──
with st.container(border=True):
    file_col, text_col = st.columns([1, 2.6])
    with file_col:
        st.markdown('<div class="fgi-stage">📄 전사본</div>', unsafe_allow_html=True)
        st.file_uploader(
            "파일 올리기", type=ACCEPT, key="upload", on_change=load_file,
            help="txt·md·hwpx·docx·doc 파일의 글자를 오른쪽 칸에 채웁니다. 파일은 서버에 저장하지 않습니다.",
        )
        msg = st.session_state.get("upload_msg")
        if msg:
            (st.caption if msg[0] == "ok" else st.error)(msg[1])
        st.caption("참여자명은 P1, P2 등으로 익명화해주세요.")
    with text_col:
        transcript = st.text_area("전사본", key="transcript", height=230, placeholder="여기에 전사본을 붙여넣거나 왼쪽에서 파일을 올리세요...", label_visibility="collapsed")
        if transcript and len(transcript.strip()) >= 20:
            st.caption(f"✅ {len(transcript.strip()):,}자")

if not transcript or len(transcript.strip()) < 20:
    st.stop()

def build_prompt(i):
    if i == 0:
        return PROMPT1 + transcript.strip()
    if i == 1:
        return PROMPT2 + st.session_state.stage1
    if i == 2:
        return PROMPT3 + st.session_state.stage2
    if i == 3:
        return PROMPT4 + st.session_state.stage3 + "\n\n[전사본]\n" + transcript.strip()
    return PROMPT5 + st.session_state.stage4

# ── 분석 단계: 끝난 단계는 접고, 다음 단계만 시작 버튼 ──
for i, (key, title) in enumerate(zip(STAGE_KEYS, STAGE_TITLES)):
    if i > 0 and not st.session_state[STAGE_KEYS[i - 1]]:
        break
    result = st.session_state[key]
    with st.container(border=True):
        title_col, btn_col = st.columns([4, 1], vertical_alignment="center")
        with title_col:
            used = f'<span class="fgi-model">분석: {html.escape(st.session_state[key + "_model"] or "")}</span>' if result else ""
            st.markdown(f'<div class="fgi-stage">{i + 1}️⃣ {title}{used}</div>', unsafe_allow_html=True)
        with btn_col:
            if result is None:
                clicked = st.button("▶ 분석 시작", key=f"run_{key}", type="primary", use_container_width=True)
            elif st.button("🔄 다시", key=f"redo_{key}", use_container_width=True):
                for s in STAGE_KEYS[i:]:
                    st.session_state[s] = None
                st.rerun()
        if result is None:
            if clicked:
                try:
                    with st.spinner(f"{i + 1}단계 분석 중..."):
                        out = st.write_stream(run(build_prompt(i)))
                except Exception as e:
                    st.error(f"{provider} 호출에 실패했습니다. 잠시 뒤 다시 누르거나 다른 AI를 골라 보세요.\n\n{type(e).__name__}: {str(e)[:300]}")
                    st.stop()
                st.session_state[key] = out
                st.session_state[key + "_model"] = model_label
                st.rerun()
        else:
            with st.expander("결과 보기", expanded=(i == done - 1)):
                st.markdown(result)

if st.session_state.stage5:
    out = "# FGI 분석 결과\n\n"
    for k, n in zip(STAGE_KEYS, ["1단계", "2단계", "3단계", "4단계", "5단계"]):
        if st.session_state.get(k):
            out += f"## {n}\n\n_분석: {st.session_state.get(k + '_model')}_\n\n{st.session_state[k]}\n\n---\n\n"
    st.download_button("📥 전체 결과 다운로드", data=out.encode("utf-8"), file_name=f"FGI결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", mime="text/markdown", use_container_width=True, type="primary")
