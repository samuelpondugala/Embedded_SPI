# FIXED VERSION (SAFE + STABLE)
import spidev
import time

spi = spidev.SpiDev()

# ---------------- SEND COMMAND ----------------
def send_cmd(cmd, arg, crc):
    packet = [
        0x40 | cmd,
        (arg >> 24) & 0xFF,
        (arg >> 16) & 0xFF,
        (arg >> 8) & 0xFF,
        arg & 0xFF,
        crc
    ]

    spi.xfer([0xFF])
    spi.xfer(packet)

    for _ in range(20):
        r = spi.xfer([0xFF])[0]
        if r != 0xFF:
            return r
    return -1

# ---------------- INIT SD ----------------
def init_sd():
    spi.max_speed_hz = 400000
    spi.xfer([0xFF] * 10)

    print("CMD0:", hex(send_cmd(0, 0, 0x95)))
    print("CMD8:", hex(send_cmd(8, 0x1AA, 0x87)))

    while True:
        send_cmd(55, 0, 0)
        resp = send_cmd(41, 0x40000000, 0)
        if resp == 0:
            break

    print("Card initialized!")

# ---------------- READ OCR ----------------
def read_ocr():
    send_cmd(58, 0, 0)
    ocr = spi.xfer([0xFF]*4)
    print("OCR:", ocr)
    return True if (ocr[0] & 0x40) else False

# ---------------- READ BLOCK ----------------
def read_block(block, is_sdhc):
    addr = block if is_sdhc else block * 512

    spi.xfer([0xFF])

    if send_cmd(17, addr, 0) != 0x00:
        return None

    for _ in range(10000):
        if spi.xfer([0xFF])[0] == 0xFE:
            break

    data = spi.xfer([0xFF] * 512)
    spi.xfer([0xFF, 0xFF])

    return data

# ---------------- WRITE BLOCK ----------------
def write_block(block, data, is_sdhc):
    addr = block if is_sdhc else block * 512

    spi.xfer([0xFF])

    if send_cmd(24, addr, 0) != 0x00:
        print("CMD24 failed")
        return False

    spi.xfer([0xFE])

    data = data + [0x00] * (512 - len(data))
    spi.xfer(data)

    spi.xfer([0xFF, 0xFF])

    resp = spi.xfer([0xFF])[0]
    if (resp & 0x1F) != 0x05:
        print("Write rejected")
        return False

    timeout = 5000
    while timeout > 0:
        if spi.xfer([0xFF])[0] != 0x00:
            break
        timeout -= 1

    return True

# ---------------- FAT ----------------
def read_fat_entry(cluster, fat_start, is_sdhc):
    fat_offset = cluster * 4
    fat_sector = fat_start + (fat_offset // 512)
    offset = fat_offset % 512

    sector = read_block(fat_sector, is_sdhc)
    if sector is None:
        return 0xFFFFFFFF

    return int.from_bytes(sector[offset:offset+4], 'little') & 0x0FFFFFFF


def write_fat_entry(cluster, value, fat_start, spf, is_sdhc):
    fat_offset = cluster * 4
    fat_sector = fat_start + (fat_offset // 512)
    offset = fat_offset % 512

    sector = read_block(fat_sector, is_sdhc)
    if sector is None:
        return

    val_bytes = value.to_bytes(4, 'little')
    for i in range(4):
        sector[offset + i] = val_bytes[i]

    # write both FAT copies
    write_block(fat_sector, sector, is_sdhc)
    write_block(fat_sector + spf, sector, is_sdhc)

# ---------------- CLUSTER ----------------
def cluster_to_sector(cluster, data_start, spc):
    return data_start + (cluster - 2) * spc

# ---------------- FIND FREE ----------------
def find_free_cluster(fat_start, is_sdhc):
    for cluster in range(2, 65536):
        if read_fat_entry(cluster, fat_start, is_sdhc) == 0:
            return cluster
    return None

# ---------------- CREATE ENTRY ----------------
def create_dir_entry(name, ext, cluster, size, is_dir=False):
    entry = [0] * 32

    name = name.ljust(8)[:8]
    ext = ext.ljust(3)[:3]

    entry[0:8] = list(name.encode())
    entry[8:11] = list(ext.encode())
    entry[11] = 0x10 if is_dir else 0x20

    entry[26:28] = list(cluster.to_bytes(2, 'little'))
    entry[20:22] = list((cluster >> 16).to_bytes(2, 'little'))
    entry[28:32] = list(size.to_bytes(4, 'little'))

    return entry

# ---------------- SIMPLE DIRECTORY WRITE ----------------
def write_dir_entry(current_cluster, entry, data_start, spc, fat_start, is_sdhc):
    dir_sector = cluster_to_sector(current_cluster, data_start, spc)
    dir_data = read_block(dir_sector, is_sdhc)

    for i in range(0, 512, 32):
        if dir_data[i] == 0x00 or dir_data[i] == 0xE5:
            for j in range(32):
                dir_data[i + j] = entry[j]

            write_block(dir_sector, dir_data, is_sdhc)
            return True

    print("Directory full")
    return False

# ---------------- CREATE FILE ----------------
def create_file(filename, content, current_cluster, data_start, spc, fat_start, spf, is_sdhc):
    name, ext = filename.upper().split('.')

    cluster = find_free_cluster(fat_start, is_sdhc)
    print("Allocating cluster:", cluster)

    write_fat_entry(cluster, 0x0FFFFFFF, fat_start, spf, is_sdhc)

    data = list(content.encode())
    sector = cluster_to_sector(cluster, data_start, spc)
    write_block(sector, data, is_sdhc)

    entry = create_dir_entry(name, ext, cluster, len(data))

    if write_dir_entry(current_cluster, entry, data_start, spc, fat_start, is_sdhc):
        print("File created")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    spi.open(0, 0)

    init_sd()
    is_sdhc = read_ocr()

    spi.max_speed_hz = 1000000

    mbr = read_block(0, is_sdhc)
    partition_start = int.from_bytes(mbr[454:458], 'little')

    boot = read_block(partition_start, is_sdhc)

    reserved = boot[14] | (boot[15] << 8)
    fats = boot[16]
    spf = int.from_bytes(boot[36:40], 'little')
    spc = boot[13]
    root_cluster = int.from_bytes(boot[44:48], 'little')

    fat_start = partition_start + reserved
    data_start = partition_start + reserved + (fats * spf)

    # TEST WRITE
    create_file("TEST.TXT", "Hello", root_cluster, data_start, spc, fat_start, spf, is_sdhc)

    print("Done")