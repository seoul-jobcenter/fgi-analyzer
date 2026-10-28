"""음성 파일을 scv 의 GPU whisper(/opt/whisper-cuda)로 글자로 바꾼다.
음성은 서버 밖으로 나가지 않고, 끝나면 임시 파일을 모두 지운다. GPU 가 작아 한 번에 하나씩만 돌린다."""
import fcntl
import os
import re
import subprocess
import tempfile

WHISPER_CLI = os.environ.get("WHISPER_CLI", "/opt/whisper-cuda/src/build/bin/whisper-cli")
WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "/opt/whisper-cuda/models/ggml-large-v3-turbo.bin")
LOCK_FILE = os.path.join(tempfile.gettempdir(), "fgi-whisper.lock")
AUDIO_TYPES = ["mp3", "m4a", "wav", "aac", "ogg", "oga", "opus", "flac", "wma", "amr", "3gp", "webm", "mp4", "mov"]

# whisper 가 한 구간씩 내놓는 줄: [00:01:02.340 --> 00:01:05.120]  글자
SEGMENT = re.compile(r"^\[(\d+):(\d+):(\d+(?:\.\d+)?) --> (\d+):(\d+):(\d+(?:\.\d+)?)\]")


def clock(sec):
    sec = int(sec)
    return f"{sec // 3600}:{sec % 3600 // 60:02d}:{sec % 60:02d}" if sec >= 3600 else f"{sec // 60}:{sec % 60:02d}"


def _open_lock():
    # 읽기로만 연다. /tmp 에서는 남이 만든 파일을 '없으면 만들기'로 열 수 없어 있으면 그냥 연다
    try:
        return os.open(LOCK_FILE, os.O_RDONLY)
    except FileNotFoundError:
        return os.open(LOCK_FILE, os.O_RDONLY | os.O_CREAT, 0o644)


def transcribe(filename, data, on_progress=lambda ratio, msg: None):
    """(글자, 녹음 길이 초)를 돌려준다."""
    with tempfile.TemporaryDirectory(prefix="fgi-stt-") as tmp:
        src = os.path.join(tmp, "in" + os.path.splitext(filename)[1].lower())
        with open(src, "wb") as f:
            f.write(data)
        wav = os.path.join(tmp, "in.wav")
        on_progress(0.0, "음성 파일 준비 중…")
        try:
            subprocess.run(
                ["ffmpeg", "-nostdin", "-loglevel", "error", "-y", "-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
                check=True, timeout=1800, capture_output=True,
            )
        except subprocess.CalledProcessError:
            raise ValueError("음성 파일을 읽지 못했습니다. 다른 형식(mp3·m4a·wav)으로 저장해 다시 올려 주세요.")
        os.remove(src)
        duration = max((os.path.getsize(wav) - 44) / 32000, 1)  # 16kHz·16bit·모노 = 초당 32000바이트

        with os.fdopen(_open_lock()) as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                on_progress(0.0, "다른 사람의 변환이 끝나기를 기다리는 중…")
                fcntl.flock(lock, fcntl.LOCK_EX)
            on_progress(0.0, f"글로 바꾸는 중… 0:00 / {clock(duration)}")
            out = os.path.join(tmp, "out")
            proc = subprocess.Popen(
                [WHISPER_CLI, "-m", WHISPER_MODEL, "-f", wav, "-l", "ko", "-otxt", "-of", out],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
            for line in proc.stdout:
                m = SEGMENT.match(line.strip())
                if m:
                    end = int(m[4]) * 3600 + int(m[5]) * 60 + float(m[6])
                    on_progress(min(end / duration, 1.0), f"글로 바꾸는 중… {clock(end)} / {clock(duration)}")
            if proc.wait() != 0:
                raise RuntimeError("음성 인식이 중간에 멈췄습니다. 잠시 뒤 다시 시도해 주세요.")

        with open(out + ".txt", encoding="utf-8") as f:
            text = f.read()
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not text:
        raise ValueError("음성에서 말소리를 찾지 못했습니다.")
    return text, duration
