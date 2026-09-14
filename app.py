import streamlit as st
import google.generativeai as genai
from datetime import datetime

st.set_page_config(page_title="FGI 질적연구 AI 코딩 분석", page_icon="🔍", layout="wide")

with st.sidebar:
    st.title("🔍 FGI 분석 프로그램")
    st.caption("서울특별시장애인일자리센터")
    st.divider()
    api_key = st.secrets.get("GOOGLE_API_KEY", "")
    if api_key:
        st.success("✅ API 연결됨")
    else:
        api_key = st.text_input("🔑 Google API 키", type="password", placeholder="AIza...")
    st.divider()
    st.warning("⚠️ AI 결과는 후보안입니다. 최종 확정은 연구자가 결정합니다.")
    st.divider()
    if st.button("🔄 처음부터 다시 시작", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

for s in ["stage1","stage2","stage3","stage4","stage5"]:
    if s not in st.session_state:
        st.session_state[s] = None

st.title("FGI 질적연구 AI 코딩 분석")
st.caption("Braun & Clarke 분석법 | 2~5단계 AI 보조")

if not api_key:
    st.info("👈 왼쪽에 Google API 키를 입력하세요.")
    st.stop()

genai.configure(api_key=api_key)

st.subheader("📄 전사본 입력")
st.caption("참여자명은 P1, P2 등으로 익명화해주세요.")
transcript = st.text_area("전사본", height=250, placeholder="여기에 전사본을 붙여넣으세요...", label_visibility="collapsed")

if not transcript or len(transcript.strip()) < 20:
    st.info("전사본을 입력하면 분석을 시작할 수 있습니다.")
    st.stop()

st.success(f"✅ 전사본 입력 완료: {len(transcript.strip()):,}자")

def run(prompt):
    model = genai.GenerativeModel("gemini-1.5-flash")
    for chunk in model.generate_content(prompt, stream=True):
        if chunk.text:
            yield chunk.text

st.divider()
st.subheader("1️⃣ 개방 코딩")
if st.session_state.stage1 is None:
    if st.button("▶ 1단계 분석 시작", type="primary", use_container_width=True):
        p = "당신은 질적 코딩을 돕는 보조자다. 자료에 없는 해석이나 추론은 하지 않는다.\n\n다음 전사본에 개방코딩을 하라.\n\n[규칙]\n- 의미 단위마다 코드를 부여한다.\n- 각 코드는 자료에 밀착한 짧은 분석적 표지로 작성한다.\n- 코드마다 근거가 된 원문 문장을 함께 제시한다.\n- 자료에 없는 감정, 의도, 원인을 추정하지 않는다.\n- 코드명과 정의는 한국어로 작성하고, 인용은 원문 그대로 제시한다.\n\n[출력형식]\n| 의미 단위 | 코드 | 근거 문장 | 분석 메모 |\n\n[전사본]\n" + transcript.strip()
        with st.spinner("분석 중..."):
            result = st.write_stream(run(p))
        st.session_state.stage1 = result
        st.rerun()
else:
    st.markdown(st.session_state.stage1)
    if st.button("🔄 1단계 다시"):
        for s in ["stage1","stage2","stage3","stage4","stage5"]:
            st.session_state[s] = None
        st.rerun()

if st.session_state.stage1:
    st.divider()
    st.subheader("2️⃣ 코드북 초안")
    if st.session_state.stage2 is None:
        if st.button("▶ 2단계 분석 시작", type="primary", use_container_width=True):
            p = "당신은 질적 코딩을 돕는 보조자다. 제공된 코드와 자료 안에서만 작성한다.\n\n코드북 초안을 작성하라. 각 코드: 코드명, 정의, 포함 기준, 제외 기준, 예시 인용문\n\n[제약]\n- 예시 인용문은 새로 만들지 않는다.\n- 유사 코드 통합 시 근거를 메모로 남긴다.\n\n[출력형식]\n| 코드명 | 정의 | 포함 기준 | 제외 기준 | 예시 인용문 | 화자 |\n\n[1단계 결과]\n" + st.session_state.stage1
            with st.spinner("분석 중..."):
                result = st.write_stream(run(p))
            st.session_state.stage2 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage2)
        if st.button("🔄 2단계 다시"):
            for s in ["stage2","stage3","stage4","stage5"]:
                st.session_state[s] = None
            st.rerun()

