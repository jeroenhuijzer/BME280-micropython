# BME280-micropython
(micro)Python library to communicate with the Bosch sensortec BME280 sensor

This is a python library intended for use on low cost, low power microcontroller units like the ESP8266.
The goal is to provide most of the official c++ driver functions while maintaining a low memory profile.
Tested with a ESP8266-12F 4MB microcontroller running micropython v1.18
based on the official [v3.5.0 driver](https://github.com/BoschSensortec/BME280_driver)
## basic usage
- usecase: weather monitoring (low power, forced mode, one measurement per interval)

```python
import machine
import time
from bme280 import BME280

scl = machine.Pin(5)
sda = machine.Pin(4)
i2c = machine.SoftI2C(scl, sda)

# initialize the sensor
sensor = BME280(i2c)
print(sensor.chip_id)
# use recommended settings for monitoring 
sensor.set_sensor_settings(0x01, 0x01, 0x01, 0x00, 0x00)
# calculate minimal wait time with chosen settings
req_delay = sensor.cal_meas_delay()

while True:
    # set 'forced mode' (do a measurement then sensor goes to sleep)
    sensor.set_sensor_mode(0x01)
    time.sleep_us(req_delay)
    temperature, pressure, humidity = sensor.get_sensor_data()
    # do something with the results:
    print("temp:", temperature / 100, 'C', 'press:', pressure / 100, 'hPa', 'hum:', humidity / 1024, 'rel%')
    time.sleep(60)
```
- usecase 'gaming' (high power, normal mode, continuous stream of measurements)

```python
import machine
import time
from bme280 import BME280

scl = machine.Pin(5)
sda = machine.Pin(4)
i2c = machine.SoftI2C(scl, sda)

# initialize the sensor
sensor = BME280(i2c)
print(sensor.chip_id)
# use recommended settings for data stream 
sensor.set_sensor_settings(0x01, 0x05, 0x02, 0x05, 0x02)
# set normal mode
sensor.set_sensor_mode(0x03)
while True:
    # continuous stream of results
    temperature, pressure, humidity = sensor.get_sensor_data()
    print("temp:", temperature / 100, 'C', 'press:', pressure / 100, 'hPa', 'hum:', humidity / 1024, 'rel%')
    time.sleep_us(40000)  # 25 hz
```

##setting the sensor

use `BME280.set_sensor_mode` to set the sensor
 it takes 5 parameters:
- humidity_oversampling_rate (range 0x00 - 0x05)
- pressure_oversampling (range 0x00 - 0x05)
- temperature_oversampling_rate (range 0x00 - 0x05)
- filter_coefficient (range 0x00 - 0x05)
- standby_time (range 0x00 - 0x07)

there is no check for validity of the setting, do not use values out-of-range