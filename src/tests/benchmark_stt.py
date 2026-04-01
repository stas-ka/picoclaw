#!/usr/bin/env python3
"""
benchmark_stt.py — faster-whisper model comparison on SintAItion / OpenClaw
===========================================================================
Compares all locally-cached faster-whisper models across:
  • WER  — Word Error Rate on Russian/German/English TTS-generated sentences
  • RTF  — Real-Time Factor (latency / audio duration)
  • Load — Model load time (cold start)

Test audio is generated via Piper TTS (known reference text → controlled WER).
Falls back to a synthetic tone if Piper is unavailable.

Usage (run on SintAItion):
    python3 tests/benchmark_stt.py               # all cached models, RU sentences
    python3 tests/benchmark_stt.py --lang ru de  # also German
    python3 tests/benchmark_stt.py --model tiny base small large-v3-turbo
    python3 tests/benchmark_stt.py --audio file.ogg --text "reference text"
    python3 tests/benchmark_stt.py --compute int8 float32
    python3 tests/benchmark_stt.py --save results.json

Environment (read from ~/.taris/bot.env if not set):
    FASTER_WHISPER_MODEL   — active model (default: base)
    FASTER_WHISPER_DEVICE  — cpu / cuda (default: cpu)
    FASTER_WHISPER_COMPUTE — int8 / float16 / float32 (default: int8)
    PIPER_BIN              — path to piper binary
    PIPER_MODEL            — path to RU onnx model
    PIPER_MODEL_DE         — path to DE onnx model (optional)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TARIS_HOME = os.environ.get("TARIS_HOME", os.path.expanduser("~/.taris"))

def _env(key: str, default: str) -> str:
    val = os.environ.get(key)
    if val:
        return val
    env_file = Path(TARIS_HOME) / "bot.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k.strip() == key:
                return v.strip()
    return default

FW_DEVICE  = _env("FASTER_WHISPER_DEVICE", "cpu")
FW_THREADS = int(_env("FASTER_WHISPER_THREADS", "4"))
PIPER_BIN  = _env("PIPER_BIN", str(Path(TARIS_HOME) / "piper/piper"))
PIPER_MODEL_RU = _env("PIPER_MODEL", str(Path(TARIS_HOME) / "ru_RU-irina-medium.onnx"))
PIPER_MODEL_DE = _env("PIPER_MODEL_DE", "")

SAMPLE_RATE = 16000

# Candidate models: ordered small→large
CANDIDATE_MODELS = [
    "tiny",
    "base",
    "small",
    "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
]

# Test sentences with known WER reference (Russian focus, bot's primary language)
TEST_SENTENCES = {
    "ru": [
        ("добавь событие встреча с врачом в четверг в четырнадцать часов",
         "добавь событие встреча с врачом в четверг в четырнадцать часов"),
        ("покажи мне мои задачи на сегодня пожалуйста",
         "покажи мне мои задачи на сегодня пожалуйста"),
        ("какая погода сейчас в берлине",
         "какая погода сейчас в берлине"),
        ("установи напоминание завтра в восемь часов утра",
         "установи напоминание завтра в восемь часов утра"),
    ],
    "de": [
        ("füge einen Termin für Donnerstag um vierzehn Uhr hinzu",
         "füge einen Termin für Donnerstag um vierzehn Uhr hinzu"),
        ("zeig mir meine Aufgaben für heute bitte",
         "zeig mir meine Aufgaben für heute bitte"),
    ],
    "en": [
        ("add a meeting with the doctor on Thursday at two pm",
         "add a meeting with the doctor on thursday at two pm"),
        ("show me my tasks for today please",
         "show me my tasks for today please"),
    ],
}


# ---------------------------------------------------------------------------
# Audio generation
# ---------------------------------------------------------------------------
def _piper_model_for_lang(lang: str) -> str | None:
    if lang == "ru":
        p = Path(PIPER_MODEL_RU)
        return str(p) if p.exists() else None
    if lang == "de":
        p = Path(PIPER_MODEL_DE) if PIPER_MODEL_DE else None
        if p and p.exists():
            return str(p)
        # Try common location
        for pat in ["*.de*.onnx", "de_DE*.onnx"]:
            matches = list(Path(TARIS_HOME).glob(pat))
            if matches:
                return str(matches[0])
    return None


def _tts_piper(text: str, lang: str) -> bytes | None:
    """Generate speech via Piper TTS. Returns WAV bytes or None."""
    piper = Path(PIPER_BIN)
    if not piper.exists():
        return None
    model = _piper_model_for_lang(lang)
    if not model:
        return None
    try:
        proc = subprocess.run(
            [str(piper), "--model", model, "--output_raw"],
            input=text.encode(),
            capture_output=True, timeout=30,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        # Piper outputs raw 16-bit LE PCM at 22050 Hz → resample to 16000
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as f:
            f.write(proc.stdout)
            raw_path = f.name
        cmd = [
            "ffmpeg", "-y",
            "-f", "s16le", "-ar", "22050", "-ac", "1", "-i", raw_path,
            "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le",
            "-loglevel", "error", "-",
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        os.unlink(raw_path)
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None


def _tts_fallback(text: str) -> bytes:
    """Generate 2s silence as a fallback (for load-time benchmark only)."""
    import numpy as np
    return (np.zeros(SAMPLE_RATE * 2, dtype=np.int16)).tobytes()


def _ogg_to_pcm(ogg_path: str) -> tuple[bytes, float]:
    cmd = [
        "ffmpeg", "-y", "-i", ogg_path,
        "-ar", str(SAMPLE_RATE), "-ac", "1", "-f", "s16le",
        "-loglevel", "error", "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.decode()[:200]}")
    pcm = result.stdout
    return pcm, len(pcm) / (SAMPLE_RATE * 2)


def _wer(ref: str, hyp: str) -> float:
    ref_w = ref.lower().split()
    hyp_w = hyp.lower().split()
    if not ref_w:
        return 0.0 if not hyp_w else 1.0
    n, m = len(ref_w), len(hyp_w)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            dp[i][j] = dp[i-1][j-1] if ref_w[i-1] == hyp_w[j-1] else \
                       1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    return dp[n][m] / n


# ---------------------------------------------------------------------------
# Benchmark one model
# ---------------------------------------------------------------------------
def _get_cached_models() -> list[str]:
    """Return faster-whisper models that are locally cached in HuggingFace hub."""
    cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    cached = []
    for m in CANDIDATE_MODELS:
        # Standard HuggingFace cache: models--<org>--<name>
        safe = m.replace("/", "--").replace(":", "--")
        if any(d.name.startswith(f"models--{safe}") or d.name == f"models--Systran--faster-whisper-{safe}"
               for d in cache_dir.iterdir() if d.is_dir()):
            cached.append(m)
    return cached


def benchmark_model(
    model_id: str,
    sentences: list[tuple[str, str]],
    lang: str,
    compute_type: str,
    verbose: bool = False,
) -> dict:
    """Benchmark a single model+compute_type combo. Returns result dict."""
    import numpy as np
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return {"model": model_id, "compute_type": compute_type, "error": "faster-whisper not installed"}

    result = {
        "model": model_id,
        "compute_type": compute_type,
        "device": FW_DEVICE,
        "lang": lang,
        "load_s": 0.0,
        "sentences": [],
        "avg_wer": None,
        "avg_rtf": 0.0,
        "avg_latency_s": 0.0,
        "error": None,
    }

    # Load model
    t0 = time.time()
    try:
        model = WhisperModel(
            model_id, device=FW_DEVICE, compute_type=compute_type,
            num_workers=1, cpu_threads=FW_THREADS,
        )
        result["load_s"] = round(time.time() - t0, 2)
    except Exception as e:
        result["error"] = f"load failed: {e}"
        return result

    wers, rtfs, lats = [], [], []
    for i, (text, ref) in enumerate(sentences):
        # Generate audio
        pcm = _tts_piper(text, lang)
        if pcm is None:
            pcm = _tts_fallback(text)
            ref = None  # can't compute WER on silence

        audio_np = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        duration = len(pcm) / (SAMPLE_RATE * 2)

        t1 = time.time()
        try:
            segments, info = model.transcribe(
                audio_np, language=lang, beam_size=3,
                vad_filter=True, condition_on_previous_text=False,
            )
            hyp = " ".join(seg.text.strip() for seg in segments).strip()
            hyp = re.sub(r"\s+", " ", hyp.lower().strip(" .!?,"))
        except Exception as e:
            hyp = ""
            if verbose:
                print(f"    [ERR] {e}")
        latency = round(time.time() - t1, 3)
        rtf = round(latency / duration, 3) if duration > 0 else 0

        wer = _wer(ref, hyp) if ref else None
        if wer is not None:
            wers.append(wer)
        rtfs.append(rtf)
        lats.append(latency)

        entry = {
            "ref": ref,
            "hyp": hyp,
            "wer": round(wer, 3) if wer is not None else None,
            "latency_s": latency,
            "rtf": rtf,
            "duration_s": round(duration, 2),
        }
        result["sentences"].append(entry)
        if verbose:
            w = f"{wer:.0%}" if wer is not None else "  -"
            print(f"    [{i+1}] RTF={rtf:.2f}  WER={w}  → {hyp[:55]}")

    result["avg_wer"]      = round(sum(wers) / len(wers), 3) if wers else None
    result["avg_rtf"]      = round(sum(rtfs) / len(rtfs), 3) if rtfs else 0
    result["avg_latency_s"] = round(sum(lats) / len(lats), 3) if lats else 0
    del model  # release VRAM
    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def print_results(all_results: list[dict], langs: list[str]) -> None:
    print(f"\n{'='*90}")
    print(f"{'Model':<48} {'Compute':<9} {'Load':>6} {'Lat':>6} {'RTF':>6} {'WER':>6}  Verdict")
    print("-" * 90)
    for r in all_results:
        if r.get("error"):
            print(f"  {r['model']:<46} {'':9} ERROR: {r['error'][:40]}")
            continue
        wer_str  = f"{r['avg_wer']:.0%}" if r['avg_wer'] is not None else "  n/a"
        rtf_ok   = r['avg_rtf'] < 1.0   # faster than real-time
        wer_ok   = r['avg_wer'] is not None and r['avg_wer'] < 0.20
        verdict  = ("✅ fast+accurate" if rtf_ok and wer_ok
                    else "⚠️  slow" if not rtf_ok and wer_ok
                    else "⚠️  inaccurate" if rtf_ok and not wer_ok
                    else "⚠️  slow+inaccurate" if not rtf_ok
                    else "—")
        label = r['model'].replace("mobiuslabsgmbh/", "")
        print(f"  {label:<46} {r['compute_type']:<9} {r['load_s']:>5.1f}s {r['avg_latency_s']:>5.2f}s "
              f"{r['avg_rtf']:>5.2f} {wer_str:>6}  {verdict}")
    print("=" * 90)

    # Recommendation
    valid = [r for r in all_results if not r.get("error") and r["avg_rtf"] > 0]
    if not valid:
        return
    fast_and_accurate = [r for r in valid
                         if r["avg_rtf"] < 1.0 and (r["avg_wer"] or 1) < 0.20]
    best_wer   = min(valid, key=lambda r: r["avg_wer"] or 1)
    best_speed = min(valid, key=lambda r: r["avg_rtf"])
    recommend  = min(fast_and_accurate, key=lambda r: r["avg_wer"] or 1) if fast_and_accurate \
                 else best_wer

    print(f"\n🎯 Best WER:      {best_wer['model'].replace('mobiuslabsgmbh/','')} "
          f"({best_wer['avg_wer']:.0%} WER)")
    print(f"⚡ Fastest:       {best_speed['model'].replace('mobiuslabsgmbh/','')} "
          f"(RTF {best_speed['avg_rtf']:.2f})")
    print(f"✅ Recommended:   {recommend['model'].replace('mobiuslabsgmbh/','')} "
          f"— {recommend['avg_wer']:.0%} WER, RTF {recommend['avg_rtf']:.2f}, "
          f"load {recommend['load_s']:.1f}s")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="faster-whisper model benchmark")
    parser.add_argument("--model",   nargs="+", help="Model IDs to benchmark (default: all cached)")
    parser.add_argument("--lang",    nargs="+", default=["ru"], help="Languages (ru de en)")
    parser.add_argument("--compute", nargs="+", default=["int8"], help="Compute types (int8 float32)")
    parser.add_argument("--audio",   help="OGG file to transcribe (overrides TTS generation)")
    parser.add_argument("--text",    help="Reference text for --audio")
    parser.add_argument("--save",    metavar="PATH", help="Save JSON results to this file")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    # Determine models to test
    if args.model:
        models = args.model
    else:
        models = _get_cached_models()
        if not models:
            # Fallback to just the active model
            models = [_env("FASTER_WHISPER_MODEL", "base")]

    print(f"\n🎙  faster-whisper STT Benchmark — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"   Device:   {FW_DEVICE}  threads={FW_THREADS}")
    print(f"   Models:   {', '.join(m.replace('mobiuslabsgmbh/','') for m in models)}")
    print(f"   Langs:    {', '.join(args.lang)}")
    print(f"   Compute:  {', '.join(args.compute)}")

    # Check Piper availability
    piper_ok = Path(PIPER_BIN).exists()
    if not piper_ok:
        print(f"   [WARN] Piper not found at {PIPER_BIN} — using silence (no WER)")
    else:
        print(f"   Piper:    {PIPER_BIN}")

    all_results = []

    if args.audio:
        # Single-file mode
        pcm, dur = _ogg_to_pcm(args.audio)
        print(f"\n   Audio: {args.audio}  ({dur:.1f}s)")
        sentences = [(args.text or "", args.text or "")] if args.text else [("", "")]
    else:
        sentences = None  # will use TEST_SENTENCES per lang

    for lang in args.lang:
        if args.audio:
            sents = sentences
        else:
            sents = TEST_SENTENCES.get(lang, [])
            if not sents:
                print(f"\n[SKIP] No test sentences for lang={lang}")
                continue

        print(f"\n── Language: {lang.upper()} ({len(sents)} sentences) ──────────────────────────────")

        for compute in args.compute:
            for model_id in models:
                label = model_id.replace("mobiuslabsgmbh/", "")
                print(f"\n  [{label}  {compute}]  loading…", end=" ", flush=True)
                r = benchmark_model(model_id, sents, lang, compute, verbose=args.verbose)
                if r.get("error"):
                    print(f"ERROR: {r['error']}")
                else:
                    print(f"load={r['load_s']:.1f}s  RTF={r['avg_rtf']:.2f}  "
                          f"WER={r['avg_wer']:.0%}" if r['avg_wer'] is not None
                          else f"load={r['load_s']:.1f}s  RTF={r['avg_rtf']:.2f}  WER=n/a")
                all_results.append(r)

    print_results(all_results, args.lang)

    # Save
    if args.save or not args.audio:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        path = args.save or str(Path(TARIS_HOME) / "tests" / f"stt_benchmark_{ts}.json")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w") as f:
            json.dump({"timestamp": datetime.now(timezone.utc).isoformat(),
                       "device": FW_DEVICE, "threads": FW_THREADS,
                       "results": all_results}, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved → {path}")


if __name__ == "__main__":
    main()
