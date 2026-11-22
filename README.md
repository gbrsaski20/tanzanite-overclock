# tanzanite-overclock

Reverse engineering dan tooling overclock untuk **Redmi Note 14 4G** (codename `tanzanite`, MT6789 / Helio G99).

## Ringkasan

| Item | Stock | OC |
|---|---|---|
| CPU A76 (`cpu7`) | 2.2 GHz | 2.5 GHz (eksperimen: 2.6 / 3.0 GHz) |
| CPU A55 (`cpu0`) | 2.0 GHz | 2.4 GHz |
| GPU Mali | 1.003 GHz | 1.1 / 1.2 / 1.25 GHz |

Kernel: GKI 5.10 (Halcyon Calla, Android 17).

## Temuan utama

- `dtbo.img` **tidak** berisi node CPU/GPU/OPP — tidak perlu diubah.
- GPU OPP ada di vendor DTB: `/soc/opp-table0/opp00`.
- CPU **tidak** punya OPP node di DTB. Tabel frekuensi dibaca dari **hardware LUT** MMIO oleh `mediatek-cpufreq-hw.ko`.
- Device ini **tidak punya partition `dtb`**. DTB hanya ada di dalam `vendor_boot.img`.

### Format CPU LUT

`mtk_cpu_create_freq_table()`:

```
entry size   = 12 bytes, 33 entries
LUT base     = reg window + 0x0000
LUT stride   = 4 bytes, 32 slots
frequency    = (u32 & 0xfff) * 1000   // kHz
index reg    = reg window + 0x88
```

Register window dari DTB:

| Cluster | CPUs | Base | LUT[0] stock |
|---|---|---|---|
| A55 | 0-5 | `0x11bc10` | 2000 MHz (`0x7d0`) |
| A76 | 6-7 | `0x11bd30` | 2200 MHz (`0x898`) |

Patch melakukan read-modify-write pada `LUT[0]`: hanya 12 bit bawah yang diubah, 20 bit atas dipertahankan.

### Layout vendor_boot.img

```
0x0000            header 4096 byte, ramdisk size @0x18, dtb size @0x834
0x1000            legacy LZ4 stream, blok 8 MiB, magic 0x184c2102
0x1e80000         dt_table + FDT (178665 byte)
```

Kompresi harus **LZ4 HC level 12** supaya ukurannya sama dengan stock.

## Scripts

| File | Fungsi |
|---|---|
| `scripts/inspect_fdt.py` | parser FDT minimal, grep/dump node |
| `scripts/patch_gpu_opp.py` | ubah `/soc/opp-table0/opp00` di raw FDT |
| `scripts/wrap_dtb.py` | bungkus raw FDT jadi `dt_table` image |
| `scripts/extract_vendor_ramdisk.py` | decompress vendor ramdisk + ambil modul |
| `scripts/patch_cpufreq_ko.py` | patch LUT[0] di `mediatek-cpufreq-hw.ko` |
| `scripts/repack_vendor_boot.py` | rebuild `vendor_boot.img` dengan modul/DTB baru |
| `scripts/erofs_list.py` | parser EROFS minimal untuk eksplorasi vendor |

## Contoh alur

```sh
# 1. Ambil vendor_boot.img dari ROM/OTA kamu sendiri
python scripts/extract_vendor_ramdisk.py vendor_boot.img ramdisk.cpio \
    --module-out mediatek-cpufreq-hw.ko

# 2. Patch CPU (A76 2.5 GHz, A55 2.4 GHz)
python scripts/patch_cpufreq_ko.py mediatek-cpufreq-hw.ko patched.ko

# 3. Patch GPU 1.2 GHz / 850 mV, lalu bungkus DTB
python scripts/patch_gpu_opp.py dtb_blob.dtb dtb_patched.dtb \
    --hz 1200000000 --uv 850000
python scripts/wrap_dtb.py dtb_patched.dtb dtb_patched.img

# 4. Repack
python scripts/repack_vendor_boot.py \
    --module patched.ko --dtb dtb_patched.img --output vendor_boot_oc.img
```

## Prebuilt image

Image yang sudah divalidasi di perangkat tersedia di GitHub Releases:

