from time import sleep
from datetime import datetime
from gpiozero import Button
import bme680

vane_table = [5, 3, 4, 7, 6, 9, 8, 1, 2, 11, 10, 15, 0, 13, 14, 12]  # voltage -> angle / 22.5

interval_sec = 10
interval_min = 5

wind_factor = 2.4  # impulse -> km/h
rain_factor = 0.2794  # impulse -> mm


class Counter(Button):
    def __init__(self, pin):
        super(Counter, self).__init__(pin)
        self.count = 0
        self.when_pressed = self.inc

    def inc(self):
        self.count += 1

    def reset(self):
        t, self.count = self.count, 0
        return t


def main():
    sensor = bme680.BME680()

    sensor.set_humidity_oversample(bme680.OS_2X)
    sensor.set_pressure_oversample(bme680.OS_4X)
    sensor.set_temperature_oversample(bme680.OS_8X)
    sensor.set_filter(bme680.FILTER_SIZE_3)

    sensor.set_gas_status(bme680.ENABLE_GAS_MEAS)
    sensor.set_gas_heater_temperature(320)
    sensor.set_gas_heater_duration(150)
    sensor.select_gas_heater_profile(0)

    wind_speed_sensor = Counter(5)
    rain_sensor = Counter(6)

    count = count_gas = 0
    temperature_sum = pressure_sum = humidity_sum = gas_resistance_sum = 0
    rain_lap = wind_lap = 0
    tt = t = lt = datetime.now()
    sleep((interval_sec - t.second % interval_sec) - t.microsecond / 1000000.0)
    while True:
        t = datetime.now()
        # work begin
        if sensor.get_sensor_data():
            count += 1
            temperature, pressure, humidity = sensor.data.temperature, sensor.data.pressure, sensor.data.humidity
            temperature_sum += temperature
            pressure_sum += pressure
            humidity_sum += humidity
            if sensor.data.heat_stable:
                count_gas += 1
                gas_resistance = sensor.data.gas_resistance
                gas_resistance_sum += gas_resistance
                rain_count = rain_sensor.count
                wind_count = wind_speed_sensor.count
                dt = (t - lt).total_seconds()
                print (u"{:%Y-%m-%d %H:%M:%S.%f} {:6.2f}\N{DEGREE SIGN}C, {:7.2f} hPa, {:5.2f} %RH, {:6} Ohms"
                       u", {:7.4f} mm, {:6.2f} km/h".format(t, temperature, pressure, humidity,
                                                            gas_resistance if count_gas else 0,
                                                            (rain_count - rain_lap)*rain_factor,
                                                            (wind_count - wind_lap)*wind_factor/dt))
                rain_lap = rain_count
                wind_lap = wind_count
                lt = t
        if t.second == 0 and t.minute % interval_min == 0:
            dt = (t - tt).total_seconds()
            rain_count = rain_sensor.reset()
            wind_count = wind_speed_sensor.reset()
            rain_lap = wind_lap = 0
            print "#"*40
            print (u"{:%Y-%m-%d %H:%M:%S} {:6.2f}\N{DEGREE SIGN}C, {:7.2f} hPa, {:5.2f} %RH, {:6} Ohms"
                   u", {:7.4f} mm, {:6.2f} km/h".format(t, temperature_sum/count if count else 0,
                                                        pressure_sum/count if count else 0,
                                                        humidity_sum/count if count else 0,
                                                        gas_resistance_sum/count_gas if count_gas else 0,
                                                        rain_count*rain_factor, wind_count*wind_factor/dt))
            print "#"*40
            tt = t
            count = count_gas = 0
            temperature_sum = pressure_sum = humidity_sum = gas_resistance_sum = 0
        # work end
        t = datetime.now()
        sleep((interval_sec - t.second % interval_sec) - t.microsecond / 1000000.0)


if __name__ == "__main__":
    main()
