# tests/test_margins.py
import time
import pytest
import logging
import drivers

CLOCK_SPEEDS = [400_000, 1_000_000, 5_000_000, 10_000_000, 20_000_000]

def test_spi_clock_margin(sd_env):
    """Sweeps the SPI clock to discover the maximum stable throughput."""
    is_sdhc = sd_env["is_sdhc"]
    test_sector = sd_env["data_start"] + 2000
    blocks_to_read = 20
    
    max_stable_freq = 0
    
    try:
        for freq in CLOCK_SPEEDS:
            drivers.spi.max_speed_hz = freq
            logging.info(f"Testing SPI stability at {freq / 1_000_000} MHz...")
            
            start_time = time.perf_counter()
            
            # Attempt to read blocks
            success = True
            for i in range(blocks_to_read):
                data = drivers.read_block(test_sector + i, is_sdhc)
                if data is None:
                    success = False
                    break
                    
            if not success:
                logging.warning(f"Communication degraded at {freq / 1_000_000} MHz. Physical limit reached.")
                break # Stop testing higher frequencies
                
            end_time = time.perf_counter()
            
            bytes_transferred = blocks_to_read * 512
            elapsed = end_time - start_time
            throughput = (bytes_transferred * 8) / elapsed / 1_000_000
            
            logging.info(f"Pass! Throughput: {throughput:.2f} Mbps")
            max_stable_freq = freq

    finally:
        # CRITICAL FIX: Always reset back to a safe 1MHz so next tests don't crash!
        drivers.spi.max_speed_hz = 1_000_000
        
    assert max_stable_freq >= 1_000_000, "Bus is unstable even at 1 MHz! Check wiring."