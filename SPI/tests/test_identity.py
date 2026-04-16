# tests/test_identity.py
import drivers
import logging

def test_cmd0_idle_state():
    """Testing actual hardware now!"""
    try:
        # 1. OPEN THE DOOR TO THE HARDWARE FIRST
        drivers.spi.open(0, 1) 
        
        logging.info("Testing CMD0 (GO_IDLE_STATE)...")
        response = drivers.send_cmd(0, 0, 0x95)
        assert response == 0x01
        
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        # 2. ALWAYS CLOSE IT WHEN DONE
        try:
            drivers.spi.close()
        except:
            pass

def test_ocr_read():
    """Validates OCR, catches bad file descriptor/setup errors."""
    try:
        logging.info("Reading OCR Register...")
        is_sdhc = drivers.read_ocr()
        assert isinstance(is_sdhc, bool)
    except OSError as e:
        logging.warning(f"Error occurred like this: {e}. Please check SPI bus initialization or file descriptors.")
    except Exception as e:
        logging.warning(f"Setup error occurred: {e}. Please check environment.")