if st.session_state.stage2:
    st.divider()
    st.subheader("3️⃣ 주제 묶기")
    if st.session_state.stage3 is None:
        if st.button("▶ 3단계 분석 시작", type="primary", use_container_width=True):
            p = "당신은 질적 코딩을 돕는 보조자다. 자료 범위를 넘어 과장하지 않는다.\n\n코드를 의미가 비슷한 것끼리 묶어라.\n\n[요청]\n- 유사 코드를 묶어 하위주제 후보를 찾는다.\n- 하위주제를 포괄하는 상위주제를 구성한다.\n- 각 주제에 분석적 명칭을 제안한다.\n- 각 주제가 어떤 코드와 인용문에 근거하는지 표시한다.\n- 경계가 모호한 코드는 별도로 표시한다.\n- 주제명은 동사, 관계, 과정이 드러나게 작성한다.\n\n[2단계 결과]\n" + st.session_state.stage2
            with st.spinner("분석 중..."):
                result = st.write_stream(run(p))
            st.session_state.stage3 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage3)
        if st.button("🔄 3단계 다시"):
            for s in ["stage3","stage4","stage5"]:
                st.session_state[s] = None
            st.rerun()

if st.session_state.stage3:
    st.divider()
    st.subheader("4️⃣ 원자료 검토")
    if st.session_state.stage4 is None:
        if st.button("▶ 4단계 분석 시작", type="primary", use_container_width=True):
            p = "당신은 질적 코딩을 돕는 보조자다. 이 결과는 후보안이며 최종 결정은 연구자가 한다.\n\n주제 후보를 전사본과 대조하여 검토하라.\n\n[규칙]\n- 내적 일관성(반복 패턴 대표 여부) 확인\n- 외적 구별성(다른 주제와 구별 여부) 확인\n- 미코딩 발화 중 관련 내용 찾아 표시\n- 패턴 혼재 시 분리 제안, 겹치면 통합 제안, 빈약하면 폐기 제안\n- 자료에 없는 해석 금지\n\n[출력형식]\n| 주제명 | 검토 의견(유지/분리/통합/폐기) | 판단 근거(원문 인용) | 미비점 |\n\n[주제 후보]\n" + st.session_state.stage3 + "\n\n[전사본]\n" + transcript.strip()
            with st.spinner("분석 중..."):
                result = st.write_stream(run(p))
            st.session_state.stage4 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage4)
        if st.button("🔄 4단계 다시"):
            for s in ["stage4","stage5"]:
                st.session_state[s] = None
            st.rerun()

if st.session_state.stage4:
    st.divider()
    st.subheader("5️⃣ 최종 보고서 초안")
    if st.session_state.stage5 is None:
        if st.button("▶ 5단계 분석 시작", type="primary", use_container_width=True):
            p = "당신은 질적 코딩을 돕는 보조자다. 유지 판정된 주제에 한해 설명문을 작성한다.\n\n유지 판정된 주제로 보고서 초안을 작성하라.\n\n[구조]\n① 자료 근거 - 어떤 코드와 인용문이 이 주제를 지지하는가\n② 해석 - 이 인용문들이 보여주는 패턴이 무엇인가\n③ 의미 - 이 패턴이 연구 질문에 대해 무엇을 말해주는가\n\n[출력형식]\n| 주제명 | 자료 근거(코드·인용문) | 해석 | 의미 |\n\n[4단계 결과]\n" + st.session_state.stage4
            with st.spinner("분석 중..."):
                result = st.write_stream(run(p))
            st.session_state.stage5 = result
            st.rerun()
    else:
        st.markdown(st.session_state.stage5)
        if st.button("🔄 5단계 다시"):
            st.session_state.stage5 = None
            st.rerun()

if st.session_state.stage5:
    st.divider()
    st.subheader("💾 결과 다운로드")
    out = "# FGI 분석 결과\n\n"
    for k,n in [("stage1","1단계"),("stage2","2단계"),("stage3","3단계"),("stage4","4단계"),("stage5","5단계")]:
        if st.session_state.get(k):
            out += f"## {n}\n\n{st.session_state[k]}\n\n---\n\n"
    st.download_button("📥 전체 결과 다운로드", data=out.encode("utf-8"), file_name=f"FGI결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md", mime="text/markdown", use_container_width=True, type="primary")
