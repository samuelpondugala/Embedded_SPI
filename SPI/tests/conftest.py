# tests/conftest.py
import pytest
import logging
import drivers

@pytest.fixture(scope="session", autouse=True)
def sd_env():
    """
    Initializes SPI and SD Card globally.
    autouse=True ensures the bus is opened before ANY test runs, 
    even if a specific test doesn't explicitly request 'sd_env' in its arguments.
    """
    logging.info("Initializing SPI & SD Card Interface...")
    
    # Default empty environment in case of hardware failure
    env = {}
    
    try:
        # 1. Open the bus globally for the whole test session
        drivers.spi.open(0, 1) 
        drivers.spi.max_speed_hz = 1_000_000
        
        # 2. Initialize SD Card
        drivers.init_sd()
        is_sdhc = drivers.read_ocr()

        # 3. Parse MBR and Boot Sector
        mbr = drivers.read_block(0, is_sdhc)
        
        if mbr is not None:
            partition_start = int.from_bytes(mbr[454:458], 'little')
            boot = drivers.read_block(partition_start, is_sdhc)
            
            reserved = boot[14] | (boot[15] << 8)
            fats = boot[16]
            spf = int.from_bytes(boot[36:40], 'little')
            spc = boot[13]
            root_cluster = int.from_bytes(boot[44:48], 'little')

            fat_start = partition_start + reserved
            data_start = partition_start + reserved + (fats * spf)

            env = {
                "is_sdhc": is_sdhc,
                "fat_start": fat_start,
                "data_start": data_start,
                "spc": spc,
                "root_cluster": root_cluster
            }
            logging.info(f"SD Card Mounted. SDHC: {is_sdhc}, Data Start Sector: {data_start}")
        else:
            logging.warning("Failed to read MBR! Bus is open, but data is missing. Check wiring.")

    except OSError as e:
        # Catch Bad File Descriptor or missing SPI interface
        logging.error(f"Hardware blocked or missing: {e}. Tests will run in safe-fail mode.")
    except Exception as e:
        # Catch unexpected initialization crashes
        logging.error(f"Unexpected setup error: {e}")

    # 4. Yield the environment to the tests
    # Tests that request 'sd_env' get this dictionary.
    # Tests that don't request it still benefit from the bus being open.
    yield env
    
    # 5. Teardown: Safely close the bus after all tests finish
    logging.info("Tearing down SPI Bus...")
    try:
        drivers.spi.close()
    except OSError:
        pass # Ignore if it's already closed or never opened