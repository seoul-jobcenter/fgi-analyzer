import streamlit as st
import anthropic
from datetime import datetime

st.set_page_config(
    page_title="FGI 질적연구 AI 코딩 분석",
    page_icon="🔍",
    layout="wide"
)

# ── 사이드바 ──────────────────────────────────────────────────────
with st.sidebar:
    st.title("🔍 FGI 분석 프로그램")
    st.caption("서울특별시장애인일자리센터")
    st.divider()

    # API 키: Streamlit 시크릿 우선, 없으면 직접 입력
    default_key = st.secrets.get("ANTHROPIC_API_KEY", "")
    if default_key:
        api_key = default_key
        st.success("✅ API 연결됨")
    else:
        api_key = st.text_input("🔑 Anthropic API 키", type="password",
                                placeholder="sk-ant-...")

    st.divider()
    st.warning("⚠️ AI 결과는 **후보안**입니다.\n\n최종 코드북과 주제 구조는 연구자가 확정합니다.")
    st.divider()

    if st.button("🔄 처음부터 다시 시작", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

# ── 세션 초기화 ───────────────────────────────────────────────────
for stage in ["stage1", "stage2", "stage3", "stage4", "stage5"]:
    if stage not in st.session_state:
        st.session_state[stage] = None

# ── 메인 화면 ─────────────────────────────────────────────────────
st.title("FGI 질적연구 AI 코딩 분석")
st.caption("Braun & Clarke 분석법 | 2~5단계 AI 보조")

# API 키 확인
if not api_key:
    st.info("👈 왼쪽 사이드바에 Anthropic API 키를 입력하세요.")
    st.stop()

client = anthropic.Anthropic(api_key=api_key)

# ── 전사본 입력 ───────────────────────────────────────────────────
st.subheader("📄 전사본 입력")
st.caption("참여자명은 P1, P2 등으로 익명화해주세요.")

transcript = st.text_area(
    "FGI 전사본",
    height=250,
    placeholder="여기에 전사본을 붙여넣으세요...",
    label_visibility="collapsed"
)

if not transcript or len(transcript.strip()) < 20:
    st.info("전사본을 입력하면 분석을 시작할 수 있습니다.")
    st.stop()

st.success(f"✅ 전사본 입력 완료: {len(transcript.strip()):,}자")


# ── 스트리밍 헬퍼 ─────────────────────────────────────────────────
def stream_stage(system_text, user_content):
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=8192,
        system=[{"type": "text", "text": system_text,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_delta" and hasattr(event.delta, "text"):
                yield event.delta.text


# ── 1단계: 개방 코딩 ─────────────────────────────────────────────
st.divider()
st.subheader("1️⃣ 개방 코딩")

if st.session_state.stage1 is None:
    if st.button("▶ 1단계 분석 시작", type="primary", use_container_width=True):
        SYSTEM = "당신은 질적 코딩을 돕는 보조자다. 연구자의 분석을 지원하되, 자료에 없는 해석이나 추론은 하지 않는다."
        USER = (
            "다음 익명화된 인터뷰 전사본에 개방코딩을 하라.\n\n"
            "[규칙]\n"
            "- 의미 단위마다 코드를 부여한다.\n"
            "- 각 코드는 자료에 밀착한 짧은 분석적 표지로 작성한다.\n"
            "- 코드마다 근거가 된 원문 문장을 함께 제시한다.\n"
            "- 자료에 없는 감정, 의도, 원인을 추정하지 않는다.\n"
            "- 코드명과 정의는 한국어로 작성하고, 인용은 원문 그대로 제시한다.\n\n"
            "[출력형식]\n"
            "| 의미 단위 | 코드 | 근거 문장 | 분석 메모 |\n\n"
            "[전사본]\n"
            + transcript.strip()
        )
        with st.spinner("1단계 분석 중... (시간이 걸릴 수 있습니다)"):
            result = st.write_stream(stream_stage(
                SYSTEM,
                [{"type": "text", "text": USER, "cache_control": {"type": "ephemeral"}}]
            ))
        st.session_state.stage1 = result
        st.rerun()
else:
    st.markdown(st.session_state.stage1)
    if st.button("🔄 1단계 다시 실행"):
        st.session_state.stage1 = None
        for s in ["stage2", "stage3", "stage4", "stage5"]:
            st.session_state[s] = None
        st.rerun()


# ── 2단계: 코드북 초안 ───────────────────────────────────────────
if st.session_state.stage1:
    st.divider()
    st.subheader("2️⃣ 코드북 초안 작성")

    if st.session_state.stage2 is None:
        if st.button("▶ 2단계 분석 시작", type="primary", use_container_width=True):
            SYSTEM = "당신은 질적 코딩을 돕는 보조자다. 제공된 코드와 자료 안에서만 분석하며, 자료 외부의 내용을 만들지 않는다."
            USER = (
                "생성된 코드와 대표 인용문을 바탕으로 코드북 초안을 작성하라.\n"
                "각 코드는 다음 5요소를 포함: 코드명, 정의, 포함 기준, 제외 기준, 예시 인용문\n\n"
                "[제약]\n"
                "- 제공한 코드와 자료 안에서만 작성한다.\n"
                "- 예시 인용문은 새로 만들지 않는다.\n"
                "- 유사 코드를 통합할 경우 통합 근거를 메모로 남긴다.\n\n"
                "[출력형식]\n"
                "| 코드명 | 정의 | 포함 기준 | 제외 기준 | 예시 인용문 | 화자 |\n\n"
                "[1단계 개방코딩 결과]\n"
                + st.session_state.stage1
            )
            with st.spinner("2단계 분석 중..."):
                result = st.write_stream(stream_stage(
                    SYSTEM, [{"type": "text", "text": USER}]
                ))
            st.session_state.stage2 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage2)
        if st.button("🔄 2단계 다시 실행"):
            for s in ["stage2", "stage3", "stage4", "stage5"]:
                st.session_state[s] = None
            st.rerun()


# ── 3단계: 주제 묶기 ─────────────────────────────────────────────
if st.session_state.stage2:
    st.divider()
    st.subheader("3️⃣ 주제 묶기")

    if st.session_state.stage3 is None:
        if st.button("▶ 3단계 분석 시작", type="primary", use_container_width=True):
            SYSTEM = "당신은 질적 코딩을 돕는 보조자다. 코드 간 의미 관계를 분석하되, 자료 범위를 넘어 과장하지 않는다."
            USER = (
                "다음 코드 목록을 의미가 비슷한 것끼리 묶어라.\n\n"
                "[요청]\n"
                "- 유사 코드를 묶어 하위주제 후보를 찾는다.\n"
                "- 하위주제를 포괄하는 상위주제를 구성한다.\n"
                "- 각 주제에 분석적 명칭을 제안한다.\n"
                "- 각 주제가 어떤 코드와 인용문에 근거하는지 표시한다.\n"
                "- 경계가 모호한 코드는 별도로 표시한다.\n\n"
                "[주의]\n"
                "- 주제명은 동사, 관계, 과정이 드러나게 작성한다.\n"
                "- 자료 범위를 넘어 과장하지 않는다.\n\n"
                "[2단계 코드북 초안]\n"
                + st.session_state.stage2
            )
            with st.spinner("3단계 분석 중..."):
                result = st.write_stream(stream_stage(
                    SYSTEM, [{"type": "text", "text": USER}]
                ))
            st.session_state.stage3 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage3)
        if st.button("🔄 3단계 다시 실행"):
            for s in ["stage3", "stage4", "stage5"]:
                st.session_state[s] = None
            st.rerun()


# ── 4단계: 원자료 검토 ───────────────────────────────────────────
if st.session_state.stage3:
    st.divider()
    st.subheader("4️⃣ 전사본 원자료 검토")

    if st.session_state.stage4 is None:
        if st.button("▶ 4단계 분석 시작", type="primary", use_container_width=True):
            SYSTEM = "당신은 질적 코딩을 돕는 보조자다. 이 결과는 후보안이며, 최종 결정은 연구자가 내린다."
            USER = (
                "다음 상위주제·하위주제 후보 목록을, 제공된 전사본 원자료 전체와 대조하여 검토하라.\n\n"
                "[규칙]\n"
                "- 각 주제가 전사본 전체에서 반복적으로 나타나는 패턴을 대표하는지(내적 일관성) 확인한다.\n"
                "- 각 주제가 다른 주제와 개념적으로 뚜렷이 구별되는지(외적 구별성) 확인한다.\n"
                "- 코딩되지 않았지만 주제와 관련된 발화가 원자료에 남아있는지 찾아 표시한다.\n"
                "- 하나의 주제 안에 서로 다른 패턴이 섞여 있다면 분리를 제안한다.\n"
                "- 서로 겹치는 주제는 통합을 제안한다.\n"
                "- 주제로 성립하기 어려운 경우 폐기를 제안하되, 반론·예외는 별도 표시한다.\n"
                "- 자료에 없는 새로운 해석이나 결론을 만들지 않는다.\n"
                "- 최종 결정은 연구자가 하며, 이 결과는 후보안일 뿐임을 전제한다.\n\n"
                "[출력형식]\n"
                "| 주제명 | 검토 의견(유지/분리/통합/폐기) | 판단 근거(원문 인용 포함) | 미비점·추가 확인 필요 사항 |\n\n"
                "[상위주제·하위주제 후보]\n"
                + st.session_state.stage3
                + "\n\n[전사본 원자료]\n"
                + transcript.strip()
            )
            with st.spinner("4단계 분석 중... (전사본 전체를 다시 검토하므로 시간이 걸립니다)"):
                result = st.write_stream(stream_stage(
                    SYSTEM,
                    [{"type": "text", "text": USER, "cache_control": {"type": "ephemeral"}}]
                ))
            st.session_state.stage4 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage4)
        if st.button("🔄 4단계 다시 실행"):
            for s in ["stage4", "stage5"]:
                st.session_state[s] = None
            st.rerun()


