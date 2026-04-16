# tests/test_integrity.py
import pytest
import logging
import drivers

@pytest.mark.parametrize("pattern_val", [0xAA, 0x55, 0xFF, 0x00])
def test_raw_block_write_read(sd_env, pattern_val):
    """Writes a stressful bit pattern to a safe raw sector and verifies it."""
    is_sdhc = sd_env["is_sdhc"]
    
    # Use a sector safely inside the data partition, away from FAT tables
    test_sector = sd_env["data_start"] + 1000 
    
    pattern = [pattern_val] * 512
    logging.info(f"Writing pattern {hex(pattern_val)} to sector {test_sector}...")
    
    success = drivers.write_block(test_sector, pattern, is_sdhc)
    
    # If this still fails, physical write-protection might be enabled on the SD adapter
    assert success is True, f"Block write rejected by SD Card for pattern {hex(pattern_val)}"
    
    read_data = drivers.read_block(test_sector, is_sdhc)
    assert read_data is not None, "Block read timed out."
    
    assert read_data == pattern, f"Data corruption detected on pattern {hex(pattern_val)}!"
    logging.info(f"Pattern {hex(pattern_val)} verified successfully.")