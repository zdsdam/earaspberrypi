HOW TO USE
1. Install requirements

Activate the existing virtual environment and install the server dependencies:
```
source .venv/bin/activate
python -m pip install -r requirements.txt
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
The server accepts `trap_triggered` and the existing firmware's `blinding`
alias, normalizing both to `trap_triggered`. Device ID and location must be
non-empty strings; sequence must be a positive integer (not a boolean).
Strings are trimmed and extra fields are ignored. Invalid or malformed JSON
returns HTTP 400 without broadcasting.

Accepted events receive a UTC ISO 8601 `received_at` timestamp and are broadcast
as a Socket.IO `trap_triggered` event containing the four normalized fields plus
the timestamp. HTTP 200 returns `{"status": "received", "event": {...}}`.
Retries with the same normalized device ID and sequence return HTTP 200 with
`{"status": "duplicate"}` and are not broadcast again. Broadcast failures return
HTTP 500 and do not mark the event as processed, allowing a retry.

Duplicate tracking is in memory for the lifetime of one server process; run a
single process. The set grows with accepted events and clears on server restart.
The Pico resets its sequence on reboot: restart the server or use a new device
ID for that session to avoid collisions with previously accepted sequences.
GET `/health` returns `{"status": "ok"}`. Standard Python logging records accepted
and duplicate events, validation and broadcast errors, and Socket.IO connections.

The React frontend still reads `data.message`; it needs a separate update to
display these structured event fields. No legacy `message` field is emitted.

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
     curl -X POST http://127.0.0.1:5000/message -H "Content-Type: application/json" -d '{"device_id":"pico-w-01","event":"trap_triggered","location":"Armoury","sequence":1}'
     ```

5. Run host-side tests (no Pico hardware needed)
```
python -m unittest discover -s tests -v
```
