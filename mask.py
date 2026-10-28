"""전사본 개인정보 가리기 — 참여자 이름 목록(P1, P2…)과 pii-cleaner 자동 찾기를 함께 쓴다.
모두 이 서버 안에서만 처리한다(자동 찾기 모델도 로컬, 인터넷 안 씀). 자동 찾기는 놓치는 것이 있어 사람이 결과를 확인하고 적용한다."""
import os
import re
import sys
from pathlib import Path

PII_REPO = Path(os.environ.get("PII_CLEANER_REPO", "/srv/projects/pii-cleaner/repo"))

# 화면 이름 → pii-cleaner 종류 코드, 바꿀 말
AUTO_TYPES = {
    "이름": ("PERSON", "이름"),
    "전화번호": ("PHONE", "[전화번호]"),
    "주민등록번호": ("RRN", "[주민등록번호]"),
    "이메일": ("EMAIL", "[이메일]"),
    "주소": ("ADDRESS", "[주소]"),
    "계좌번호": ("ACCOUNT", "[계좌번호]"),
    "날짜": ("DATE", "[날짜]"),
    "URL": ("URL", "[URL]"),
    "IP 주소": ("IP", "[IP]"),
}
DEFAULT_AUTO = ["이름", "전화번호", "주민등록번호", "이메일", "주소", "계좌번호"]

# 이름만 부를 때(민수 씨, 하늘아)는 뒤에 호칭이 올 때만 가린다 — '하늘' 같은 낱말을 잘못 가리지 않도록
CALLED = r"(?=\s*(?:씨|님|선생|샘)|(?:아|야)(?![가-힣]))"


def load_detector():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    if str(PII_REPO) not in sys.path:
        sys.path.insert(0, str(PII_REPO))
    from app.core.detector import PIIDetector
    det = PIIDetector(PII_REPO / "models" / "schift-ko-pii-v7")
    det.initialize()
    return det


def parse_names(text):
    """한 줄(또는 쉼표)에 한 명. '이름=바꿀 말' 이면 그 말로, 아니면 적은 순서대로 P1, P2…"""
    out, n = [], 0
    for item in re.split(r"[\n,]", text or ""):
        item = item.strip()
        if not item:
            continue
        name, _, label = item.partition("=")
        name = re.sub(r"\s+", "", name)
        if len(name) < 2:
            continue
        if not label.strip():
            n += 1
        out.append((name, label.strip() or f"P{n}"))
    return out


def _name_patterns(name):
    pats = [re.escape(name[0]) + r"\s?" + re.escape(name[1:])]  # '정하늘'·'정 하늘'
    if len(name) == 3:
        pats.append(re.escape(name[1:]) + CALLED)  # '하늘 씨', '민수야'
    return [re.compile(r"(?<![가-힣])" + p) for p in pats]


def find(text, names, auto, detector=None):
    """바꿀 곳 목록(spans)과 확인용 표(rows)를 만든다. span = (시작, 끝, 묶음 번호)."""
    spans = []  # (start, end, key, priority)
    groups = {}  # key -> {원래, 바꿀 말, 종류}

    def group(value, label, kind):
        key = f"{kind}|{value}"
        groups.setdefault(key, {"원래": value, "바꿀 말": label, "종류": kind})
        return key

    for name, label in names:
        for pat in _name_patterns(name):
            for m in pat.finditer(text):
                spans.append((m.start(), m.end(), group(m.group(), label, "참여자"), 0))

    codes = {AUTO_TYPES[a][0]: AUTO_TYPES[a][1] for a in auto}
    if detector is not None and codes:
        listed = {n: l for n, l in names}
        person_no = {}
        for d in detector.detect(text, set(codes)):
            value = text[d.start:d.end]
            if d.type == "PERSON":
                bare = re.sub(r"\s+", "", value)
                label = listed.get(bare) or next((l for n, l in listed.items() if len(n) == 3 and bare == n[1:]), None)
                if not label:
                    label = person_no.setdefault(bare, f"[이름{len(person_no) + 1}]")
            else:
                label = codes.get(d.type, f"[{d.type}]")
            spans.append((d.start, d.end, group(value, label, "자동:" + {v[0]: k for k, v in AUTO_TYPES.items()}.get(d.type, d.type)), 1))

    # 겹치면 목록 쪽, 그다음 긴 쪽을 남긴다
    spans.sort(key=lambda s: (s[3], -(s[1] - s[0]), s[0]))
    taken, kept = [], []
    for s in spans:
        if all(s[1] <= a or s[0] >= b for a, b in taken):
            taken.append((s[0], s[1]))
            kept.append((s[0], s[1], s[2]))
    kept.sort()

    rows = {}
    for start, end, key in kept:
        r = rows.setdefault(key, dict(groups[key], 가리기=True, 횟수=0, 예시=""))
        r["횟수"] += 1
        if not r["예시"]:
            r["예시"] = "…" + text[max(0, start - 12):end + 12].replace("\n", " ") + "…"
    order = ["가리기", "원래", "바꿀 말", "종류", "횟수", "예시"]
    return kept, [dict(key=k, **{c: r[c] for c in order}) for k, r in rows.items()]


def apply(text, spans, rows):
    """표에서 체크된 줄만, 표의 '바꿀 말'로 바꾼다."""
    use = {r["key"]: r["바꿀 말"] for r in rows if r["가리기"]}
    out, pos = [], 0
    for start, end, key in spans:
        if key in use:
            out.append(text[pos:start])
            out.append(use[key])
            pos = end
    out.append(text[pos:])
    return "".join(out)