- [`vendor_boot_cpuoc_gpu12.img`](https://github.com/gbrsaski20/tanzanite-overclock/releases/download/v1.0.0/vendor_boot_cpuoc_gpu12.img) — A76 2.5 GHz, A55 2.4 GHz, GPU 1.2 GHz
- SHA-256: `8c5aeedff6ae865e8126519ceb1e1e568f1a864ac0db9959a759f0896886b565`

Binary ini berisi modul vendor dari ROM Halcyon. Pakai hanya jika kamu memang memiliki hak atas firmware tersebut.

## MiuiCamera port (v1.4)

MiuiCamera HyperOS dari LineageOS `flourite` (Qualcomm) bisa jalan di tanzanite, tapi butuh tiga penyesuaian:

| Masalah | Solusi |
|---|---|
| `libmicampostproc_client.so` null deref di session MIA | 14 fungsi `MiPostProcSessionIntf` / `MiPostProcServiceIntf` di-stub jadi `return 0` |
| JNI panggil `MIAProcessFrame` di engine vendor yang lebih tua | `processFrame` + `Jni_ProcessFrameWithSync_V10/V11` di-stub |
| `camerahalserver` abort di `libanc_mfnr.so` (OpenCL) | `resetprop debug.anc.yuvsiq.emptysdk 1` dari `service.sh` |

Hasilnya: **preview live**, foto tersimpan, tidak ada FC, modul bisa dipasang lewat Magisk maupun KernelSU.

### Build dari donor

Binary Xiaomi **tidak disertakan**. Ambil dari ROM yang kamu miliki, lalu letakkan di `camera/files/`:

```
MiuiCamera.apk
libcamera_algoup_jni.xiaomi.so
libcamera_mianode_jni.xiaomi.so
libmicampostproc_client.so
vendor.xiaomi.hardware.campostproc@1.0.so
```

```sh
cd camera
python build_module.py --files files --output ../miuicamera_tanzanite_v1.4_ksu_magisk.zip
```

Script `patch_postproc_client.py` dan `patch_algoup_jni.py` juga bisa dipakai sendiri:

```sh
python patch_postproc_client.py files/libmicampostproc_client.so patched_client.so
python patch_algoup_jni.py files/libcamera_algoup_jni.xiaomi.so patched_jni.so
```

Alamat patch spesifik untuk build `flourite` 2026-11-14. Jangan pakai donor versi lain tanpa memverifikasi offset.

### Pasang

Flash `miuicamera_tanzanite_v1.4_ksu_magisk.zip` lewat aplikasi Magisk atau KernelSU, lalu reboot. Modul akan otomatis memberi runtime permission dan menetapkan properti MFNR.

Prebuilt: [`miuicamera_tanzanite_v1.4_ksu_magisk.zip`](https://github.com/gbrsaski20/tanzanite-overclock/releases/download/v1.1.0-camera/miuicamera_tanzanite_v1.4_ksu_magisk.zip)

Keterbatasan: efek MIA (beauty, HDR fusion) dan MFNR dimatikan; foto adalah keluaran langsung HAL. Di device dengan KernelSU + `meta-overlayfs`, jangan pasang modul ini dua kali (bisa dobel overlay).

## Flash

Script di `flash/` sudah flash **dua slot sekaligus**.

```sh
fastboot flash vendor_boot_a vendor_boot_oc.img
fastboot flash vendor_boot_b vendor_boot_oc.img
fastboot reboot
```

**Jangan** `fastboot flash boot vendor_boot_oc.img` — itu merusak partisi `boot`.

`vbmeta` sengaja tidak disentuh oleh script. ROM yang sudah lolos verifikasi tidak memerlukan `vbmeta_disabled.img`.

## Verifikasi

```sh
adb shell cat /sys/devices/system/cpu/cpu7/cpufreq/scaling_available_frequencies
adb shell cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_available_frequencies
adb shell cat /sys/class/devfreq/13000000.mali/available_frequencies
```

## Disclaimer

- Binary firmware, ROM, dan device tree **tidak disertakan**. Ambil dari perangkat/OTA kamu sendiri sesuai hukum yang berlaku.
- Overclock bisa merusak perangkat, bikin bootloop, atau hangus garansi. Pakai risiko sendiri.
- `init_user0 failed` di recovery stock Halcyon biasanya-normal: recovery stock tidak bisa decrypt `/data` yang pakai FBE. Data tidak hilang selama system masih boot.

## Dependencies

```sh
pip install lz4 capstone keystone-engine
```

`avbtool.py` bisa diunduh dari AOSP `platform/external/avb` bila diperlukan.

## License

MIT — lihat [LICENSE](LICENSE). Tidak mencakup firmware vendor.
