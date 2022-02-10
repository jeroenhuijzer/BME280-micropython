import struct
import time



class BME280:

    def __init__(self, i2c: any, addr: int = 0x76):
        self.i2c = i2c
        self.addr = addr
        # check and reset sensor
        chip_id = self.i2c.readfrom_mem(self.addr, 0xD0, 1)[0]
        if chip_id != 0x60:
            raise Exception("BME280_E_DEV_NOT_FOUND")
        self.chip_id = hex(chip_id)
        self.soft_reset()
        # get temperature and pressure calibration data
        reg_data = self.i2c.readfrom_mem(self.addr, 0x88, 26)
        self.dig_t1 = struct.unpack('H', reg_data[0:2])[0]
        self.dig_t2 = struct.unpack('h', reg_data[2:4])[0]
        self.dig_t3 = struct.unpack('h', reg_data[4:6])[0]
        self.dig_p1 = struct.unpack('H', reg_data[6:8])[0]
        self.dig_p2 = struct.unpack('h', reg_data[8:10])[0]
        self.dig_p3 = struct.unpack('h', reg_data[10:12])[0]
        self.dig_p4 = struct.unpack('h', reg_data[12:14])[0]
        self.dig_p5 = struct.unpack('h', reg_data[14:16])[0]
        self.dig_p6 = struct.unpack('h', reg_data[16:18])[0]
        self.dig_p7 = struct.unpack('h', reg_data[18:20])[0]
        self.dig_p8 = struct.unpack('h', reg_data[20:22])[0]
        self.dig_p9 = struct.unpack('h', reg_data[22:24])[0]
        self.dig_h1 = reg_data[25]
        # get humidity calibration data
        reg_data = self.i2c.readfrom_mem(self.addr, 0xE1, 7)
        self.dig_h2 = struct.unpack('h', reg_data[0:2])[0]
        self.dig_h3 = reg_data[2]
        self.dig_h4 = (reg_data[3] << 4) | (reg_data[4] & 0x0F)
        self.dig_h5 = (reg_data[5] << 4) | (reg_data[4] >> 4)
        self.dig_h6 = struct.unpack('b', reg_data[6:7])[0]
        self.t_fine = 0

    def soft_reset(self):
        self.i2c.writeto_mem(self.addr, 0xE0, bytearray([0xB6]))
        for _ in range(5):
            status = self.i2c.readfrom_mem(self.addr, 0xF3, 1)[0]
            time.sleep_us(2000)
            if status & 0x01:
                break
        else:
            raise Exception("BME280_E_NVM_COPY_FAILED")

    def set_sensor_settings(self, osr_h: int, osr_p: int, osr_t: int, filter: int, standby_time: int):
        sensor_mode = self.get_sensor_mode()
        if sensor_mode != 0x00:
            self.soft_reset()

        ctrl_hum = osr_h & 0x07
        self.i2c.writeto_mem(self.addr, 0xF2, bytearray([ctrl_hum]))

        reg_data = self.i2c.readfrom_mem(self.addr, 0xF4, 1)[0]
        reg_data = (reg_data & ~0x1C) | ((osr_p << 0x02) & 0x1C)
        reg_data = (reg_data & ~0xE0) | ((osr_t << 0x05) & 0xE0)
        self.i2c.writeto_mem(self.addr, 0xF4, bytearray([reg_data]))

        reg_data = self.i2c.readfrom_mem(self.addr, 0xF5, 1)[0]
        reg_data = (reg_data & ~0x1C) | ((filter << 0x02) & 0x1C)
        reg_data = (reg_data & ~0xE0) | ((standby_time << 0x05) & 0xE0)
        self.i2c.writeto_mem(self.addr, 0xF5, bytearray([reg_data]))

    def get_sensor_settings(self) -> tuple[int, int, int, int, int]:
        reg_data = self.i2c.readfrom_mem(self.addr, 0xF2, 4)
        osr_h = reg_data[0] & 0x03
        osr_p = (reg_data[2] & 0x1C) >> 0x02
        osr_t = (reg_data[2] & 0xE0) >> 0x05
        filter = (reg_data[3] & 0x1C) >> 0x02
        standby_time = (reg_data[3] & 0xE0) >> 0x05
        return osr_h, osr_p, osr_t, filter, standby_time

    def set_sensor_mode(self, mode: int):
        last_set_mode = self.get_sensor_mode()
        if last_set_mode != 0x00:
            settings = self.get_sensor_settings()
            self.soft_reset()
            self.set_sensor_settings(*settings)
        reg_data = self.i2c.readfrom_mem(self.addr, 0xF4, 1)[0]
        sensor_mode_reg_val = (reg_data & ~0x03) | (mode & 0x03)
        self.i2c.writeto_mem(self.addr, 0xF4, bytearray([sensor_mode_reg_val]))

    def get_sensor_mode(self) -> int:
        reg_data = self.i2c.readfrom_mem(self.addr, 0xF4, 1)[0]
        return reg_data & 0x03

    def cal_meas_delay(self) -> int:
        osr_t, osr_p, osr_h, _, _ = self.get_sensor_settings()
        osr_sett_to_act_osr = [0, 1, 2, 4, 8, 16]
        temp_osr = osr_sett_to_act_osr[osr_t]
        pres_osr = osr_sett_to_act_osr[osr_p]
        hum_osr = osr_sett_to_act_osr[osr_h]
        max_delay = 1250 + (2300 * temp_osr) + (2300 * pres_osr) + 575 + (2300 * hum_osr) + 575
        return max_delay

    def get_sensor_data(self) -> tuple[int, int, int]:
        reg_data = self.i2c.readfrom_mem(self.addr, 0xF7, 8)
        upressure = reg_data[0] << 12 | reg_data[1] << 4 | reg_data[2] >> 4
        utemperature = reg_data[3] << 12 | reg_data[4] << 4 | reg_data[5] >> 4
        uhumidity = reg_data[6] << 8 | reg_data[7]

        var1 = (utemperature // 8) - (self.dig_t1 * 2)
        var1 = (var1 * self.dig_t2) // 2048
        var2 = (utemperature // 16) - self.dig_t1
        var2 = (((var2 * var2) // 4096) * self.dig_t3) // 16384
        self.t_fine = var1 + var2
        temperature = (self.t_fine * 5 + 128) // 256

        var1 = (self.t_fine // 2) - 64000
        var2 = (((var1 // 4) * (var1 // 4)) // 2048) * self.dig_p6
        var2 = var2 + (var1 * self.dig_p5 * 2)
        var2 = (var2 // 4) + (self.dig_p4 * 65536)
        var3 = (self.dig_p3 * (((var1 // 4) * (var1 // 4)) // 8192)) // 8
        var4 = (self.dig_p2 * var1) // 2
        var1 = (var3 + var4) // 262144
        var1 = ((32768 + var1) * self.dig_p1) // 32768

        if var1:
            var5 = 1048576 - upressure
            pressure = (var5 - (var2 // 4096)) * 3125
            if pressure < 0x80000000:
                pressure = (pressure << 1) // var1
            else:
                pressure = (pressure // var1) * 2

            var1 = (self.dig_p9 * ((pressure // 8) * (pressure // 8)) // 8192) // 4096
            var2 = ((pressure // 4) * self.dig_p8) // 8192
            pressure = pressure + ((var1 + var2 + self.dig_p7) // 16)
        else:
            pressure = 30000

        var1 = self.t_fine - 768000
        var2 = uhumidity * 16384
        var3 = self.dig_h4 * 1048576
        var4 = self.dig_h5 * var1
        var5 = (((var2 - var3) - var4) + 16384) // 32768
        var2 = (var1 * self.dig_h6) // 1024
        var3 = (var1 * self.dig_h3) // 2048
        var4 = ((var2 * (var3 + 32768)) // 1024) + 2097152
        var2 = ((var4 * self.dig_h2) + 8192) // 16384
        var3 = var5 * var2
        var4 = ((var3 // 32768) * (var3 // 32768)) // 128
        var5 = var3 - ((var4 * self.dig_h1) // 16)
        var5 = 0 if var5 < 0 else var5
        var5 = 419430400 if var5 > 419430400 else var5
        humidity = var5 // 4096

        return temperature, pressure, humidity
