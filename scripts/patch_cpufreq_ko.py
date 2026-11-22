#!/usr/bin/env python3
"""Patch mediatek-cpufreq-hw.ko to raise the first MT6789 CPU LUT entry.

The stock driver builds cpufreq's table from a hardware LUT:
  - LUT base  = reg window + 0x0000, 32 x u32, 4-byte stride
  - bits[11:0] of each u32 = frequency in MHz
  - driver multiplies by 1000 to get kHz
  - index register = reg window + 0x88

This script rewrites mtk_cpu_create_freq_table() in place so that, before the
table is read, entry 0 is updated in hardware:
  A76 (LUT[0] == 2200 MHz) -> 2500 MHz
  A55 (LUT[0] == 2000 MHz) -> 2400 MHz

Upper 20 bits of the register are preserved with read-modify-write.

The patched function keeps the original prologue (including the single
devm_kmalloc relocation at offset 0xd1c) and original epilogue, so no ELF
relocation table changes are required.
"""

import argparse
import struct
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN

FUNC_OFF = 0xCF4          # function virtual/relative address
FUNC_SIZE = 304
PREFIX_END = 0xD28        # bytes before this are kept verbatim
EPILOGUE = 0xE0C          # success path jumps here
REGION_END = 0xE08        # end of writable custom region (error path starts here)

BIG_FROM, BIG_TO = 0x898, 0x9C4      # 2200 -> 2500 MHz
LITTLE_FROM, LITTLE_TO = 0x7D0, 0x960  # 2000 -> 2400 MHz


def assemble(base, lines):
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    try:
        enc, _ = ks.asm("\n".join(lines), base)
    except Exception as exc:
        raise SystemExit(f"keystone assemble failed at {base:#x}: {exc}")
    return bytes(enc)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--big-to", type=lambda x: int(x, 0), default=BIG_TO)
    ap.add_argument("--little-to", type=lambda x: int(x, 0), default=LITTLE_TO)
    ap.add_argument("--big-only", action="store_true",
                    help="leave A55 untouched")
    args = ap.parse_args()

    blob = bytearray(open(args.src, "rb").read())
    start_file = 0x1000 + FUNC_OFF          # .text is at file offset 0x1000
    prefix = bytes(blob[start_file:start_file + (PREFIX_END - FUNC_OFF)])
    assert len(prefix) == PREFIX_END - FUNC_OFF

    lines = [
        # x19 = data, x8 = LUT base, x9 = freq table, w10 = byte offset
        "ldr x8, [x19, #8]",
        "ldr x9, [x19]",
        "mov w10, #8",
        "mov w11, #0",                       # previous kHz
        "mov x12, #0",                       # entry count
        "mov x17, #0",                       # LUT index
        "mov w16, #1000",
        "loop:",
        "ldr w13, [x8]",                     # raw LUT word
        "and w14, w13, #0xfff",              # MHz field
        "cbnz x17, skip_patch",
    ]
    if not args.big_only:
        lines += [
            "mov w15, #0x7d0",                # A55: 2000 MHz
            "cmp w14, w15",
            "b.ne chk_big",
            "bic w13, w13, #0xfff",
            "mov w15, #0x%x" % args.little_to,
            "orr w13, w13, w15",
            "str w13, [x8]",
            "mov w14, #0x%x" % args.little_to,
            "b skip_patch",
            "chk_big:",
        ]
    lines += [
        "mov w15, #0x898",                   # A76: 2200 MHz
        "cmp w14, w15",
        "b.ne skip_patch",
        "bic w13, w13, #0xfff",
        "mov w15, #0x%x" % args.big_to,
        "orr w13, w13, w15",
        "str w13, [x8]",
        "mov w14, #0x%x" % args.big_to,
        "skip_patch:",
        "mul w13, w14, w16",                 # kHz
        "cmp w13, w11",
        "b.eq done",
        "str w13, [x9, x10]",
        "add x10, x10, #0xc",
        "mov w11, w13",
        "add x8, x8, #4",
        "add x12, x12, #1",
        "add x17, x17, #1",  # LUT index: patch only applies to entry 0
        "cmp x12, #0x20",
        "b.ne loop",
        "done:",
        "ldr x8, [x19]",
        "mov w10, #0xc",
        "mov w11, #0xfffffffe",              # -2 terminator
        "mul x8, x12, x10",
        "ldr x10, [x19]",
        "add x8, x8, x10",
        "str w11, [x8, #8]",
        "str w12, [x19, #0x38]",
        "mov w0, #0",
    ]

    code = assemble(PREFIX_END, lines)

    # Success path must jump over the original -ENOMEM branch at 0xe08.
    branch_addr = PREFIX_END + len(code)
    imm = (EPILOGUE - branch_addr) // 4
    if not 0 <= imm < (1 << 26):
        raise SystemExit("branch out of range")
    branch = struct.pack("<I", 0x14000000 | imm)

    total = len(code) + len(branch)
    capacity = REGION_END - PREFIX_END
    if total > capacity:
        raise SystemExit(f"patched code too large: {total} > {capacity} bytes")
    nops = b"\x1f\x20\x03\xd5" * ((capacity - total) // 4)

    patched = prefix + code + branch + nops
    blob[start_file:start_file + (REGION_END - FUNC_OFF)] = patched[:REGION_END - FUNC_OFF]

    # The stock function has R_AARCH64_CALL26 relocations at 0xd94
    # (__log_read_mmio) and 0xdcc (__log_post_read_mmio). Our replacement code
    # reuses those offsets for non-branch instructions, so the module loader
    # must be told to ignore them. Set them to R_AARCH64_NONE (type 0).
    e_shoff = struct.unpack_from("<Q", blob, 0x28)[0]
    e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", blob, 0x3A)
    secs = []
    for i in range(e_shnum):
        v = struct.unpack_from("<IIQQQQIIQQ", blob, e_shoff + i * e_shentsize)
        secs.append({"name": v[0], "type": v[1], "off": v[4], "size": v[5]})
    stro = secs[e_shstrndx]["off"]
    strd = bytes(blob[stro:stro + secs[e_shstrndx]["size"]])
    cleared = []
    for sec in secs:
        nm = strd[sec["name"]:strd.find(b"\0", sec["name"])].decode("ascii", "replace")
        if sec["type"] != 4 or "rela.text" not in nm:
            continue
        for o in range(sec["off"], sec["off"] + sec["size"], 24):
            ro = struct.unpack_from("<Q", blob, o)[0]
            if ro in (0xD94, 0xDCC):
                struct.pack_into("<QQq", blob, o, ro, 0, 0)
                cleared.append((nm, hex(ro)))
    if len(cleared) != 2:
        raise SystemExit(f"expected 2 relocations to clear, got {cleared}")

    open(args.dst, "wb").write(blob)
    print(f"wrote {args.dst}")
    print(f"  custom code   : {len(code)} bytes at {PREFIX_END:#x}")
    print(f"  success branch: {branch.hex()} at {branch_addr:#x} -> {EPILOGUE:#x}")
    print(f"  spare nops    : {len(nops)} bytes")
    print(f"  A76 LUT[0]    : {BIG_FROM:#x} -> {args.big_to:#x} ({args.big_to} MHz)")
    if not args.big_only:
        print(f"  A55 LUT[0]    : {LITTLE_FROM:#x} -> {args.little_to:#x} ({args.little_to} MHz)")
    else:
        print("  A55 LUT[0]    : untouched")


if __name__ == "__main__":
    main()
