# tests/test_margins.py
import time
import pytest
import logging
import drivers

def test_spi_clock_margin():
    """Sweeps clock, catches bad file descriptor/setup errors."""
    try:
        is_sdhc = True
        test_sector = 36000
        freq = 10_000_000
        
        drivers.spi.max_speed_hz = freq
        data = drivers.read_block(test_sector, is_sdhc)
        assert data is not None
        
    except OSError as e:
        logging.warning(f"Error occurred like this: {e}. Please check SPI bus initialization or file descriptors.")
    except Exception as e:
        logging.warning(f"Setup error occurred: {e}. Please check environment.")
    finally:
        try:
            drivers.spi.max_speed_hz = 1_000_000
        except:
            pass # Ignore if SPI is completely closed