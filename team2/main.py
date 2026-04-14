from drivers.spi_core import SPICore
from drivers.flash_driver import FlashDriver
from tests.spi_tests import SPITester
from utils.logger import Logger

def main():
    logger = Logger()

    spi = SPICore(bus=0, device=0, speed=1000000)
    flash = FlashDriver(spi)

    tester = SPITester(flash, spi, logger)

    tester.run_all()

    spi.close()

if __name__ == "__main__":
    main()