# ── 5단계: 최종 보고서 초안 ─────────────────────────────────────
if st.session_state.stage4:
    st.divider()
    st.subheader("5️⃣ 최종 주제 선정 및 보고서 초안")

    if st.session_state.stage5 is None:
        if st.button("▶ 5단계 분석 시작", type="primary", use_container_width=True):
            SYSTEM = "당신은 질적 코딩을 돕는 보조자다. 유지 판정된 주제에 한해 자료 근거 기반 설명문을 작성한다."
            USER = (
                "검토 의견 '유지'로 기재된 내용을 최종 주제로 확정한다.\n"
                "그에 속한 코드·인용문을 바탕으로 주제 설명문을 작성하라.\n\n"
                "[구조]\n"
                "① 자료 근거 — 어떤 코드와 인용문이 이 주제를 지지하는가\n"
                "② 해석 — 이 인용문들이 보여주는 패턴이 무엇인가\n"
                "③ 의미 — 이 패턴이 연구 질문에 대해 무엇을 말해주는가\n\n"
                "[출력형식]\n"
                "| 주제명 | 자료 근거(코드·인용문) | 해석 | 의미(연구 질문과의 연결) |\n\n"
                "[4단계 검토 결과]\n"
                + st.session_state.stage4
            )
            with st.spinner("5단계 분석 중..."):
                result = st.write_stream(stream_stage(
                    SYSTEM, [{"type": "text", "text": USER}]
                ))
            st.session_state.stage5 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage5)
        if st.button("🔄 5단계 다시 실행"):
            st.session_state.stage5 = None
            st.rerun()


# ── 결과 다운로드 ─────────────────────────────────────────────────
if st.session_state.stage5:
    st.divider()
    st.subheader("💾 결과 다운로드")

    stage_map = [
        ("stage1", "1단계: 개방 코딩"),
        ("stage2", "2단계: 코드북 초안"),
        ("stage3", "3단계: 주제 묶기"),
        ("stage4", "4단계: 원자료 검토"),
        ("stage5", "5단계: 최종 보고서 초안"),
    ]

    all_results = "# FGI 분석 결과\n\n"
    all_results += f"> 생성: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
    all_results += "> ⚠️ AI 결과는 후보안입니다. 최종 확정은 연구자가 결정합니다.\n\n"
    for key, name in stage_map:
        if st.session_state.get(key):
            all_results += f"---\n\n## {name}\n\n{st.session_state[key]}\n\n"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="📥 전체 결과 다운로드 (.md)",
        data=all_results.encode("utf-8"),
        file_name=f"FGI_분석결과_{timestamp}.md",
        mime="text/markdown",
        use_container_width=True,
        type="primary"
    )
