from time import sleep
from datetime import datetime, timedelta
from collections import namedtuple
from gpiozero import Button
import bme680

vane_table = [5, 3, 4, 7, 6, 9, 8, 1, 2, 11, 10, 15, 0, 13, 14, 12]  # voltage -> angle / 22.5


def wait(interval):
    """Wait for next multiple of seconds"""
    t = datetime.now()
    d = (interval - t.second % interval) - t.microsecond / 1000000.0
    sleep(d)
    return t + timedelta(0, d)


class Counter(Button):
    """Counter of positive edges"""
    rollover = 10000

    def __init__(self, pin):
        super(Counter, self).__init__(pin)
        self.last_count = 0
        self.count = 0
        self.when_pressed = self._inc

    def _inc(self):
        self.count = (self.count + 1) % Counter.rollover

    def get(self):
        c = self.count
        d = c - self.last_count
        self.last_count = c
        if d < 0:
            d += Counter.rollover
        return d


AirData = namedtuple('AirData', ['temperature', 'pressure', 'humidity', 'gas_resistance'])


class AirSensor(bme680.BME680, object):
    """Self initiating BME680"""

    def __init__(self):
        super(AirSensor, self).__init__()
        self.set_humidity_oversample(bme680.OS_2X)
        self.set_pressure_oversample(bme680.OS_4X)
        self.set_temperature_oversample(bme680.OS_8X)
        self.set_filter(bme680.FILTER_SIZE_3)

        self.set_gas_status(bme680.ENABLE_GAS_MEAS)
        self.set_gas_heater_temperature(320)
        self.set_gas_heater_duration(150)
        self.select_gas_heater_profile(0)

    def read(self):
        if self.get_sensor_data():
            d = self.data
            if d.heat_stable:
                return AirData(d.temperature, d.pressure, d.humidity, d.gas_resistance)
            else:
                return AirData(d.temperature, d.pressure, d.humidity, None)


def main():
    interval_sec = 10
    interval_min = 5

    wind_factor = 2.4  # impulse/s -> km/h
    rain_factor = 0.2794  # impulse -> mm

    air_sensor = AirSensor()
    wind_speed_sensor = Counter(5)
    rain_fall_sensor = Counter(6)

    while True:
        air_sum = AirData(0, 0, 0, 0)
        count = count_air = count_gas = 0
        wind_speed_sum = 0
        rain_fall_sum = 0
        t = wait(interval_sec)
        while True:
            # work begin (t)
            # wind and rain
            count += 1
            wind_speed = wind_speed_sensor.get()
            wind_speed_sum += wind_speed
            rain_fall = rain_fall_sensor.get()
            rain_fall_sum += rain_fall
            # air sensor
            air_data = air_sensor.read()
            if air_data:
                count_air += 1
                if air_data.gas_resistance:
                    count_gas += 1
                air_sum = AirData(air_sum.temperature + air_data.temperature,
                                  air_sum.pressure + air_data.pressure,
                                  air_sum.humidity + air_data.humidity,
                                  air_sum.gas_resistance + (air_data.gas_resistance if air_data.gas_resistance else 0))
                if air_data.gas_resistance:
                    air_string = u"{:6.2f}\N{DEGREE SIGN}C, {:7.2f} hPa, {:5.2f} %RH, {:7} Ohms".format(*air_data)
                else:
                    air_string = u"{:6.2f}\N{DEGREE SIGN}C, {:7.2f} hPa, {:5.2f} %RH, ------- Ohms".format(*air_data)
            else:
                air_string = u"------\N{DEGREE SIGN}C, ------- hPa, ----- %RH, ------- Ohms"
            if t.second == 0 and t.minute % interval_min == 0:
                break
            print(u"{:%Y-%m-%d %H:%M:%S.%f}: {:s}, {:2.4f} mm, {:7.3f} km/h".format(
                t, air_string, rain_fall * rain_factor, wind_speed * wind_factor / interval_sec))
            # work end
            t = wait(interval_sec)
        # work begin (t)
        print(u"{:%Y-%m-%d %H:%M:%S.%f}: "
              u"{:6.2f}\N{DEGREE SIGN}C, {:7.2f} hPa, {:5.2f} %RH, {:7} Ohms, {:2.4f} mm, {:7.3f} km/h"
              .format(t, air_sum.temperature / count_air if count_air else 0,
                      air_sum.pressure / count_air if count_air else 0,
                      air_sum.humidity / count_air if count_air else 0,
                      air_sum.gas_resistance / count_gas if count_gas else 0,
                      rain_fall_sum * rain_factor, wind_speed_sum * wind_factor / (count * interval_sec)))
        # work end


if __name__ == "__main__":
    main()
