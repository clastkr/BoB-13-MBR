import struct
import sys

SECTOR_SIZE = 512
PARTITION_OFFSET = 446
PARTITION_STRUCT = "<1s3s1s3sII"
EBR_STRUCT = "<446s16s16s16s16s2s"

PARTITION_TYPES = {
    "NTFS": b'\x07',
    "Extended": b'\x05',
    "FAT32": [b'\x0B', b'\x0C']
}

def unpack_partition_entry(entry):
    unpacked_entry = struct.unpack(PARTITION_STRUCT, entry)
    partition_type = unpacked_entry[2]
    start_lba = unpacked_entry[4]
    sector_count = unpacked_entry[5]

    return partition_type, start_lba, sector_count

def identify_filesystem(partition_type):
    if partition_type in PARTITION_TYPES["FAT32"]:
        return "FAT32"
    elif partition_type == PARTITION_TYPES["NTFS"]:
        return "NTFS"
    return None

def read_mbr(file_path):
    with open(file_path, 'rb') as f:
        mbr = f.read(SECTOR_SIZE)
        partitions = []

        for i in range(4):
            entry = mbr[PARTITION_OFFSET + i * 16 : PARTITION_OFFSET + (i + 1) * 16]
            partition_type, start_lba, sector_count = unpack_partition_entry(entry)

            fs_type = identify_filesystem(partition_type)

            if fs_type:
                partitions.append((fs_type, start_lba, sector_count))
            elif partition_type == PARTITION_TYPES["Extended"]:
                logical_partitions = parse_ebr(file_path, start_lba)
                partitions.extend(logical_partitions)

        return partitions

def parse_ebr(file_path, start_lba):
    logical_partitions = []
    base_lba = start_lba

    with open(file_path, 'rb') as f:
        f.seek(start_lba * SECTOR_SIZE)
        while True:
            ebr = f.read(SECTOR_SIZE)
            if not ebr or len(ebr) < SECTOR_SIZE:
                break

            ebr_entries = struct.unpack(EBR_STRUCT, ebr)
            first_entry = ebr_entries[1]
            next_entry = ebr_entries[2]

            partition_type, rel_start_lba, sector_count = unpack_partition_entry(first_entry)

            fs_type = identify_filesystem(partition_type)
            if fs_type:
                absolute_start_lba = start_lba + rel_start_lba
                logical_partitions.append((fs_type, absolute_start_lba, sector_count))

            next_ebr_rel_start_lba = unpack_partition_entry(next_entry)[1]
            if next_ebr_rel_start_lba == 0:
                break

            start_lba = base_lba + next_ebr_rel_start_lba
            f.seek(start_lba * SECTOR_SIZE)

    return logical_partitions

def main():
    
    disk_image = sys.argv[1]
    partitions = read_mbr(disk_image)

    for fs_type, start_lba, sector_count in partitions:
        print(f"{fs_type} {start_lba} {sector_count}")

if __name__ == "__main__":
    main()