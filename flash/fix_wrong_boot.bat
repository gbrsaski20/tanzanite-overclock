@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  PERBAIKAN: salah flash vendor_boot ke boot
echo ================================================
echo.
echo  Akan flash ulang:
echo    boot_a/b        -^> stock-images\boot.img
echo    vendor_boot_a/b -^> vendor_boot_cpuoc_gpu12.img
echo.
echo  vbmeta TIDAK disentuh (ROM kamu sudah lolos verifikasi).
echo  Pastikan di FASTBOOT. JANGAN wipe data.
echo.
pause

echo [1/4] boot stock (slot a) ...
fastboot flash boot_a "stock-images\boot.img"
if errorlevel 1 goto gagal

echo [2/4] boot stock (slot b) ...
fastboot flash boot_b "stock-images\boot.img"
if errorlevel 1 goto gagal

echo [3/4] vendor_boot OC (slot a) ...
fastboot flash vendor_boot_a "vendor_boot_cpuoc_gpu12.img"
if errorlevel 1 goto gagal

echo [4/4] vendor_boot OC (slot b) ...
fastboot flash vendor_boot_b "vendor_boot_cpuoc_gpu12.img"
if errorlevel 1 goto gagal

echo.
echo Selesai. Reboot langsung ke system (jangan masuk recovery) ...
fastboot reboot
goto selesai

:gagal
echo.
echo GAGAL. Cek kabel, driver, dan mode FASTBOOT.

:selesai
echo.
pause
