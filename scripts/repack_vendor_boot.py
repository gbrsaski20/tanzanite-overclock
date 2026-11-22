#!/usr/bin/env python3
"""Rebuild a Redmi Note 14 4G vendor_boot.img with a swapped kernel module.

Layout of the stock 64 MiB image:
  0x0000        header (4096 bytes), ramdisk size at 0x18, dtb size at 0x834
  0x1000        legacy LZ4 block stream (magic 0x184c2102)
  0x01e7e800    dt_table-wrapped DTB (178665 bytes, from dtb.img)
  rest          zero padding
"""

import argparse
import struct

import lz4.block

LZ4_MAGIC = 0x184C2102
DTB_OFFSET = 31_981_568  # 0x1E7FA00, dt_table start; FDT magic at +64
IMAGE_SIZE = 67_108_864
HEADER_SIZE = 4096
RAMDISK_SIZE_FIELD = 0x18
DTB_SIZE_FIELD = 0x834
BLOCK = 8 * 1024 * 1024  # Android legacy LZ4 vendor ramdisk block size


def parse_newc(cpio):
    """Return list of (name, data_start, size) for newc entries."""
    out = []
    p = 0
    while p + 110 <= len(cpio):
        if cpio[p:p + 6] not in (b"070701", b"070702"):
            raise ValueError(f"bad cpio magic at {p:#x}")
        fields = [int(cpio[p + 6 + i * 8:p + 14 + i * 8], 16) for i in range(13)]
        size, namesize = fields[6], fields[11]
        name_start = p + 110
        name = cpio[name_start:name_start + namesize - 1].decode("utf-8", "replace")
        data = (name_start + namesize + 3) & ~3
        if name == "TRAILER!!!":
            break
        out.append((name, data, size))
        p = (data + size + 3) & ~3
    return out


def lz4_decompress_stream(raw):
    if struct.unpack_from("<I", raw, 0)[0] != LZ4_MAGIC:
        raise ValueError("not a legacy LZ4 stream")
    p = 4
    out = bytearray()
    while True:
        size = struct.unpack_from("<I", raw, p)[0]
        p += 4
        if size == 0:
            break
        uncompressed = bool(size & 0x80000000)
        size &= 0x7FFFFFFF
        chunk = raw[p:p + size]
        p += size
        if uncompressed:
            out += chunk
        else:
            out += lz4.block.decompress(chunk, uncompressed_size=BLOCK)
    return bytes(out), p


def lz4_compress_stream(data):
    out = bytearray(struct.pack("<I", LZ4_MAGIC))
    for off in range(0, len(data), BLOCK):
        chunk = data[off:off + BLOCK]
        packed = lz4.block.compress(chunk, mode="high_compression",
                                    compression=12, store_size=False)
        if len(packed) < len(chunk):
            out += struct.pack("<I", len(packed)) + packed
        else:
            out += struct.pack("<I", 0x80000000 | len(chunk)) + chunk
    out += struct.pack("<I", 0)
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="stock-images/vendor_boot.img")
    ap.add_argument("--cpio", default="vendor_ramdisk.cpio")
    ap.add_argument("--module", default="extracted/modules/mediatek-cpufreq-hw-oc.ko")
    ap.add_argument("--module-name", default="lib/modules/mediatek-cpufreq-hw.ko")
    ap.add_argument("--dtb", default=None,
                    help="optional replacement dtb.img (GPU OC)")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    image = open(args.base, "rb").read()
    if len(image) != IMAGE_SIZE:
        raise SystemExit(f"unexpected base size {len(image)}")
    header = bytearray(image[:HEADER_SIZE])
    entries = parse_newc(open(args.cpio, "rb").read())
    mod = open(args.module, "rb").read()
    cpio = bytearray(open(args.cpio, "rb").read())

    matches = [e for e in entries if e[0] == args.module_name]
    if len(matches) != 1:
        raise SystemExit(f"expected one {args.module_name}, got {len(matches)}")
    _, data_off, old_size = matches[0]
    if old_size != len(mod):
        raise SystemExit(f"module size mismatch: cpio={old_size} new={len(mod)}")
    cpio[data_off:data_off + len(mod)] = mod

    stream = lz4_compress_stream(bytes(cpio))
    struct.pack_into("<I", header, RAMDISK_SIZE_FIELD, len(stream) - 4)

    dtb = open(args.dtb, "rb").read() if args.dtb else image[DTB_OFFSET:DTB_OFFSET + 178665]
    if HEADER_SIZE + len(stream) > DTB_OFFSET:
        raise SystemExit("compressed ramdisk does not fit before DTB")
    if DTB_OFFSET + len(dtb) > IMAGE_SIZE:
        raise SystemExit("DTB does not fit in image")

    out = bytearray(IMAGE_SIZE)
    out[:HEADER_SIZE] = header
    out[HEADER_SIZE:HEADER_SIZE + len(stream)] = stream
    out[DTB_OFFSET:DTB_OFFSET + len(dtb)] = dtb

    open(args.output, "wb").write(out)
    print(f"wrote {args.output}")
    print(f"  module      : {args.module_name} ({len(mod)} bytes)")
    print(f"  cpio        : {len(cpio)} bytes")
    print(f"  lz4 stream  : {len(stream)} bytes "
          f"(header field {len(stream) - 4})")
    print(f"  dtb         : {len(dtb)} bytes at {DTB_OFFSET:#x}")
    print(f"  end of ramdisk: {HEADER_SIZE + len(stream):#x} "
          f"(limit {DTB_OFFSET:#x})")


if __name__ == "__main__":
    main()
