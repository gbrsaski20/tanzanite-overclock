@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  EKSPERIMEN: CPU A76 3.0 GHz / A55 2.4 GHz
echo              GPU 1.25 GHz @ 900 mV
echo ================================================
echo.
echo  Ini agresif. Siapkan flash_cpuoc_gpu12.bat untuk balik.
echo  Pastikan di FASTBOOT. vbmeta tidak disentuh.
echo.
pause

echo [1/2] vendor_boot 3GHz (slot a) ...
fastboot flash vendor_boot_a "vendor_boot_cpu3_gpu125.img"
if errorlevel 1 goto gagal

echo [2/2] vendor_boot 3GHz (slot b) ...
fastboot flash vendor_boot_b "vendor_boot_cpu3_gpu125.img"
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
