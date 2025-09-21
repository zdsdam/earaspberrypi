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
    ssid = "YOUR_WIFI_NAME"
    password = "YOUR_WIFI_PASSWORD"
    pc_ip = "YOUR_COMPUTER_IPV4_ADDRESS"
    (find your IP by running ipconfig in Command Prompt; use the IPv4 Address).
  4. Upload main.py to the Pico W.

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

   
   

