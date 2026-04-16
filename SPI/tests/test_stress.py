# tests/test_stress.py
import logging
import drivers

def test_fat32_filesystem_churn(sd_env):
    """Stress tests the FAT allocation logic by rapidly creating and deleting a file."""
    filename = "STRESS.TXT"
    content = "V&V STRESS TEST PAYLOAD." * 5
    iterations = 5
    
    logging.info("Starting FAT32 File System Churn Test...")
    
    for i in range(iterations):
        logging.info(f"Churn Iteration {i+1}/{iterations}...")
        
        drivers.create_file(
            filename, content, sd_env["root_cluster"], sd_env["data_start"], 
            sd_env["spc"], sd_env["fat_start"], sd_env["is_sdhc"]
        )
        
        idx, entry, dir_data = drivers.find_file(
            filename, sd_env["root_cluster"], sd_env["data_start"], 
            sd_env["spc"], sd_env["fat_start"], sd_env["is_sdhc"]
        )
        assert entry is not None, f"File creation failed silently on loop {i}"
        
        drivers.delete_file(
            filename, sd_env["root_cluster"], sd_env["data_start"], 
            sd_env["spc"], sd_env["fat_start"], sd_env["is_sdhc"]
        )
        
        idx, entry, dir_data = drivers.find_file(
            filename, sd_env["root_cluster"], sd_env["data_start"], 
            sd_env["spc"], sd_env["fat_start"], sd_env["is_sdhc"]
        )
        assert entry is None, f"File deletion failed; zombie file left on loop {i}"
        
    logging.info("File system churn completed successfully without FAT corruption.")