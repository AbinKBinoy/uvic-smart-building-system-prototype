# Minimal web server test - just serves "Hello World"
# If this loads in the browser, we know the issue is HTML size

import network
import socket
import time
from machine import Pin

pico_led = Pin("LED", Pin.OUT)
pico_led.on()

# Setup Wi-Fi AP
ssid = 'BMS_UVic'
password = 'engr120bms'

ap = network.WLAN(network.AP_IF)
ap.config(essid=ssid, password=password)
ap.active(True)

while ap.active() == False:
    pass

print('AP Active')
print('IP:', ap.ifconfig()[0])

# Setup socket - BLOCKING mode (simpler)
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(('', 80))
s.listen(5)

print('Waiting for connections...')
print('Connect to Wi-Fi: BMS_UVic / engr120bms')
print('Then open: http://' + ap.ifconfig()[0])

while True:
    try:
        conn, addr = s.accept()
        print('Client connected:', addr)
        
        # Read request
        request = conn.recv(1024)
        print('Request received')
        
        # Send simple response
        response = """<!DOCTYPE html>
<html><body>
<h1>BMS Test</h1>
<p>If you see this, the web server works!</p>
</body></html>"""
        
        conn.send("HTTP/1.1 200 OK\r\n")
        conn.send("Content-Type: text/html\r\n")
        conn.send("Content-Length: " + str(len(response)) + "\r\n")
        conn.send("Connection: close\r\n\r\n")
        conn.send(response)
        conn.close()
        print('Response sent')
        
    except Exception as e:
        print('Error:', e)
        try:
            conn.close()
        except:
            pass
