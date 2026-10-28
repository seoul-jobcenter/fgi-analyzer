"""올린 전사본 파일(txt·md·hwpx·docx·doc)에서 글자만 뽑는다. 파일은 메모리에서만 다루고 저장하지 않는다."""
import io
import os
import re
import subprocess
import tempfile
import zipfile
import xml.etree.ElementTree as ET

ACCEPT = ["txt", "md", "hwpx", "docx", "doc"]
MAX_XML_BYTES = 50 * 1024 * 1024  # 압축을 푼 XML 한 개의 상한(압축 폭탄 방지)


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _decode(data):
    for enc in ("utf-8-sig", "cp949", "utf-16"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("글자 인코딩을 알 수 없습니다. UTF-8 로 저장해 다시 올려 주세요.")


def _zip_xml(zf, name):
    if zf.getinfo(name).file_size > MAX_XML_BYTES:
        raise ValueError("문서가 너무 큽니다.")
    return ET.fromstring(zf.read(name))


def _hwpx(data):
    zf = zipfile.ZipFile(io.BytesIO(data))
    sections = [n for n in zf.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n)]
    if not sections:
        raise ValueError("hwpx 본문을 찾지 못했습니다.")
    lines = []
    for name in sorted(sections, key=lambda n: int(re.search(r"\d+", n).group())):
        for p in _zip_xml(zf, name).iter():
            if _local(p.tag) != "p":
                continue
            # 문단 바로 아래 글자만 모은다(표 안 문단은 따로 돌 때 나온다)
            lines.append("".join(
                "".join(t.itertext())
                for run in p if _local(run.tag) == "run"
                for t in run if _local(t.tag) == "t"
            ))
    return "\n".join(lines)


def _docx(data):
    zf = zipfile.ZipFile(io.BytesIO(data))
    root = _zip_xml(zf, "word/document.xml")
    return "\n".join(
        "".join(t.text or "" for t in p.iter() if _local(t.tag) == "t")
        for p in root.iter() if _local(p.tag) == "p"
    )


def _doc(data):
    # 옛 워드(.doc)는 서버의 LibreOffice 로 글자 파일로 바꾼다. 실행마다 임시 프로필을 쓰고 끝나면 지운다.
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "in.doc")
        with open(src, "wb") as f:
            f.write(data)
        subprocess.run(
            ["soffice", f"-env:UserInstallation=file://{tmp}/profile", "--headless",
             "--convert-to", "txt:Text (encoded):UTF8", "--outdir", tmp, src],
            check=True, timeout=60, capture_output=True,
        )
        with open(os.path.join(tmp, "in.txt"), "rb") as f:
            return _decode(f.read())


def extract_text(filename, data):
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext in ("txt", "md"):
        text = _decode(data)
    elif ext == "hwpx":
        text = _hwpx(data)
    elif ext == "docx":
        text = _docx(data)
    elif ext == "doc":
        text = _doc(data)
    else:
        raise ValueError(f"{ext or '확장자 없는'} 파일은 읽을 수 없습니다. ({', '.join(ACCEPT)})")
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()
    if not text:
        raise ValueError("파일에서 글자를 찾지 못했습니다.")
    return text
