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
    r = send_cmd(58, 0, 0)
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


# ---------------- FAT ENTRY ----------------
def read_fat_entry(cluster, fat_start, is_sdhc):
    fat_offset = cluster * 4
    fat_sector = fat_start + (fat_offset // 512)
    offset = fat_offset % 512

    sector = read_block(fat_sector, is_sdhc)
    return int.from_bytes(sector[offset:offset+4], 'little') & 0x0FFFFFFF


# ---------------- CLUSTER → SECTOR ----------------
def cluster_to_sector(cluster, data_start, spc):
    return data_start + (cluster - 2) * spc


# ---------------- READ DIRECTORY ----------------
def read_directory(start_cluster, data_start, spc, fat_start, is_sdhc):
    cluster = start_cluster
    data_all = []
    visited = set()

    while cluster >= 2 and cluster < 0x0FFFFFF8:
        if cluster in visited:
            break
        visited.add(cluster)

        sector = cluster_to_sector(cluster, data_start, spc)

        for i in range(spc):
            d = read_block(sector + i, is_sdhc)
            if d:
                data_all.extend(d)

        cluster = read_fat_entry(cluster, fat_start, is_sdhc)

    return data_all


# ---------------- LIST FILES ----------------
def list_files(data):
    print("\n--- FILES ---")

    files = []

    for i in range(0, len(data), 32):
        entry = data[i:i+32]

        if entry[0] == 0x00:
            break
        if entry[0] == 0xE5 or entry[11] == 0x0F:
            continue

        name = bytes(entry[0:8]).decode('ascii', errors='ignore').strip()
        ext  = bytes(entry[8:11]).decode('ascii', errors='ignore').strip()
        size = int.from_bytes(entry[28:32], 'little')

        cl_low  = int.from_bytes(entry[26:28], 'little')
        cl_high = int.from_bytes(entry[20:22], 'little')
        cluster = (cl_high << 16) | cl_low

        if not name:
            continue

        if entry[11] & 0x10:
            print(f"[DIR ] {name} (cluster {cluster})")
        else:
            print(f"[FILE] {name}.{ext} Size:{size} (cluster {cluster})")
            files.append((name, ext, cluster, size))

    return files


# ---------------- READ FILE ----------------
def read_file(start_cluster, data_start, spc, fat_start, is_sdhc, size):
    cluster = start_cluster
    data_all = []
    visited = set()

    while cluster < 0x0FFFFFF8:
        if cluster in visited:
            break
        visited.add(cluster)

        sector = cluster_to_sector(cluster, data_start, spc)

        for i in range(spc):
            d = read_block(sector + i, is_sdhc)
            if d:
                data_all.extend(d)

        cluster = read_fat_entry(cluster, fat_start, is_sdhc)

    return data_all[:size]  # trim exact size


# ---------------- CLI EXPLORER ----------------
def cli_explorer(root_cluster, data_start, spc, fat_start, is_sdhc):
    current_cluster = root_cluster
    path_stack = [(root_cluster, "/")]  # start with root

    while True:
        cmd = input("\nSD> ").strip().upper()

        if cmd == "EXIT":
            break

        elif cmd == "LS":
            data = read_directory(current_cluster, data_start, spc, fat_start, is_sdhc)
            list_files(data)

        elif cmd.startswith("CD "):
            target = cmd[3:].strip()

            # handle cd ..
            if target == "..":
                if len(path_stack) > 1:
                    path_stack.pop()
                    current_cluster = path_stack[-1][0]
                continue

            data = read_directory(current_cluster, data_start, spc, fat_start, is_sdhc)

            found = False
            for i in range(0, len(data), 32):
                entry = data[i:i+32]

                if entry[0] == 0x00:
                    break
                if entry[0] == 0xE5 or entry[11] == 0x0F:
                    continue

                name = bytes(entry[0:8]).decode('ascii', errors='ignore').strip()
                attr = entry[11]

                if name.upper() == target and (attr & 0x10):
                    cl_low  = int.from_bytes(entry[26:28], 'little')
                    cl_high = int.from_bytes(entry[20:22], 'little')
                    cluster = (cl_high << 16) | cl_low

                    if cluster == 0:
                        continue  # ignore invalid

                    path_stack.append((cluster, target.lower()))
                    current_cluster = cluster
                    found = True
                    break

            if not found:
                print("Directory not found")

        elif cmd.startswith("TOUCH "):
            filename = cmd[6:].strip()
            create_file(filename, "", current_cluster, data_start, spc, fat_start, is_sdhc)

        elif cmd.startswith("WRITE "):
            parts = cmd.split(" ", 2)

            if len(parts) < 3:
                print("Usage: write filename content")
                continue

            filename = parts[1]
            content = parts[2]

            create_file(filename, content, current_cluster, data_start, spc, fat_start, is_sdhc)

        elif cmd == "PWD":
            path = "/".join([p[1] for p in path_stack if p[1] != "/"])
            print("/" + path if path else "/")

        elif cmd.startswith("RM "):
            filename = cmd[3:].strip()
            delete_file(filename, current_cluster, data_start, spc, fat_start, is_sdhc)

        elif cmd.startswith("MKDIR "):
            dirname = cmd[6:].strip()
            create_directory(dirname, current_cluster, data_start, spc, fat_start, is_sdhc)

        elif cmd.startswith("RMDIR"):
            parts = cmd.split()

            if len(parts) < 2:
                print("Usage: rmdir [-r] dirname")
                continue

            recursive = False

            if parts[1].upper() == "-R":
                recursive = True
                dirname = parts[2] if len(parts) > 2 else ""
            else:
                dirname = parts[1]

            dirname = dirname.upper()

            idx, entry, dir_data = find_file(dirname, current_cluster, data_start, spc, fat_start, is_sdhc)

            if not entry:
                print("Directory not found")
                continue

            if not (entry[11] & 0x10):
                print("Not a directory")
                continue

            cl_low  = int.from_bytes(entry[26:28], 'little')
            cl_high = int.from_bytes(entry[20:22], 'little')
            cluster = (cl_high << 16) | cl_low

            if recursive:
                # 🔥 delete contents
                delete_directory_recursive(cluster, data_start, spc, fat_start, is_sdhc)

                # 🔥 REMOVE ENTRY FROM PARENT (CRITICAL FIX)
                dir_data[idx] = 0xE5

                # 🔥 WRITE BACK ROOT DIRECTORY
                dir_sector = cluster_to_sector(current_cluster, data_start, spc)
                write_block(dir_sector, dir_data[:512], is_sdhc)

                print("Directory recursively deleted:", dirname)

            else:
                delete_directory(dirname, current_cluster, data_start, spc, fat_start, is_sdhc)
        

        elif cmd.startswith("CAT "):
            target = cmd[4:].strip()

            data = read_directory(current_cluster, data_start, spc, fat_start, is_sdhc)

            found = False
            for i in range(0, len(data), 32):
                entry = data[i:i+32]

                if entry[0] == 0x00:
                    break
                if entry[0] == 0xE5 or entry[11] == 0x0F:
                    continue

                if entry[0] in (0x00, 0xE5):
                    continue

                if entry[11] == 0x0F:
                    continue

                raw_name = bytes(entry[0:8])
                name = raw_name.decode('ascii', errors='ignore').strip()
                ext  = bytes(entry[8:11]).decode('ascii', errors='ignore').strip()
                attr = entry[11]

                full_name = f"{name}.{ext}".strip(".")

                if full_name.upper() == target and not (attr & 0x10):
                    cl_low  = int.from_bytes(entry[26:28], 'little')
                    cl_high = int.from_bytes(entry[20:22], 'little')
                    cluster = (cl_high << 16) | cl_low
                    size = int.from_bytes(entry[28:32], 'little')

                    file_data = read_file(cluster, data_start, spc, fat_start, is_sdhc, size)

                    print("\n--- FILE CONTENT ---")
                    print(bytes(file_data).decode('utf-8', errors='ignore'))
                    found = True
                    break

            if not found:
                print("File not found")

        else:
            print("Commands: ls, cd <dir>, cd .., cat <file>, pwd, exit")

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

    # ✅ FIX: safe timeout (NO infinite loop)
    timeout = 5000

    while timeout > 0:
        if spi.xfer([0xFF])[0] != 0x00:
            break
        timeout -= 1

    if timeout == 0:
        print("Write timeout!")
        return False

    return True

def find_free_cluster(fat_start, is_sdhc):
    for cluster in range(2, 10000):
        val = read_fat_entry(cluster, fat_start, is_sdhc)
        if val == 0:
            return cluster
    return None

def write_fat_entry(cluster, value, fat_start, is_sdhc):
    fat_offset = cluster * 4
    fat_sector = fat_start + (fat_offset // 512)
    offset = fat_offset % 512

    sector = read_block(fat_sector, is_sdhc)
    if sector is None:
        print("FAT read failed")
        return

    val_bytes = value.to_bytes(4, 'little')
    for i in range(4):
        sector[offset + i] = val_bytes[i]

    write_block(fat_sector, sector, is_sdhc)
    

def create_dir_entry(name, ext, cluster, size):
    entry = [0] * 32

    name = name.ljust(8)[:8]
    ext = ext.ljust(3)[:3]

    entry[0:8] = list(name.encode('ascii'))
    entry[8:11] = list(ext.encode('ascii'))

    entry[11] = 0x20  # file

    entry[26:28] = list(cluster.to_bytes(2, 'little'))
    entry[20:22] = list((cluster >> 16).to_bytes(2, 'little'))

    entry[28:32] = list(size.to_bytes(4, 'little'))

    return entry

def create_file(filename, content, current_cluster, data_start, spc, fat_start, is_sdhc):
    try:
        name, ext = filename.upper().split('.')
    except:
        print("Invalid filename. Use format: name.txt")
        return

    free_cluster = find_free_cluster(fat_start, is_sdhc)
    if not free_cluster:
        print("No free cluster available")
        return

    print("Creating new file at cluster:", free_cluster)

    # Mark FAT (end of chain)
    write_fat_entry(free_cluster, 0x0FFFFFFF, fat_start, is_sdhc)

    # Write file content
    data_bytes = list(content.encode('utf-8'))
    sector = cluster_to_sector(free_cluster, data_start, spc)
    write_block(sector, data_bytes, is_sdhc)

    # Create directory entry
    entry = create_dir_entry(name, ext, free_cluster, len(data_bytes))

    dir_data = read_directory(current_cluster, data_start, spc, fat_start, is_sdhc)

    for i in range(0, len(dir_data), 32):
        if dir_data[i] in (0x00, 0xE5):  # free slot
            for j in range(32):
                dir_data[i + j] = entry[j]

            # Write back directory sector
            dir_sector = cluster_to_sector(current_cluster, data_start, spc)
            write_block(dir_sector, dir_data[:512], is_sdhc)

            print("File created:", filename)
            return

    print("No space in directory")

def find_file(filename, current_cluster, data_start, spc, fat_start, is_sdhc):
    data = read_directory(current_cluster, data_start, spc, fat_start, is_sdhc)

    filename = filename.upper()

    if '.' in filename:
        name, ext = filename.split('.')
    else:
        name = filename
        ext = None  # directory case

    for i in range(0, len(data), 32):
        entry = data[i:i+32]

        if entry[0] == 0x00:
            break
        if entry[0] == 0xE5 or entry[11] == 0x0F:
            continue

        ename = bytes(entry[0:8]).decode().strip()
        eext  = bytes(entry[8:11]).decode().strip()

        if ext is None:
            # DIRECTORY MATCH
            if ename == name:
                return i, entry, data
        else:
            # FILE MATCH
            if ename == name and eext == ext:
                return i, entry, data

    return None, None, data


def delete_file(filename, current_cluster, data_start, spc, fat_start, is_sdhc):
    idx, entry, dir_data = find_file(filename, current_cluster, data_start, spc, fat_start, is_sdhc)

    if not entry:
        print("File not found")
        return

    # get cluster
    cl_low  = int.from_bytes(entry[26:28], 'little')
    cl_high = int.from_bytes(entry[20:22], 'little')
    cluster = (cl_high << 16) | cl_low

    # free FAT
    if cluster != 0:
        write_fat_entry(cluster, 0x00000000, fat_start, is_sdhc)

    # mark deleted
    dir_data[idx] = 0xE5

    # write back
    dir_sector = cluster_to_sector(current_cluster, data_start, spc)
    write_block(dir_sector, dir_data[:512], is_sdhc)

    print("File deleted:", filename)

def create_directory(dirname, current_cluster, data_start, spc, fat_start, is_sdhc):
    dirname = dirname.upper()

    free_cluster = find_free_cluster(fat_start, is_sdhc)
    if not free_cluster:
        print("No free cluster")
        return

    print("Allocating cluster:", free_cluster)

    # mark cluster end
    write_fat_entry(free_cluster, 0x0FFFFFFF, fat_start, is_sdhc)

    # create empty cluster
    sector = cluster_to_sector(free_cluster, data_start, spc)
    empty = [0x00] * 512
    write_block(sector, empty, is_sdhc)

    # create "." and ".."
    dot = create_dir_entry(".", "", free_cluster, 0)
    dotdot = create_dir_entry("..", "", current_cluster, 0)
    dot[11] = 0x10
    dotdot[11] = 0x10

    cluster_data = dot + dotdot + [0x00] * (512 - 64)
    write_block(sector, cluster_data, is_sdhc)

    # add entry in parent dir
    dir_data = read_directory(current_cluster, data_start, spc, fat_start, is_sdhc)

    for i in range(0, len(dir_data), 32):
        if dir_data[i] == 0x00:
            entry = create_dir_entry(dirname, "", free_cluster, 0)
            entry[11] = 0x10  # directory

            for j in range(32):
                dir_data[i + j] = entry[j]

            dir_sector = cluster_to_sector(current_cluster, data_start, spc)
            write_block(dir_sector, dir_data[:512], is_sdhc)

            print("Directory created:", dirname)
            return

def delete_directory(dirname, current_cluster, data_start, spc, fat_start, is_sdhc):
    idx, entry, dir_data = find_file(dirname, current_cluster, data_start, spc, fat_start, is_sdhc)

    if not entry:
        print("Directory not found")
        return

    if not (entry[11] & 0x10):
        print("Not a directory")
        return

    cl_low  = int.from_bytes(entry[26:28], 'little')
    cl_high = int.from_bytes(entry[20:22], 'little')
    cluster = (cl_high << 16) | cl_low

    # check if empty
    sub = read_directory(cluster, data_start, spc, fat_start, is_sdhc)

    for i in range(64, len(sub), 32):  # skip . and ..
        if sub[i] not in (0x00, 0xE5):
            print("Directory not empty")
            return

    # free FAT
    write_fat_entry(cluster, 0x00000000, fat_start, is_sdhc)

    # mark deleted
    dir_data[idx] = 0xE5

    dir_sector = cluster_to_sector(current_cluster, data_start, spc)
    write_block(dir_sector, dir_data[:512], is_sdhc)

    print("Directory removed:", dirname)

def delete_directory_recursive(cluster, data_start, spc, fat_start, is_sdhc):
    print(f"\nEntering directory cluster: {cluster}")

    data = read_directory(cluster, data_start, spc, fat_start, is_sdhc)

    for i in range(0, len(data), 32):
        entry = data[i:i+32]

        # ✅ STOP at end of directory
        if entry[0] == 0x00:
            break

        # skip deleted / LFN
        if entry[0] == 0xE5 or entry[11] == 0x0F:
            continue

        name = bytes(entry[0:8]).decode('ascii', errors='ignore').strip()

        if name in (".", ".."):
            continue

        cl_low  = int.from_bytes(entry[26:28], 'little')
        cl_high = int.from_bytes(entry[20:22], 'little')
        sub_cluster = (cl_high << 16) | cl_low

        # ✅ VALIDATION (CRITICAL)
        if sub_cluster < 2 or sub_cluster >= 0x0FFFFFF8:
            continue

        print(f"Deleting: {name}, cluster: {sub_cluster}")

        if entry[11] & 0x10:
            # directory → recurse
            delete_directory_recursive(sub_cluster, data_start, spc, fat_start, is_sdhc)
        else:
            # file → free FAT
            write_fat_entry(sub_cluster, 0, fat_start, is_sdhc)

        # mark entry deleted
        data[i] = 0xE5

    # write directory back
    dir_sector = cluster_to_sector(cluster, data_start, spc)
    write_block(dir_sector, data[:512], is_sdhc)

    # free this directory
    write_fat_entry(cluster, 0, fat_start, is_sdhc)

    print(f"Freed cluster: {cluster}")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    spi.open(0, 0)

    init_sd()
    is_sdhc = read_ocr()

    spi.max_speed_hz = 1000000

    # MBR
    mbr = read_block(0, is_sdhc)
    partition_start = int.from_bytes(mbr[454:458], 'little')

    print("\nPartition start:", partition_start)

    # Boot
    boot = read_block(partition_start, is_sdhc)

    reserved = boot[14] | (boot[15] << 8)
    fats = boot[16]
    spf = int.from_bytes(boot[36:40], 'little')
    spc = boot[13]
    root_cluster = int.from_bytes(boot[44:48], 'little')

    fat_start = partition_start + reserved
    data_start = partition_start + reserved + (fats * spf)

    # ROOT
    root_data = read_directory(root_cluster, data_start, spc, fat_start, is_sdhc)
    files = list_files(root_data)

    # # ENTER EMBEDDED (cluster 5)
    # embedded_data = read_directory(5, data_start, spc, fat_start, is_sdhc)
    # embedded_files = list_files(embedded_data)

    # # READ FIRST FILE (example)
    # if embedded_files:
    #     name, ext, cluster, size = embedded_files[0]

    #     print(f"\nReading file: {name}.{ext}")

    #     file_data = read_file(cluster, data_start, spc, fat_start, is_sdhc, size)

    #     print("\n--- FILE CONTENT ---")
    #     print(bytes(file_data).decode('utf-8', errors='ignore'))
    # -------------Start CLI---------------------
    cli_explorer(root_cluster, data_start, spc, fat_start, is_sdhc)