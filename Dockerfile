FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget ca-certificates libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# Install piper
RUN pip install --no-cache-dir piper-tts flask gunicorn

# Download German voice model (thorsten high quality)
RUN mkdir -p /app/models && \
    wget -q -O /app/models/de_DE-thorsten-high.onnx \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx" && \
    wget -q -O /app/models/de_DE-thorsten-high.onnx.json \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/high/de_DE-thorsten-high.onnx.json"

# Download a second German voice for comparison (karlsson medium)
RUN wget -q -O /app/models/de_DE-karlsson-low.onnx \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/karlsson/low/de_DE-karlsson-low.onnx" && \
    wget -q -O /app/models/de_DE-karlsson-low.onnx.json \
      "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/karlsson/low/de_DE-karlsson-low.onnx.json"

WORKDIR /app
COPY server.py /app/server.py

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "60", "server:app"]
