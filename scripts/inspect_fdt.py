#!/usr/bin/env python3
"""Minimal Flattened Device Tree inspector for Android boot images.

Usage:
  python inspect_fdt.py <fdt.bin> [--grep PATTERN ...] [--dump PATH]

Reads a raw FDT blob (not the Android dt_table wrapper). To extract the blob
from a dtb.img/dtbo.img, skip the first 64 bytes of the dt_table image.
"""

import argparse
import re
import struct
import sys

FDT_MAGIC = 0xD00DFEED
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9


def parse(raw):
    if len(raw) < 40 or struct.unpack_from(">I", raw, 0)[0] != FDT_MAGIC:
        raise ValueError("not a raw FDT blob (bad magic)")
    (_, total, off_struct, off_strings, off_mem, version, _, _, size_strings,
     size_struct) = struct.unpack_from(">10I", raw, 0)
    strings = raw[off_strings:off_strings + size_strings]
    block = raw[off_struct:off_struct + size_struct]

    def sname(offset):
        end = strings.find(b"\0", offset)
        return strings[offset:end].decode("utf-8", "replace")

    nodes = {}
    stack = []
    pos = 0
    while pos < len(block):
        tag = struct.unpack_from(">I", block, pos)[0]
        pos += 4
        if tag == BEGIN_NODE:
            end = block.find(b"\0", pos)
            name = block[pos:end].decode("utf-8", "replace")
            pos = (end + 4) & ~3
            stack.append(name or "/")
            path = "/" + "/".join(x for x in stack if x != "/")
            nodes[path] = {}
        elif tag == END_NODE:
            stack.pop()
        elif tag == PROP:
            length, nameoff = struct.unpack_from(">II", block, pos)
            pos += 8
            data = block[pos:pos + length]
            pos = (pos + length + 3) & ~3
            if stack:
                path = "/" + "/".join(x for x in stack if x != "/")
                nodes.setdefault(path, {})[sname(nameoff)] = data
        elif tag == NOP:
            continue
        elif tag == END:
            break
        else:
            raise ValueError(f"bad FDT tag 0x{tag:x} at {pos}")
    return nodes, {"version": version, "total": total, "memory_reservations": off_mem}


def fmt(data):
    if len(data) == 0:
        return "<empty>"
    if len(data) >= 4 and len(data) % 4 == 0:
        vals = struct.unpack(">" + "I" * (len(data) // 4), data)
        preview = " ".join(f"0x{v:x}" for v in vals[:12])
        if len(vals) > 12:
            preview += f" ... (+{len(vals) - 12})"
        return preview
    return repr(data[:120])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fdt")
    ap.add_argument("--grep", action="append", default=[])
    ap.add_argument("--dump", default=None)
    args = ap.parse_args()

    raw = open(args.fdt, "rb").read()
    nodes, meta = parse(raw)
    print(f"# FDT: {args.fdt}  nodes={len(nodes)}  version={meta['version']}  total={meta['total']}")

    if args.dump:
        for path, props in sorted(nodes.items()):
            if args.dump in path:
                print(f"\n[{path}]")
                for name, data in sorted(props.items()):
                    print(f"  {name} = {fmt(data)}")
        return

    patterns = [re.compile(p, re.I) for p in args.grep] if args.grep else [
        re.compile(p, re.I) for p in
        ("opp", "freq", "cpu", "mali", "gpu", "thermal", "hvfs", "dvfs", "volt")
    ]
    for path, props in sorted(nodes.items()):
        hit_path = any(p.search(path) for p in patterns)
        hit_props = {k: v for k, v in props.items() if any(p.search(k) for p in patterns)}
        if hit_path or hit_props:
            print(f"\n[{path}]")
            for name, data in sorted(hit_props.items()):
                print(f"  {name} = {fmt(data)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)
