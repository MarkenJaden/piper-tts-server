"""Minimal HTTP wrapper around Piper TTS CLI."""
import io
import subprocess
import wave
from flask import Flask, request, Response, jsonify

app = Flask(__name__)

DEFAULT_MODEL = "de_DE-thorsten-high"
MODEL_DIR = "/app/models"


def synthesize(text: str, model: str = DEFAULT_MODEL, rate: int = 22050) -> bytes:
    """Run piper and return WAV bytes."""
    model_path = f"{MODEL_DIR}/{model}.onnx"
    cmd = [
        "piper",
        "--model", model_path,
        "--output-raw",
    ]
    proc = subprocess.run(
        cmd,
        input=text.encode("utf-8"),
        capture_output=True,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))

    raw_audio = proc.stdout
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
    if not text:
        return jsonify({"error": "text is required"}), 400
    try:
        wav = synthesize(text, model)
        return Response(wav, mimetype="audio/wav")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/voices", methods=["GET"])
def list_voices():
    import glob
    models = glob.glob(f"{MODEL_DIR}/*.onnx")
    names = [m.split("/")[-1].replace(".onnx", "") for m in models]
    return jsonify({"voices": names, "default": DEFAULT_MODEL})


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
