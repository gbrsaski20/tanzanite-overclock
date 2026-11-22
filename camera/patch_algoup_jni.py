#!/usr/bin/env python3
"""Stub JNI frame-processing entry points that call MIAProcessFrame directly.

libcamera_algoup_jni.xiaomi.so dlopens /vendor/lib64/libmialgoengine.so and
calls MIAProcessFrame; tanzanite's engine is an older generation and crashes
inside MiaFrameWrapper.  Skip only the post-processing JNI calls.  The photo
bytes still come from the camera HAL, and the preview becomes live.
"""
import argparse
import struct

STUBS = {
    0xb340: 'Java_MiCamAlgoInterfaceJNI_processFrame',
    0xb4e0: 'Jni_ProcessFrameWithSync_V10',
    0xbb44: 'Jni_ProcessFrameWithSync_V11',
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
    ap.add_argument('src', help='original libcamera_algoup_jni.xiaomi.so')
    ap.add_argument('dst', help='output patched library')
    a = ap.parse_args()
    data = open(a.src, 'rb').read()
    open(a.dst, 'wb').write(patch(data))
    print(f'patched {len(STUBS)} functions -> {a.dst}')


if __name__ == '__main__':
    main()
