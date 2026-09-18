import logging
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, request, jsonify
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


def create_app():
    app = Flask(__name__)
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

    return app, socketio


app, socketio = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    socketio.run(app, host="0.0.0.0", port=5000)
