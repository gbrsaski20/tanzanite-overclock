#!/usr/bin/env python3
"""Patch a raw FDT in place: raise the top GPU OPP frequency/voltage.

Targets /soc/opp-table0/opp00 on mt6789 (Helio G99) vendor DTB.
In-place 4-byte writes keep the FDT size and the Android dt_table header valid.
"""

import argparse
import struct

MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


def locate(raw):
    if struct.unpack_from(">I", raw, 0)[0] != MAGIC:
        raise ValueError("bad FDT magic")
    _, _, off_struct, off_strings, _, _, _, _, size_strings, size_struct = \
        struct.unpack_from(">10I", raw, 0)
    strings = raw[off_strings:off_strings + size_strings]

    def sname(o):
        return strings[o:strings.find(b"\0", o)].decode("utf-8")

    props = {}
    stack = []
    pos = off_struct
    limit = off_struct + size_struct
    while pos < limit:
        tag = struct.unpack_from(">I", raw, pos)[0]
        pos += 4
        if tag == BEGIN_NODE:
            end = raw.find(b"\0", pos)
            name = raw[pos:end].decode("utf-8", "replace")
            pos = (end + 4) & ~3
            stack.append(name or "/")
        elif tag == END_NODE:
            stack.pop()
        elif tag == PROP:
            length, nameoff = struct.unpack_from(">II", raw, pos)
            pos += 8
            data_off = pos
            path = "/" + "/".join(x for x in stack if x != "/")
            props[(path, sname(nameoff))] = (data_off, length)
            pos = (data_off + length + 3) & ~3
        elif tag == NOP:
            continue
        elif tag == END:
            break
        else:
            raise ValueError(f"bad tag 0x{tag:x} at {pos}")
    return props


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fdt_in")
    ap.add_argument("fdt_out")
    ap.add_argument("--hz", type=lambda x: int(x, 0), default=1_100_000_000)
    ap.add_argument("--uv", type=lambda x: int(x, 0), default=775_000)
    args = ap.parse_args()

    raw = bytearray(open(args.fdt_in, "rb").read())
    props = locate(raw)

    hz_key = ("/soc/opp-table0/opp00", "opp-hz")
    uv_key = ("/soc/opp-table0/opp00", "opp-microvolt")
    if hz_key not in props:
        raise SystemExit("opp-hz for /soc/opp-table0/opp00 not found")

    hz_off, hz_len = props[hz_key]
    if hz_len != 8:
        raise SystemExit(f"unexpected opp-hz length {hz_len}")
    old_hz = struct.unpack_from(">Q", raw, hz_off)[0]

    struct.pack_into(">Q", raw, hz_off, args.hz)

    old_uv = None
    if uv_key in props:
        uv_off, uv_len = props[uv_key]
        if uv_len == 4:
            old_uv = struct.unpack_from(">I", raw, uv_off)[0]
            struct.pack_into(">I", raw, uv_off, args.uv)

    open(args.fdt_out, "wb").write(raw)
    print(f"opp-hz    {old_hz} -> {args.hz} (0x{args.hz:x}) at FDT+{hz_off}")
    if old_uv is not None:
        print(f"opp-uV    {old_uv} -> {args.uv} (0x{args.uv:x}) at FDT+{uv_off}")
    print(f"wrote {args.fdt_out} ({len(raw)} bytes)")


if __name__ == "__main__":
    main()
