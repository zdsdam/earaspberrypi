import logging
import os
from datetime import datetime, timezone
from threading import Lock
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, abort
from flask_socketio import SocketIO


logger = logging.getLogger(__name__)


def normalize_event(data):
    if not isinstance(data, dict):
        raise ValueError("Payload must be a JSON object")
    normalized = {}
    for field in ("device_id", "event", "location"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("{} must be a non-empty string".format(field))
        normalized[field] = value.strip()

    # Compatibility with the Pico firmware already deployed in this repository.
    if normalized["event"] not in ("trap_triggered", "blinding"):
        raise ValueError("Unsupported event")
    normalized["event"] = "trap_triggered"
    sequence = data.get("sequence")
    if type(sequence) is not int or sequence < 1:
        raise ValueError("sequence must be a positive integer")
    normalized["sequence"] = sequence
    return normalized


def create_app(frontend_dir=None):
    app = Flask(__name__, static_folder=None)
    frontend = Path(frontend_dir or Path(__file__).parent / "frontend").resolve()
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    seen = set()
    seen_lock = Lock()

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    @app.post("/message")
    def receive_message():
        try:
            payload = normalize_event(request.get_json(silent=True))
        except ValueError as error:
            logger.warning("Invalid event: %s", error)
            return jsonify({"error": str(error)}), 400

        key = (payload["device_id"], payload["sequence"])
        try:
            # Serialize duplicate checks and emission for concurrent HTTP retries.
            with seen_lock:
                if key in seen:
                    logger.info("Duplicate event device_id=%s sequence=%s", *key)
                    return jsonify({"status": "duplicate"}), 200
                payload["received_at"] = datetime.now(timezone.utc).isoformat()
                socketio.emit("trap_triggered", payload)
                seen.add(key)
            logger.info("Received event: %s", payload)
            return jsonify({"status": "received", "event": payload}), 200
        except Exception:
            logger.exception("Failed to broadcast event device_id=%s sequence=%s", *key)
            return jsonify({"error": "Internal Server Error"}), 500

    @socketio.on("connect")
    def on_connect(auth=None):
        logger.info("Socket.IO client connected: %s", request.sid)

    @socketio.on("disconnect")
    def on_disconnect(reason=None):
        logger.info("Socket.IO client disconnected: %s reason=%s", request.sid, reason)

    @app.get("/")
    @app.get("/<path:path>")
    def serve_frontend(path=""):
        # Never turn API mistakes or missing assets into successful HTML responses.
        if path.split("/", 1)[0] in ("message", "health", "socket.io"):
            abort(404)
        candidate = (frontend / path).resolve()
        if frontend not in candidate.parents and candidate != frontend:
            abort(404)
        if path and candidate.is_file():
            return send_from_directory(frontend, path)
        if path.startswith("assets/") or Path(path).suffix:
            abort(404)
        if not (frontend / "index.html").is_file():
            return jsonify({"error": "Frontend missing; run copy_frontend.py after npm run build"}), 503
        return send_from_directory(frontend, "index.html", max_age=0)

    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # port is 5050 instead of 5000 because mac os uses 5000 for airplay, switch this if needed
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "5050")))
