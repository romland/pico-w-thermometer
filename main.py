#
# A test to poke around a bit with the RP Pico W that was released a couple
# of days ago. The difference from the RP Pico microcontroller is that this
# one has WiFi radio (hence the W).
#
# This program does the following:
#
# 1. Connect to a WiFi network
# 2. Reads the temperature from a ds18b20 sensor wired to the Pico W board
# 3. Reports temperature to HomeAssistant by using an "HTTP sensor", you do
#    not need to add any configuration in HomeAssistant for this to work.
# 4. Goes to deep sleep for 15 minutes
# 5. Goto 1.
#
# Notes on changing the code:
# - When the program is running, the on-board LED of the Pico board is lit. If 
#   you are using a UI like the recommended Thonny, you can simply halt the 
#   program when LED is on and update the program.
#
#     -- Joakim Romland, 05-Jul-2022
#

import urequests, rp2, network, machine, onewire, ds18x20, time
from machine import Pin, Timer

# Configuration =====================================
REPORT_INTERVAL_MINUTES = 15         # How often to report to HomeAssistant (HA)
WIFI_COUNTRY_ISO_CODE = "NL"         # You will want to change this to US/GB/or what-have-you
SSID =  "YOUR_SSID"                  # WiFi network name
SSID_KEY = "YOUR_SECRET"             # WiFi network password

# Create a Long-Lived Access Tokens in your HomeAssistant UI (bottom of your profile), paste it below.
HA_LONG_LIVED_TOKEN = "A_REALLY_LONG_TOKEN_FROM_HOME_ASSISTANT"
HA_SENSOR_ID = "temp_shed"           # Unique ID of this sensor
HA_SENSOR_NAME = "Shed Thermometer"  # A pretty name for this sensor
HA_IP = "192.168.178.248:8123"       # IP address (and port) to HomeAssistant

# Globals ===========================================
wlan = None       # network object
led = None        # onboard LED
ds_pin = None     # GPIO pin for temperature data
ds_sensor = None  # temperature sensor object (Dallas)

# Functions =========================================
def init():
    global led
    global ds_sensor
    global ds_pin
    
    # Get on-board LED
    led = Pin("LED", Pin.OUT)
    
    # Set country for additional WiFi frequencies
    rp2.country(WIFI_COUNTRY_ISO_CODE)
    
    # Find thermometer
    ds_pin = machine.Pin(16)
    ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))


def connectWifi(ssid, password):
    global wlan
    
    # STA_IF = station interface, AP_IF = Access Point interface
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    # Wait for connect, fail after 10 seconds
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('connecting to access point...')
        time.sleep(1)

    # Handle connection error
    if wlan.status() != 3:
        raise RuntimeError('connecting to wifi failed')
    else:
        status = wlan.ifconfig()
        print('connected as ' + status[0])


def disconnectWifi():
    wlan.disconnect()


def getTemperature():
    roms = ds_sensor.scan()
    print('found ds18x20 sensor')
    ds_sensor.convert_temp()
    time.sleep_ms(250)
    # You can chain these temperature sensors and get multiple objects,
    # in this case, we just care about the first; roms[0].
    temp = ds_sensor.read_temp(roms[0])
        
    return temp


# See:
#   https://www.home-assistant.io/integrations/http/
def reportTemperature(temp):
    data = {
        "state": temp,
        "attributes" : {
            "friendly_name" : HA_SENSOR_NAME
        }
    }

    resp = urequests.post(
        "http://" + HA_IP + "/api/states/sensor." + HA_SENSOR_ID,
        headers={
            "Authorization": "Bearer " + HA_LONG_LIVED_TOKEN,
            "content-type": "application/json",
        },
        json=data
    )

    print("Reported temperature: " + str(temp) + ", result: " + str(resp.content))
    resp.close()

# Main =============================================

# Technically we do not need to run this in a loop since a deep sleep
# resets the controller. That said, I keep it in because it makes for
# easier testing with a normal sleep.
while True:
    try:
		init()
		led.on()
		connectWifi(SSID, SSID_KEY)
		reportTemperature(getTemperature())
		disconnectWifi()
		led.off()
		time.sleep_ms(50)
    except Exception as ex:
        print("error uploading temp")
        print(e)
        time.sleep_ms(1000)
        led.off()
        machine.deepsleep(REPORT_INTERVAL_MINUTES * 60 * 1000)

    # See:
    #   https://forums.raspberrypi.com/viewtopic.php?t=321044
    #   https://github.com/micropython/micropython/pull/8832
    #   https://docs.micropython.org/en/latest/esp8266/tutorial/powerctrl.html
    machine.deepsleep(REPORT_INTERVAL_MINUTES * 60 * 1000)  # 15 minutes
	# For easier testing, comment out the line above and enable the following:
    # time.sleep_ms(5000)
