import json
from machine import Pin, PWM, Timer, reset
import network
from phew import server, connect_to_wifi
import re
import rp2
import socket
from time import sleep
import ubinascii

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
unlocked_servo_position = data["unlocked_position"]
locked_servo_position = data["locked_position"]
timeout = data["timeout"]
ssid = data["SSID"]
wifi_password = data["wifi_password"]

door_sensor_pin = 18
servo_pin = 1
unlock_button_pin = 15
lock_button_pin = 14

door_sensor = Pin(door_sensor_pin, Pin.IN, Pin.PULL_UP)
unlock_button = Pin(unlock_button_pin, Pin.IN, Pin.PULL_DOWN)
lock_button = Pin(lock_button_pin, Pin.IN, Pin.PULL_DOWN)
servo = PWM(Pin(servo_pin))
servo.freq(50)
timer = 0
timer_fraction = .25
wlan = network.WLAN(network.STA_IF)

connect_to_wifi(ssid, wifi_password)

# wlan.active(True)
# wlan.connect(ssid, wifi_password)

# wlan_timeout = 10
# while wlan_timeout > 0:
#     print(f"wlan status: {wlan.status()} Waiting for connection... ({wlan_timeout})")
#     if wlan.status() < 0 or wlan.status() >= 3:
#         break
#     timeout -= 1
#     sleep(1)
#
# if wlan_timeout == 0:
#     reset()

network_info = wlan.ifconfig()
local_ip_address = network_info[0]
# addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
# s = socket.socket()
# s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
# s.bind(addr)
# s.listen(50)
print("Listening on {}.".format(local_ip_address))
# mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
# print('mac = ' + mac)

door_is_locked = False


def door_is_open():
    return door_sensor.value() == 1


def door_is_closed():
    return not door_is_open()


def move_lock(position):
    servo.duty_u16(position)
    sleep(.5)


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
        move_lock(locked_servo_position)
        door_is_locked = True


print(f'TIMEOUT = {timeout}')

LockTimer = Timer(period=get_timeout(), mode=Timer.ONE_SHOT, callback=lock_door)


def unlock_door(_):
    global door_is_locked
    print("unlocking door")
    initialize_lock_timer()
    move_lock(unlocked_servo_position)
    door_is_locked = False


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
            <p>The door is {open_state} and {locked_state}. <a href="/status">update status</a></p>

            <form action="/unlock">
                <input type="submit" value="Unlock" />
            </form> <br />
            <form action="/lock">
                <input type="submit" value="Lock" />
            </form>

            <br />
            <br />
            <br />
            <p style="color:#ccc">Current timeout is {get_timeout() / 1000 / 60} minutes. Set new timeout with `{local_ip_address}/timeout/[new value]`.</p> 
        </body>
    </html>
    """
    return html


lock_door(None)
lock_button.irq(trigger=Pin.IRQ_RISING, handler=lock_door)
unlock_button.irq(trigger=Pin.IRQ_RISING, handler=unlock_door)
door_sensor.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=set_lock_timer)


@server.route("/lock", methods=["GET"])
def serve_lock(request):
    lock_door(None)
    return get_html(door_is_open(), door_is_locked)


@server.route("/unlock", methods=["GET"])
def serve_unlock(request):
    unlock_door(None)
    return get_html(door_is_open(), door_is_locked)


@server.route("/timeout/<t>", methods=["GET"])
def serve_unlock(request):
    print(request)
    return get_html(door_is_open(), door_is_locked)


@server.catchall()
def catchall(request):
    return get_html(door_is_open(), door_is_locked)


server.run()

# def server(s):
#     client, address = s.accept()
#     print("connected from {}.".format(address))
#     req = client.recv(1024)
#     req = str(req)
#     print("req")
#     print(req)
#     request = None
#     try:
#         request = req.split()
#     except IndexError:
#         pass
#
#     print(req)
#
#     if request is not None:
#         u = get_url_with_params(request[1])
#         print(f"U: {u}")
#         if len(u) > 0:
#             uri = u[0]
#             if uri == 'lock':
#                 lock_door(None)
#             elif uri == 'unlock':
#                 unlock_door(None)
#             elif uri == 'timeout':
#                 update_timeout(float(u[1]))
#
#     door_open = "open"
#     if door_is_closed():
#         door_open = "closed"
#
#     door_locked = "unlocked"
#     if door_is_locked:
#         door_locked = "locked"
#
#     response = get_html(door_open, door_locked)
#
#     client.send('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
#     client.send(response)
#     client.close()


# while True:
#     try:
#         server(s)
#     except BaseException:
#         reset()


while True:
    sleep(.01)
