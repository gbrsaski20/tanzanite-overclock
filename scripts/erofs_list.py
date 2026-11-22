#!/usr/bin/env python3
"""Minimal EROFS reader: list directory entries (compact inodes, flat inline/plain)."""
import argparse
import struct

MAGIC = 0xE0F5E1E2
SUPER_OFF = 1024


class Erofs:
    def __init__(self, path):
        self.d = open(path, "rb").read()
        s = self.d[SUPER_OFF:SUPER_OFF + 128]
        magic = struct.unpack_from("<I", s, 0)[0]
        if magic != MAGIC:
            raise ValueError(f"not EROFS: magic 0x{magic:x}")
        self.blkbits = s[12]
        self.bs = 1 << self.blkbits
        self.root_nid = struct.unpack_from("<H", s, 14)[0]
        self.inos = struct.unpack_from("<Q", s, 16)[0]
        self.blocks = struct.unpack_from("<I", s, 36)[0]
        self.meta_blkaddr = struct.unpack_from("<I", s, 40)[0]

    def inode(self, nid):
        off = self.meta_blkaddr * self.bs + nid * 32
        if off + 32 > len(self.d):
            raise ValueError(f"nid {nid} out of range")
        fmt, xa, mode, nlink, size, res, u, ino, uid, gid, res2 = struct.unpack_from(
            "<HHHHIIIHHHI", self.d, off)
        xasize = 12 + (xa - 1) * 4 if xa else 0
        layout = (fmt >> 1) & 7
        if layout == 2:
            data = off + 32 + xasize
        elif layout == 0:
            data = u * self.bs
        else:
            data = None
        return dict(nid=nid, off=off, fmt=fmt, layout=layout, mode=mode,
                    size=size, startblk=u, data=data, xa=xasize)

    def dirents(self, inode):
        base = inode["data"]
        if base is None or base + inode["size"] > len(self.d):
            return []
        out = []
        pos = base
        limit = base + inode["size"]
        while pos + 12 <= limit:
            nid, nameoff, ft, res = struct.unpack_from("<QHBB", self.d, pos)
            if nid == 0 and nameoff == 0:
                break
            if nameoff >= inode["size"] or nid * 32 >= len(self.d):
                break
            out.append((nid, nameoff, ft))
            pos += 12
        names = []
        for i, (nid, nameoff, ft) in enumerate(out):
            end = out[i + 1][1] if i + 1 < len(out) else inode["size"]
            name = self.d[base + nameoff:base + end].split(b"\0")[0]
            names.append((name.decode("utf-8", "replace"), nid, ft))
        return names

    def walk(self, nid=None, path=""):
        if nid is None:
            nid = self.root_nid
        inode = self.inode(nid)
        if (inode["mode"] & 0o170000) == 0o040000:
            for name, child, ft in self.dirents(inode):
                if name in (".", ".."):
                    continue
                yield from self.walk(child, path + "/" + name)
        else:
            yield path, inode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--match", default="")
    ap.add_argument("--dir", default="")
    args = ap.parse_args()
    fs = Erofs(args.image)
    print(f"# {args.image}: blksz={fs.bs} root={fs.root_nid} inos={fs.inos} blocks={fs.blocks}")
    for path, inode in fs.walk():
        if args.dir and not path.startswith(args.dir):
            continue
        if args.match and args.match.lower() not in path.lower():
            continue
        print(f"{path}\tnid={inode['nid']}\tlayout={inode['layout']}\tsize={inode['size']}\tstartblk={inode['startblk']}")


if __name__ == "__main__":
    main()
