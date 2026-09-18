HOW TO USE
1. Install requirements

Make sure Flask is installed:
```
pip install flask flask-socketio
```

2. Set up the Raspberry Pi Pico W
  1. Open Thonny.
  2. Connect the Raspberry Pi Pico W to your computer.
  3. Open main.py and edit these fields:
    WIFI_SSID = "YOUR_WIFI_NAME"
    WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
    SERVER_HOST = "YOUR_COMPUTER_IPV4_ADDRESS"
    SERVER_PORT = 5000
    DEVICE_ID = "pico-w-01"
    (find your IP by running ipconfig in Command Prompt; use the IPv4 Address).
  4. Upload main.py to the Pico W.

The Pico firmware now sends structured events such as:
```json
{"device_id": "pico-w-01", "event": "blinding", "location": "Armoury", "sequence": 1}
```
GPIO 14 is Armoury and GPIO 10 is Storage, both active-low with pull-ups.
A press must remain stable for 50 ms; holding a button does not repeat events.
A button held during startup must be released before it can trigger.
Sequence numbers start at 1 after each boot and increase once per event,
including failed events. All retries reuse the same payload and sequence.
Wi-Fi connection attempts time out after 10 seconds. Idle reconnect attempts
are spaced 5 seconds apart. Each event gets at most 3 attempts with a 500 ms
retry delay and a 5 second HTTP socket timeout. Non-transient 4xx responses
are not retried. Responses are closed even on HTTP errors.

Use Pico W MicroPython firmware with a `urequests` module supporting the
`timeout` keyword (current MicroPython requests implementation). Network calls
are synchronous: short presses during connection attempts or HTTP requests can
be missed. Failed events are logged and dropped; there is no persistent queue.
Retries can deliver duplicates if the server processes a request but its reply
is lost; sequence numbers allow a future server update to deduplicate them.

**Integration pending:** `client.py` is intentionally unchanged and still
requires a `message` field. It will return HTTP 400 for these new structured
events until the Flask server is updated. The manual request below still tests
the existing server, but the new firmware cannot yet trigger the frontend.

3. Run the client.py on your computer
  1. Open Command Prompt in the project folder
  2. Run:
     ```
     python client.py
     ```
  3. Keep https://zdsdam.github.io/easound open in your browser.

4. If the Pico setup fails
If you can’t upload main.py or connect the Pico:
  1. Make sure client.py is already running.
  2. In a new Command Prompt window, send a test message:
     ```
     curl -X POST http://127.0.0.1:5000/message -H "Content-Type: application/json" -d "{\"message\": \"Blinding: Armoury!\"}"
     ```

   
   
