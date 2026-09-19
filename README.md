HOW TO USE

## Architecture

Summary of architecture by Archify:
![Architecture](architecture/runtime.visual-check.2048x1320.light.png "Architecture").

## Live-event checks and simulator

Start the Flask server, then in another terminal with `.venv` active run:

```sh
python tools/simulate_pico.py --location armoury
```

The simulator defaults to `http://127.0.0.1:5050/message`, matching the server's
current default. Use `--url http://<laptop-LAN-IP>:5050/message` for another
computer. Each invocation gets a unique device ID so repeat runs produce new
events. To test duplicate suppression, run the same command twice with
`--device-id test-pico --sequence 1`. Requests time out after five seconds and
failures exit with a nonzero status. No additional dependencies are needed.

The Pico LED stays on during sending, flashes once after success, and flashes
three times after failure. Wi-Fi drops trigger bounded reconnect attempts.
Malformed HTTP replies and response cleanup failures are logged without ending
the button loop. Incompatible `urequests` timeout support produces a failure
pattern and a diagnostic instead of crashing. Network calls and LED feedback
are synchronous, so short presses during these operations can still be missed;
there is no persistent event queue. Configure a numeric LAN IPv4 server address.

Accepted-event logs include device ID, location, sequence, and UTC received time;
duplicate events are logged separately. The frontend retains the latest ten
events until page reload, shows the latest separately, and keeps its timer
running while the server is disconnected. Events sent while a browser is
disconnected are not replayed on reconnect.

## Run the complete system on a local LAN

One-time online setup: install npm dependencies in the sibling frontend repo,
and run `python3 -m venv .venv` followed by
`.venv/bin/python -m pip install -r requirements.txt` in this repository.
Then build and copy the site (commands from the parent workspace):

```sh
cd easound-main
npm install
npm run build
python3 ../earaspberrypi-main/copy_frontend.py ./dist
cd ../earaspberrypi-main
source .venv/bin/activate
python client.py
```

If your folders are named `easound` and `earaspberrypi`, use those names instead.
The copy script also auto-detects either sibling name when run without arguments.
It copies all build assets and MP3s into `frontend/`, which is generated locally
and excluded from Git. Older hashed assets are retained for open browser tabs.
Rerun the build and copy after changing the frontend.

Open `http://<laptop-LAN-IP>:5000`. Flask serves the page, static files, audio,
and Socket.IO on the same origin; no Vite process or internet is needed after
setup. Extensionless SPA routes fall back to index.html. Missing files return
404; a missing frontend build returns 503. `/health` and `POST /message` remain
available. The frontend has no runtime CDN dependencies.

Configure the Pico Wi-Fi credentials and set `SERVER_HOST` to the laptop's LAN
IP and `SERVER_PORT` to 5000. Allow port 5000 through the laptop firewall and
use a Wi-Fi network without client isolation. If port 5000 is occupied, free
it (macOS AirPlay Receiver may use it) or run `PORT=5050 python client.py`
and change the browser URL and Pico port to 5050. Audio may require a browser
interaction such as clicking Start. Keep the server in the foreground.

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

The updated React frontend displays the structured location and timestamp.
No legacy `message` field is emitted.

3. Run the client.py on your computer
  1. Open Command Prompt in the project folder
  2. Run:
     ```
     python client.py
     ```
  3. Keep `http://<laptop-LAN-IP>:5000` open in your browser.

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
