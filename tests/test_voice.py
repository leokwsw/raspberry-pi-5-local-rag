import wave
from pathlib import Path

from local_rag.voice import VoiceService


def test_voice_disabled_fallback_and_vad(tmp_path: Path) -> None:
    audio = tmp_path / "silence.wav"
    with wave.open(str(audio), "wb") as target:
        target.setparams((1, 2, 16000, 1600, "NONE", "not compressed"))
        target.writeframes(b"\0\0" * 1600)
    voice = VoiceService("missing-whisper", tmp_path / "missing", "missing-piper",
                         tmp_path / "missing")
    assert voice.capabilities() == {"stt": False, "tts": False}
    assert not voice.has_speech(audio)
