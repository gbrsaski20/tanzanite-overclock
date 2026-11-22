#!/usr/bin/env python3
"""Wrap a raw FDT blob in the Android dt_table header used by this device."""

import argparse
import struct

DT_MAGIC = 0xD7B7AB1E
HEADER_SIZE = 32
ENTRY_SIZE = 32
BLOB_OFFSET = 64


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fdt_in")
    ap.add_argument("img_out")
    args = ap.parse_args()

    blob = open(args.fdt_in, "rb").read()
    total = BLOB_OFFSET + len(blob)

    hdr = bytearray(BLOB_OFFSET)
    struct.pack_into(">IIIIIIII", hdr, 0,
                     DT_MAGIC, total, HEADER_SIZE, ENTRY_SIZE,
                     1, HEADER_SIZE, 0x800, 0)
    # dt entry: size, offset, id, rev
    struct.pack_into(">IIII", hdr, HEADER_SIZE,
                     len(blob), BLOB_OFFSET, 0, 0)

    with open(args.img_out, "wb") as f:
        f.write(hdr)
        f.write(blob)
    print(f"wrote {args.img_out}: header {BLOB_OFFSET} + blob {len(blob)} "
          f"= {total} bytes")


if __name__ == "__main__":
    main()
