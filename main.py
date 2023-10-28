import json
from machine import Pin, PWM, Timer, reset, I2C
import network
import re
import rp2
import socket
from time import sleep
import ubinascii
from lcd_api import LcdApi
from i2c_lcd import I2cLcd

rp2.country('US')


def get_settings():
    settings = open("settings.json", "r")
    d = json.load(settings)
    settings.close()
    return d


def get_timeout():
    return int(get_settings()['timeout'] * 1000)


data = get_settings()
# servo positions min 1250 max 8550
unlocked_servo_position_r = data["unlocked_position_r"]
locked_servo_position_r = data["locked_position_r"]
unlocked_servo_position_l = data["unlocked_position_l"]
locked_servo_position_l = data["locked_position_l"]
timeout = data["timeout"]
ssid = data["SSID"]
wifi_password = data["wifi_password"]

door_sensor_pin = 18
servo_r_pin = 1
servo_l_pin = 2
unlock_button_pin = 15
lock_button_pin = 14
lcd_sda_pin = 10
lcd_scl_pin = 11

door_sensor = Pin(door_sensor_pin, Pin.IN, Pin.PULL_UP)
unlock_button = Pin(unlock_button_pin, Pin.IN, Pin.PULL_DOWN)
lock_button = Pin(lock_button_pin, Pin.IN, Pin.PULL_DOWN)
servo_l = PWM(Pin(servo_l_pin))
servo_l.freq(50)
servo_r = PWM(Pin(servo_r_pin))
servo_r.freq(50)

# Display
i2c=I2C(1, sda=Pin(lcd_sda_pin), scl=Pin(lcd_scl_pin), freq=400000)
devices = i2c.scan()

if len(devices) == 0:
    print("No i2c device!")
else:
    print('i2c devices found:',len(devices))
    
I2C_ADDR = 0x27
print("Hex address: ", I2C_ADDR)

I2C_NUM_ROWS = 2
I2C_NUM_COLS = 16

lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

def message(s1):
    lcd.clear()
    lcd.putstr(s1)


# Networking
wlan = network.WLAN(network.STA_IF)


def connect():
    print(f"connecting to '{ssid}'")
    tries = 0
    while not wlan.isconnected():
        wlan.active(True)
        wlan.connect(ssid, wifi_password)
        for i in range(5):
            message(f"WiFi connecting {tries}...")
            tries = tries + 1
            if not wlan.isconnected():
                sleep(1)
            else:
                break

connect()

network_info = wlan.ifconfig()
local_ip_address = network_info[0]
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(50)
print("Listening on {}.".format(local_ip_address))
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print('mac = ' + mac)

message(f"WiFi connected!"+'\n'+f"{local_ip_address}")

door_is_locked = False

def displayStatus(lock):
    if lock:
        lock_message = "locked"
    else:
        lock_message = "unlocked"
    message(f"IP:{local_ip_address} lock:{lock_message}")
    # todo set a timer to turn this off after 60 seconds
    # todo add4 a button that will toggle the state of this message


def door_is_open():
    return door_sensor.value() == 1


def door_is_closed():
    return not door_is_open()


def move_lock(position_l, position_r):
    print(f"L: {position_l}, R: {position_r}")
    servo_l.duty_u16(position_l)
    servo_r.duty_u16(position_r)
    sleep(1)


def update_timeout(new_timeout):
    print(f'new_timeout = {new_timeout}')
    d = get_settings()
    print(d)

    d['timeout'] = new_timeout * 60
    new_settings = json.dumps(d)
    print('new_settings***')
    print(new_settings)

    with open("settings.json", "w") as jsonfile:
        jsonfile.write(new_settings)
        print("updated timout")


def initialize_lock_timer():
    print("re-initializing lock timer")
    LockTimer.init(period=get_timeout(), mode=Timer.ONE_SHOT, callback=lock_door)


# interrupt, when door closes the counter restarts at zero
def set_lock_timer(p):
    global LockTimer
    if p.value() == 0:
        print("door is closed")
        initialize_lock_timer()
    elif p.value() == 1:
        print("door is open")
        LockTimer.deinit()


def lock_door(_):
    global door_is_locked
    if door_is_closed():
        print("door is closed, locking door")
        move_lock(locked_servo_position_l, locked_servo_position_r)
        door_is_locked = True
        displayStatus(door_is_locked)


LockTimer = Timer(period=get_timeout(), mode=Timer.ONE_SHOT, callback=lock_door)


def unlock_door(_):
    global door_is_locked
    print("unlocking door")
    initialize_lock_timer()
    move_lock(unlocked_servo_position_l, unlocked_servo_position_r)
    door_is_locked = False
    displayStatus(door_is_locked)


def get_url_with_params(url):
    new_url = re.sub('[?/]', '/', url)
    l = new_url.split('/')
    while "" in l:
        l.remove("")
    return l


def get_html(open_state, locked_state):
    global local_ip_address
    html = f"""<!DOCTYPE html>
    <html>
        <head> <title>Mapel Cottage Door Lock</title> </head>
        <body> <h1>Sliding Door</h1>
            <form action="/unlock">
                <input type="submit" value="Unlock" />
            </form> <br />
            <form action="/lock">
                <input type="submit" value="Lock" />
            </form>
            
            <h3>Status</h3>
            <p>The door is {open_state} and {locked_state}. <a href="/status">update status</a></p>

            <br />
            <br />
            <br />
            <p style="color:#ccc">Current timeout is {get_timeout()/1000/60} minutes. Set new timeout with `{local_ip_address}/timeout/[new value in minutes]`.</p> 
        </body>
    </html>
    """
    return html


lock_door(None)
lock_button.irq(trigger=Pin.IRQ_RISING, handler=lock_door)
unlock_button.irq(trigger=Pin.IRQ_RISING, handler=unlock_door)
door_sensor.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=set_lock_timer)


def server(s):
    client, address = s.accept()
    print("connected from {}.".format(address))
    req = client.recv(1024)
    req = str(req)
    print("req")
    print(req)
    request = None
    try:
        request = req.split()
    except IndexError:
        pass

    print(req)

    if request is not None:
        u = get_url_with_params(request[1])
        print(f"U: {u}")
        if len(u) > 0:
            uri = u[0]
            if uri == 'lock':
                lock_door(None)
            elif uri == 'unlock':
                unlock_door(None)
            elif uri == 'timeout':
                update_timeout(float(u[1]))

    door_open = "open"
    if door_is_closed():
        door_open = "closed"

    door_locked = "unlocked"
    if door_is_locked:
        door_locked = "locked"

    response = get_html(door_open, door_locked)

    client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
    client.send(response)
    client.close()


while True:
    try:
        server(s)
    except BaseException:
        reset()
