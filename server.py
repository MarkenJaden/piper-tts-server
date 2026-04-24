"""Minimal HTTP wrapper around Piper TTS CLI."""
import io
import json as jsonlib
import subprocess
import wave
import glob
import os
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

DEFAULT_MODEL = "de_DE-thorsten-high"
MODEL_DIR = "/app/models"


def get_sample_rate(model: str) -> int:
    """Read sample rate from model config JSON."""
    config_path = f"{MODEL_DIR}/{model}.onnx.json"
    try:
        with open(config_path, "r") as f:
            cfg = jsonlib.load(f)
        return cfg.get("audio", {}).get("sample_rate", 22050)
    except (FileNotFoundError, jsonlib.JSONDecodeError):
        return 22050


def synthesize(
    text: str,
    model: str = DEFAULT_MODEL,
    length_scale: float = 1.0,
    noise_scale: float = 0.667,
    noise_w: float = 0.8,
    sentence_silence: float = 0.2,
) -> bytes:
    """Run piper and return WAV bytes."""
    model_path = f"{MODEL_DIR}/{model}.onnx"
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model}")

    cmd = [
        "piper",
        "--model", model_path,
        "--output-raw",
        "--length-scale", str(length_scale),
        "--noise-scale", str(noise_scale),
        "--noise-w", str(noise_w),
        "--sentence-silence", str(sentence_silence),
    ]
    proc = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))

    raw_audio = proc.stdout
    rate = get_sample_rate(model)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(raw_audio)
    return buf.getvalue()


@app.route("/api/tts", methods=["POST"])
def tts_endpoint():
    data = request.get_json(force=True, silent=True) or {}
    text = data.get("text") or request.args.get("text", "")
    model = data.get("model", DEFAULT_MODEL)
    length_scale = float(data.get("length_scale", 1.0))
    noise_scale = float(data.get("noise_scale", 0.667))
    noise_w = float(data.get("noise_w", 0.8))
    sentence_silence = float(data.get("sentence_silence", 0.2))

    if not text:
        return jsonify({"error": "text is required"}), 400

    # Clamp values to safe ranges
    length_scale = max(0.5, min(3.0, length_scale))
    noise_scale = max(0.0, min(1.0, noise_scale))
    noise_w = max(0.0, min(1.0, noise_w))
    sentence_silence = max(0.0, min(2.0, sentence_silence))

    try:
        wav = synthesize(
            text, model,
            length_scale=length_scale,
            noise_scale=noise_scale,
            noise_w=noise_w,
            sentence_silence=sentence_silence,
        )
        return Response(wav, mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/voices", methods=["GET"])
def list_voices():
    models = glob.glob(f"{MODEL_DIR}/*.onnx")
    names = [m.split("/")[-1].replace(".onnx", "") for m in models]
    voices = []
    for name in sorted(names):
        rate = get_sample_rate(name)
        voices.append({"name": name, "sample_rate": rate})
    return jsonify({"voices": voices, "default": DEFAULT_MODEL})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
