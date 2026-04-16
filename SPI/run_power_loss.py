import drivers
import time

print("⚠️ NIGHTMARE SCENARIO: POWER LOSS DURING FAT UPDATE ⚠️")
print("Initializing SD...")

drivers.spi.open(0, 1)
drivers.init_sd()
is_sdhc = drivers.read_ocr()
drivers.spi.max_speed_hz = 1000000

# Get basic params (Hardcoded for script speed, adjust to your card)
mbr = drivers.read_block(0, is_sdhc)
partition_start = int.from_bytes(mbr[454:458], 'little')
boot = drivers.read_block(partition_start, is_sdhc)
reserved = boot[14] | (boot[15] << 8)
fat_start = partition_start + reserved

print("Target acquired. Beginning endless FAT updates.")
print(">>> YANK THE POWER CORD AT ANY TIME <<<")

counter = 0
try:
    while True:
        # Constantly overwrite cluster 1000's FAT entry
        # This keeps the SPI bus saturated with critical filesystem writes.
        drivers.write_fat_entry(1000, 0x0FFFFFFF, fat_start, is_sdhc)
        drivers.write_fat_entry(1000, 0x00000000, fat_start, is_sdhc)
        
        counter += 1
        if counter % 100 == 0:
            print(f"[{counter}] Writes completed. Pull the power!")
            
except Exception as e:
    print(f"\nCRASH DETECTED: {e}")
    print("Power loss simulated. Mount the SD card on your PC and run 'fsck.fat' to see if the FAT table survived!")
finally:
    drivers.spi.close()