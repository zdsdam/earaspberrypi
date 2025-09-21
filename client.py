from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit  # Added for WebSocket support

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")  # Allow frontend to connect

@app.route('/message', methods=['POST'])
def receive_message():
    try:
        data = request.json
        if 'message' in data:
            print(f"Message: {data['message']}")
            # ✅ Send to frontend via socket
            socketio.emit('trap_triggered', {'message': data['message']})
            return jsonify({"status": "Message received"}), 200
        else:
            print("No 'message' field found")
            return jsonify({"error": "No 'message' field found"}), 400
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)  # Replaces app.run()