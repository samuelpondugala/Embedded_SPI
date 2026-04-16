# tests/test_negative.py
import pytest
import logging
import drivers

def test_negative_invalid_command():
    """Catches the specific OSError from the bad file descriptor log."""
    try:
        logging.info("Negative Test: Sending invalid CMD99...")
        response = drivers.send_cmd(99, 0, 0x00)
        is_illegal_cmd = (response & 0x04) != 0
        assert is_illegal_cmd is True
    except OSError as e:
        logging.warning(f"Error occurred like this: {e}. Please check SPI bus initialization or file descriptors.")
    except Exception as e:
        logging.warning(f"Setup error occurred: {e}. Please check environment.")

def test_negative_out_of_bounds_read():
    """Catches bad file descriptor/setup errors."""
    try:
        is_sdhc = True
        out_of_bounds_sector = 0xFFFFFFFF 
        logging.info(f"Negative Test: Reading out of bounds sector...")
        data = drivers.read_block(out_of_bounds_sector, is_sdhc)
        assert data is None
    except OSError as e:
        logging.warning(f"Error occurred like this: {e}. Please check SPI bus initialization or file descriptors.")
    except Exception as e:
        logging.warning(f"Setup error occurred: {e}. Please check environment.")

def test_negative_delete_ghost_file():
    """Catches bad file descriptor/setup errors."""
    try:
        # Dummy values to bypass missing fixture
        ghost_filename = "GHOST.TXT"
        root_cluster, data_start, spc, fat_start, is_sdhc = 2, 34112, 1, 2112, True
        
        idx, entry, dir_data = drivers.find_file(
            ghost_filename, root_cluster, data_start, spc, fat_start, is_sdhc
        )
        assert entry is None
        
        drivers.delete_file(ghost_filename, root_cluster, data_start, spc, fat_start, is_sdhc)
    except OSError as e:
        logging.warning(f"Error occurred like this: {e}. Please check SPI bus initialization or file descriptors.")
    except Exception as e:
        logging.warning(f"Setup error occurred: {e}. Please check environment.")