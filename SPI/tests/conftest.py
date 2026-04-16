# tests/conftest.py
import pytest
import logging
import drivers

@pytest.fixture(scope="session")
def sd_env():
    """Initializes SPI, mounts the SD card, and extracts FAT parameters."""
    logging.info("Initializing SPI & SD Card Interface...")
    
    # Open the bus
    drivers.spi.open(0, 1) 
    
    # Initialize SD Card
    drivers.init_sd()
    is_sdhc = drivers.read_ocr()
    drivers.spi.max_speed_hz = 1000000

    # Parse MBR and Boot Sector
    mbr = drivers.read_block(0, is_sdhc)
    assert mbr is not None, "Failed to read MBR! Check wiring."
    
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
    
    yield env
    
    logging.info("Tearing down SPI Bus...")
    drivers.spi.close()