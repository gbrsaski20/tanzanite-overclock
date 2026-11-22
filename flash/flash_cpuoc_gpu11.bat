@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  FLASH: CPU 2.5/2.4 GHz + GPU 1.1 GHz
echo ================================================
echo.
echo  Pastikan di FASTBOOT. Partition dtb tidak ada;
echo  DTB sudah ikut di dalam vendor_boot.
echo.
pause

echo [1/4] vendor_boot OC (slot a) ...
fastboot flash vendor_boot_a "vendor_boot_cpuoc_gpu11.img"
if errorlevel 1 goto gagal

echo [2/4] vendor_boot OC (slot b) ...
fastboot flash vendor_boot_b "vendor_boot_cpuoc_gpu11.img"
if errorlevel 1 goto gagal

echo [3/4] vbmeta disabled (slot a) ...
fastboot flash vbmeta_a "vbmeta_disabled.img"
if errorlevel 1 goto gagal

echo [4/4] vbmeta disabled (slot b) ...
fastboot flash vbmeta_b "vbmeta_disabled.img"
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
