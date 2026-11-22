#!/usr/bin/env python3
"""Stub MIA session ops in libmicampostproc_client.so (flourite donor).

Xiaomi's MIA HIDL service is absent on tanzanite, so every session operation
dereferences a null internal pointer.  Replace the prologues with
`mov w0, #0; ret` so MiuiCamera sees "success" but no incompatible engine call
is made.  Exports and ELF size stay unchanged.
"""
import argparse
import struct

STUBS = {
    0x1533c: 'MiPostProcSessionIntf::initialize',
    0x17f2c: 'MiPostProcSessionIntf::preProcessFrame',
    0x16f64: 'MiPostProcSessionIntf::processFrame',
    0x182d8: 'MiPostProcSessionIntf::processFrameWithSync',
    0x1874c: 'MiPostProcSessionIntf::quickFinish',
    0x18584: 'MiPostProcSessionIntf::flush',
    0x18368: 'MiPostProcSessionIntf::destory',
    0x16448: 'MiPostProcSessionIntf::bypassProcess',
    0x134c0: 'MiPostProcServiceIntf::processFrame',
    0x13630: 'MiPostProcServiceIntf::preProcessFrame',
    0x136e4: 'MiPostProcServiceIntf::processFrameWithSync',
    0x13574: 'MiPostProcServiceIntf::quickFinish',
    0x13988: 'MiPostProcServiceIntf::flush',
    0x136f4: 'MiPostProcServiceIntf::destroySession',
}
STUB = struct.pack('<II', 0x52800000, 0xd65f03c0)  # mov w0,#0 ; ret


def patch(data: bytes) -> bytes:
    out = bytearray(data)
    for addr, name in STUBS.items():
        if out[addr:addr + 8] == STUB:
            continue
        out[addr:addr + 8] = STUB
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src', help='original libmicampostproc_client.so')
    ap.add_argument('dst', help='output patched library')
    a = ap.parse_args()
    data = open(a.src, 'rb').read()
    open(a.dst, 'wb').write(patch(data))
    print(f'patched {len(STUBS)} functions -> {a.dst}')


if __name__ == '__main__':
    main()
