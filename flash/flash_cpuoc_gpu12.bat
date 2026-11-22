@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  FLASH: CPU 2.5/2.4 GHz + GPU 1.2 GHz
echo ================================================
echo.
echo  Pastikan di FASTBOOT. Partition dtb tidak ada;
echo  DTB sudah ikut di dalam vendor_boot.
echo  vbmeta tidak disentuh (ROM sudah lolos verifikasi).
echo.
pause

echo [1/2] vendor_boot OC (slot a) ...
fastboot flash vendor_boot_a "vendor_boot_cpuoc_gpu12.img"
if errorlevel 1 goto gagal

echo [2/2] vendor_boot OC (slot b) ...
fastboot flash vendor_boot_b "vendor_boot_cpuoc_gpu12.img"
if errorlevel 1 goto gagal

echo.
echo Selesai. Reboot ...
fastboot reboot
goto selesai

:gagal
echo.
echo GAGAL. Cek kabel, driver, dan mode FASTBOOT.

:selesai
echo.
pause
