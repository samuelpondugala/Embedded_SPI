from tester import SDTester

def main():
    mount_point = "/home/team2/sd_test"   # Change this path

    tester = SDTester(
        mount_point=mount_point,
        file_size_mb=20,
        block_size=4096
    )

    print("===== SD CARD BASIC TEST =====")

    write_speed = tester.write_test()
    read_speed = tester.read_test()
    integrity = tester.integrity_test()

    print("\n===== SUMMARY =====")
    print(f"Write Speed : {write_speed:.2f} MB/s")
    print(f"Read Speed  : {read_speed:.2f} MB/s")
    print(f"Integrity   : {'PASS' if integrity else 'FAIL'}")

    tester.cleanup()

if __name__ == "__main__":
    main()
