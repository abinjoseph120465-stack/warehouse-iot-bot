
#   RASPBERRY PI PICO 2 W 

import machine
import time
import network
from machine import Pin, PWM, ADC, UART, WDT
from BlynkLib import Blynk


# USER CONFIGURATION

WIFI_SSID = "realme"
WIFI_PASS = "123456789"
BLYNK_AUTH_TOKEN = "nlBDrZUIE6lOIZDiK-e8BGhw7ffHRsBB"


# LED INDICATION ENGINE (on board)

led = Pin("LED", Pin.OUT)

def led_signal(pattern):
    if pattern == 1:
        for _ in range(2): led.on(); time.sleep(0.1); led.off(); time.sleep(0.1)
    elif pattern == 2:
        for _ in range(2): led.on(); time.sleep(0.3); led.off(); time.sleep(0.2)
    elif pattern == 3:
        for _ in range(3): led.on(); time.sleep(0.1); led.off(); time.sleep(0.1)
    elif pattern == 5:
        for _ in range(5): led.on(); time.sleep(0.05); led.off(); time.sleep(0.05)


# HARDWARE & TUNING


m_r1, m_r2 = PWM(Pin(10)), PWM(Pin(11))
m_l1, m_l2 = PWM(Pin(12)), PWM(Pin(13))
for m in [m_l1, m_l2, m_r1, m_r2]: m.freq(1000)

adc_sensors = [ADC(26), ADC(27), ADC(28)]
ir_left_outer, ir_right_outer = Pin(18, Pin.IN), Pin(19, Pin.IN)
trig, echo = Pin(16, Pin.OUT), Pin(17, Pin.IN)

servo = PWM(Pin(15))
servo.freq(50)

KP, KD = 35, 20

blynk = None
wdt = None
robot_enabled = True
last_error = 0
robot_state = 0
status_msg = "BOOTING..."
last_status_msg = ""
cal_black = 0
cal_white = 0
sensor_vals = [0, 0, 0, 0, 0]
current_dist = 100


# CORE FUNCTIONS

def set_motor_raw(l, r):
    l = max(min(int(l), 65535), -65535)
    r = max(min(int(r), 65535), -65535)
    if l >= 0: m_l1.duty_u16(l); m_l2.duty_u16(0)
    else: m_l1.duty_u16(0); m_l2.duty_u16(abs(l))
    if r >= 0: m_r1.duty_u16(r); m_r2.duty_u16(0)
    else: m_r1.duty_u16(0); m_r2.duty_u16(abs(r))

def move_servo(angle):
    duty = int(1638 + (angle / 180) * 6554)
    servo.duty_u16(duty)

def get_distance():
    trig.low(); time.sleep_us(2)
    trig.high(); time.sleep_us(10)
    trig.low()
    try:
        pulse = machine.time_pulse_us(echo, 1, 30000)
        if pulse < 0: return 100
        return (pulse * 0.0343) / 2
    except OSError:
        return 100

def calibrate_sensors():
    global cal_black, cal_white
    b_sum, w_sum = 0, 0
    for _ in range(10):
        w_sum += adc_sensors[0].read_u16() + adc_sensors[2].read_u16()
        b_sum += adc_sensors[1].read_u16()
        time.sleep(0.05)
    cal_white = w_sum // 20
    cal_black = b_sum // 10

def update_sensors_realtime():
    global sensor_vals
    l_out = 1000 if ir_left_outer.value() == 0 else 0
    r_out = 1000 if ir_right_outer.value() == 0 else 0

    diff = cal_black - cal_white
    if abs(diff) < 500:
        diff = 500 if diff >= 0 else -500

    mapped = []
    for i in range(3):
        raw = adc_sensors[i].read_u16()
        val = (raw - cal_white) * 1000 // diff
        mapped.append(max(0, min(1000, val)))

    sensor_vals = [l_out, mapped[0], mapped[1], mapped[2], r_out]

