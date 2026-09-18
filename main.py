from machine import Pin
import network
import urequests
import time

# Wi-Fi credentials
ssid = "WIFI_NAME"
password = "WIFI_PASS"

# Flask server URL (change this to your Render URL or local IP if testing locally)
pc_ip = "http://(ipv4address):5000/message" #5000 is the port? use local ipv4

# Setup pins
led = Pin("LED", Pin.OUT)
button1 = Pin(14, Pin.IN, Pin.PULL_UP)
button2 = Pin(10, Pin.IN, Pin.PULL_UP)

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

while not wlan.isconnected():
    print("Connecting to Wi-Fi...")
    time.sleep(1)

print("Connected to Wi-Fi")
print("IP:", wlan.ifconfig()[0])

# Loop: Check buttons and send message
while True:
    if button1.value() == 0:
        led.on()
        print("Button 1 pressed")
        try:
            message = {"message": "Blinding: Armoury!"}
            headers = {"Content-Type": "application/json"}
            response = urequests.post(pc_ip, json=message, headers=headers)
            print("Response:", response.text)
            response.close()
        except Exception as e:
            print("Failed to send:", e)
        led.off()

    if button2.value() == 0:
        led.on()
        print("Button 2 pressed")
        try:
            message = {"message": "Blinding: Storage!"}
            headers = {"Content-Type": "application/json"}
            response = urequests.post(pc_ip, json=message, headers=headers)
            print("Response:", response.text)
            response.close()
        except Exception as e:
            print("Failed to send:", e)
        led.off()

    time.sleep(0.2)

