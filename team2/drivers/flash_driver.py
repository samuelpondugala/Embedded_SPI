import time

CMD_JEDEC_ID = 0x9F
CMD_READ     = 0x03
CMD_WRITE_EN = 0x06
CMD_PAGE_PRG = 0x02
CMD_SECTOR_ERASE = 0x20
CMD_READ_STATUS = 0x05

class FlashDriver:
    def __init__(self, spi):
        self.spi = spi

    def read_jedec_id(self):
        resp = self.spi.transfer([CMD_JEDEC_ID, 0, 0, 0])
        return resp[1:]

    def write_enable(self):
        self.spi.transfer([CMD_WRITE_EN])

    def wait_busy(self):
        while True:
            status = self.spi.transfer([CMD_READ_STATUS, 0])[1]
            if (status & 0x01) == 0:
                break

    def read_data(self, addr, length):
        cmd = [
            CMD_READ,
            (addr >> 16) & 0xFF,
            (addr >> 8) & 0xFF,
            addr & 0xFF
        ]
        resp = self.spi.transfer(cmd + [0]*length)
        return resp[4:]

    def page_program(self, addr, data):
        self.write_enable()

        cmd = [
            CMD_PAGE_PRG,
            (addr >> 16) & 0xFF,
            (addr >> 8) & 0xFF,
            addr & 0xFF
        ]

        self.spi.transfer(cmd + data)
        self.wait_busy()

    def sector_erase(self, addr):
        self.write_enable()

        cmd = [
            CMD_SECTOR_ERASE,
            (addr >> 16) & 0xFF,
            (addr >> 8) & 0xFF,
            addr & 0xFF
        ]

        self.spi.transfer(cmd)
        self.wait_busy()