def send_telemetry():
    try:
        blynk.virtual_write(1, int(sensor_vals[0]))
        blynk.virtual_write(2, int(sensor_vals[1]))
        blynk.virtual_write(3, int(sensor_vals[2]))
        blynk.virtual_write(4, int(sensor_vals[3]))
        blynk.virtual_write(5, int(sensor_vals[4]))
        blynk.virtual_write(7, int(current_dist))
    except:
        pass

def get_line_position():
    weights = [-2000, -1000, 0, 1000, 2000]
    total = sum(sensor_vals)
    if total < 400:
        return None
    weighted_sum = sum(sensor_vals[i] * weights[i] for i in range(5))
    return weighted_sum // total


# MAIN

def main():
    global blynk, wdt, robot_enabled, robot_state
    global last_error, status_msg, last_status_msg, current_dist

    set_motor_raw(0, 0)
    move_servo(90)

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(pm=0xa11140)
    wlan.disconnect()
    time.sleep(1)

    wlan.connect(WIFI_SSID, WIFI_PASS)
    while wlan.status() != 3:
        led_signal(1)
        time.sleep(0.5)

    blynk = Blynk(BLYNK_AUTH_TOKEN, insecure=True)

    @blynk.on("V0")
    def v0_handler(value):
        global robot_enabled
        robot_enabled = False if str(value[0]) in ['1','True','true'] else True

    calibrate_sensors()

    wdt = WDT(timeout=8000)

    while True:
        wdt.feed()
        blynk.run()

        current_dist = get_distance()
        update_sensors_realtime()
        send_telemetry()

        if not robot_enabled:
            set_motor_raw(0, 0)
            continue

        # NORMAL RUN
        if robot_state == 0:

            if current_dist < 15:
                robot_state = 1
                continue

            if sensor_vals[0] > 500:
                set_motor_raw(-45000, 45000)
                continue

            elif sensor_vals[4] > 500:
                set_motor_raw(45000, -45000)
                continue

            pos = get_line_position()

            #  LINE LOST (STOP FOREVER)
            if pos is None:
                status_msg = "LINE LOST"
                try:
                    blynk.virtual_write(6, status_msg)
                except:
                    pass
                set_motor_raw(0, 0)

                while True:
                    wdt.feed()
                    try: blynk.run()
                    except: pass
                    time.sleep(0.1)

            else:
                status_msg = "TRACKING LINE"
                error = pos
                correction = (error * KP) + ((error - last_error) * KD)
                last_error = error
                base_speed = 40000
                set_motor_raw(base_speed + correction, base_speed - correction)

        # OBSTACLE AVOIDANCE
        elif robot_state == 1:

            set_motor_raw(0, 0)
            time.sleep(0.3)

            move_servo(150); time.sleep(0.5); left_d = get_distance()
            move_servo(30);  time.sleep(0.5); right_d = get_distance()
            move_servo(90)

            avoid_speed = 40000
            turn_time = 0.45
            pass_time = 0.6

            if left_d > right_d:
                set_motor_raw(-avoid_speed, avoid_speed); time.sleep(turn_time)
                set_motor_raw(avoid_speed, avoid_speed);  time.sleep(pass_time)
                set_motor_raw(avoid_speed, -avoid_speed); time.sleep(turn_time)
                set_motor_raw(avoid_speed, avoid_speed);  time.sleep(pass_time)
                set_motor_raw(avoid_speed, -avoid_speed); time.sleep(turn_time)
            else:
                set_motor_raw(avoid_speed, -avoid_speed); time.sleep(turn_time)
                set_motor_raw(avoid_speed, avoid_speed);  time.sleep(pass_time)
                set_motor_raw(-avoid_speed, avoid_speed); time.sleep(turn_time)
                set_motor_raw(avoid_speed, avoid_speed);  time.sleep(pass_time)
                set_motor_raw(-avoid_speed, avoid_speed); time.sleep(turn_time)

            robot_state = 0


if __name__ == "__main__":
    main()
