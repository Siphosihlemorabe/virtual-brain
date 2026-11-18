# /// script
# requires-python = ">=3.10"
# dependencies = ["faster-whisper>=1.0", "soundcard>=0.4", "numpy"]
# ///
"""Self-test helper (docs/validation/self-test-protocol.md §4). Not part of the app.

Record what the computer is playing, then transcribe it locally with faster-whisper.
Outputs stay in data/validation/ (git-ignored): course content must never be committed.

    uv run tools/validation/transcribe.py record  lecture1
    uv run tools/validation/transcribe.py transcribe data/validation/lecture1.wav
"""
import argparse
import json
import sys
import time
import wave
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "data" / "validation"
RATE = 16000  # Whisper works at 16 kHz mono
AWS_TERMS = ("AWS, Amazon Web Services, S3, EC2, IAM, VPC, Lambda, CloudFront, RDS, Aurora, DynamoDB, "
             "CloudWatch, CloudTrail, Route 53, EBS, EFS, Glacier, ELB, Auto Scaling, KMS, Shield, WAF, "
             "Trusted Advisor, Cost Explorer, Organizations, availability zone, region, edge location.")


def record(name: str):
    import numpy as np
    import soundcard as sc

    speaker = sc.default_speaker()
    loopback = sc.get_microphone(id=str(speaker.name), include_loopback=True)
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.wav"
    print(f"Recording what plays on '{speaker.name}'. Start the video, then press Ctrl+C to stop.")
    chunks = []
    t0 = time.time()
    try:
        with loopback.recorder(samplerate=RATE, channels=1) as rec:
            while True:
                chunks.append(rec.record(numframes=RATE))  # one second at a time
                print(f"\r  {int(time.time() - t0)} s", end="", flush=True)
    except KeyboardInterrupt:
        pass
    audio = np.concatenate(chunks) if chunks else np.zeros((0, 1))
    pcm = (np.clip(audio[:, 0], -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes(pcm.tobytes())
    print(f"\nSaved {path} ({len(pcm) / RATE:.0f} s). Next: transcribe it.")


def mmss(s: float) -> str:
    return f"{int(s // 60):02d}:{int(s % 60):02d}"


def transcribe(audio: Path, model_size: str, delete_audio: bool):
    from faster_whisper import WhisperModel

    if not audio.exists():
        sys.exit(f"No such file: {audio}")
    t0 = time.time()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    load_s = time.time() - t0
    t1 = time.time()
    segments, info = model.transcribe(str(audio), language="en", vad_filter=True, beam_size=5,
                                      initial_prompt=AWS_TERMS)
    lines = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments]
    work_s = time.time() - t1

    OUT.mkdir(parents=True, exist_ok=True)
    stem = OUT / audio.stem
    stem.with_suffix(".txt").write_text(
        "\n".join(f"[{mmss(l['start'])}–{mmss(l['end'])}] {l['text']}" for l in lines) + "\n", encoding="utf-8")
    stats = {"audio_seconds": round(info.duration, 1), "model": model_size, "model_load_seconds": round(load_s, 1),
             "transcribe_seconds": round(work_s, 1),
             "times_faster_than_real_time": round(info.duration / work_s, 1) if work_s else None,
             "lines": len(lines)}
    stem.with_suffix(".json").write_text(json.dumps({"stats": stats, "lines": lines}, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(f"Transcript: {stem.with_suffix('.txt')}")
    if delete_audio:
        audio.unlink()
        print(f"Deleted {audio}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record", help="record what the computer is playing")
    r.add_argument("name", help="file name without extension, e.g. lecture1")
    t = sub.add_parser("transcribe", help="transcribe a recording locally")
    t.add_argument("audio", type=Path)
    t.add_argument("--model", default="small", help="tiny, base, small (default), medium")
    t.add_argument("--delete-audio", action="store_true", help="delete the recording after transcribing")
    a = p.parse_args()
    if a.cmd == "record":
        record(a.name)
    else:
        transcribe(a.audio, a.model, a.delete_audio)


if __name__ == "__main__":
    main()
