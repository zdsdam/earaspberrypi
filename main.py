from machine import Pin
import network
import urequests
import time


WIFI_SSID = "WIFI_NAME"
WIFI_PASSWORD = "WIFI_PASS"
WIFI_TIMEOUT_MS = 10000
WIFI_RECONNECT_MS = 5000

# Use the Flask computer's LAN IPv4 address, without http:// or a path.
SERVER_HOST = "192.168.1.100"
SERVER_PORT = 5000
SERVER_PATH = "/message"
DEVICE_ID = "pico-w-01"
HTTP_TIMEOUT_SECONDS = 5
HTTP_MAX_ATTEMPTS = 3
HTTP_RETRY_MS = 500

DEBOUNCE_MS = 50
POLL_MS = 10
BUTTONS = ((14, "Armoury"), (10, "Storage"))

led = Pin("LED", Pin.OUT)
wlan = network.WLAN(network.STA_IF)
sequence = 0  # Per boot; retries keep the original event's sequence.


def connect_wifi():
    if wlan.isconnected():
        return True
    try:
        wlan.active(True)
        wlan.disconnect()
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        started = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), started) >= WIFI_TIMEOUT_MS:
                wlan.disconnect()
                print("Wi-Fi connection timed out")
                return False
            time.sleep_ms(100)
        print("Wi-Fi connected:", wlan.ifconfig()[0])
        return True
    except OSError as error:
        print("Wi-Fi connection failed:", error)
        return False


def send_event(event, location):
    global sequence
    sequence += 1
    payload = {
        "device_id": DEVICE_ID,
        "event": event,
        "location": location,
        "sequence": sequence,
    }
    url = "http://{}:{}{}".format(SERVER_HOST, SERVER_PORT, SERVER_PATH)
    led.on()
    try:
        for attempt in range(HTTP_MAX_ATTEMPTS):
            response = None
            try:
                if connect_wifi():
                    response = urequests.post(
                        url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=HTTP_TIMEOUT_SECONDS,
                    )
                    status = response.status_code
                    if 200 <= status < 300:
                        print("Event sent:", payload)
                        return True
                    print("HTTP request failed:", status)
                    # Retrying a rejected payload will not fix it.
                    if 400 <= status < 500 and status not in (408, 429):
                        return False
            except OSError as error:
                print("HTTP attempt failed:", error)
            finally:
                if response is not None:
                    response.close()
            if attempt + 1 < HTTP_MAX_ATTEMPTS:
                time.sleep_ms(HTTP_RETRY_MS)
        print("Event dropped after limited attempts:", payload)
        return False
    finally:
        led.off()


class Button:
    def __init__(self, gpio, location):
        self.pin = Pin(gpio, Pin.IN, Pin.PULL_UP)
        self.location = location
        self.raw = self.pin.value()
        self.stable = self.raw
        self.changed_at = time.ticks_ms()

    def pressed(self):
        now = time.ticks_ms()
        value = self.pin.value()
        if value != self.raw:
            self.raw = value
            self.changed_at = now
        if (self.raw != self.stable
                and time.ticks_diff(now, self.changed_at) >= DEBOUNCE_MS):
            self.stable = self.raw
            return self.stable == 0  # Active-low falling edge only.
        return False


def main():
    buttons = [Button(gpio, location) for gpio, location in BUTTONS]
    led.off()
    connect_wifi()
    last_reconnect = time.ticks_ms()
    while True:
        # Sample both buttons before any blocking network calls.
        pressed = [button for button in buttons if button.pressed()]
        for button in pressed:
            send_event("blinding", button.location)
            last_reconnect = time.ticks_ms()
        if (not wlan.isconnected()
                and time.ticks_diff(time.ticks_ms(), last_reconnect)
                >= WIFI_RECONNECT_MS):
            connect_wifi()
            last_reconnect = time.ticks_ms()
        time.sleep_ms(POLL_MS)


if __name__ == "__main__":
    main()
