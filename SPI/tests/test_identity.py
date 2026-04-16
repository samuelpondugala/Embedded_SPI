# tests/test_identity.py
import drivers
import logging

def test_cmd0_idle_state(sd_env):
    """Validates that CMD0 safely puts the card into IDLE state."""
    logging.info("Testing CMD0 (GO_IDLE_STATE)...")
    response = drivers.send_cmd(0, 0, 0x95)
    assert response == 0x01, f"CMD0 failed. Expected 0x01, got {hex(response)}"
    logging.info("CMD0 Successful.")

def test_ocr_read(sd_env):
    """Validates the OCR register returns a valid boolean SDHC flag."""
    logging.info("Reading OCR Register...")
    is_sdhc = drivers.read_ocr()
    assert isinstance(is_sdhc, bool), "OCR read did not return a boolean flag!"
    logging.info(f"OCR Read Successful. SDHC Status: {is_sdhc}")