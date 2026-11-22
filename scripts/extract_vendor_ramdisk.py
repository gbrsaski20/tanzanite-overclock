#!/usr/bin/env python3
"""Decompress the legacy-LZ4 vendor ramdisk from a vendor_boot.img.

Redmi Note 14 4G (tanzanite) uses 8 MiB uncompressed LZ4 blocks.
"""

import argparse
import struct

import lz4.block

LZ4_MAGIC = 0x184C2102
RAMDISK_OFFSET = 4096
BLOCK = 8 * 1024 * 1024
MODULE_NAME = "lib/modules/mediatek-cpufreq-hw.ko"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("vendor_boot")
    ap.add_argument("cpio_out")
    ap.add_argument("--module-out", default=None,
                    help="also extract " + MODULE_NAME)
    args = ap.parse_args()

    raw = open(args.vendor_boot, "rb").read()
    if struct.unpack_from("<I", raw, RAMDISK_OFFSET)[0] != LZ4_MAGIC:
        raise SystemExit("vendor ramdisk is not legacy LZ4")

    pos = RAMDISK_OFFSET + 4
    out = bytearray()
    blocks = 0
    while True:
        size = struct.unpack_from("<I", raw, pos)[0]
        pos += 4
        if size == 0:
            break
        direct = bool(size & 0x80000000)
        size &= 0x7FFFFFFF
        chunk = raw[pos:pos + size]
        pos += size
        out += chunk if direct else lz4.block.decompress(
            chunk, uncompressed_size=BLOCK)
        blocks += 1

    open(args.cpio_out, "wb").write(out)
    print(f"wrote {args.cpio_out}: {len(out)} bytes from {blocks} blocks")

    if args.module_out:
        p = 0
        found = False
        while p + 110 <= len(out):
            if out[p:p + 6] != b"070701":
                break
            f = [int(out[p + 6 + i * 8:p + 14 + i * 8], 16) for i in range(13)]
            size, namesize = f[6], f[11]
            name = out[p + 110:p + 110 + namesize - 1].decode(
                "utf-8", "replace")
            data = (p + 110 + namesize + 3) & ~3
            if name == MODULE_NAME:
                open(args.module_out, "wb").write(out[data:data + size])
                print(f"wrote {args.module_out}: {size} bytes")
                found = True
                break
            p = (data + size + 3) & ~3
        if not found:
            raise SystemExit("module not found in cpio")


if __name__ == "__main__":
    main()
