@echo off
setlocal
cd /d "%~dp0"

echo ================================================
echo  ROLLBACK - kembalikan image stock tanzanite
echo ================================================
echo.
echo  Pastikan HP sudah masuk FASTBOOT:
echo  matikan, lalu tahan Volume Down + Power.
echo.
echo  Catatan: partition dtb TIDAK ADA di device ini.
echo  DTB ada di dalam vendor_boot, jadi cukup flash
echo  vendor_boot + vbmeta (dua slot).
echo.
pause

echo [1/4] vendor_boot stock (slot a) ...
fastboot flash vendor_boot_a "stock-images\vendor_boot.img"
if errorlevel 1 goto gagal

echo [2/4] vendor_boot stock (slot b) ...
fastboot flash vendor_boot_b "stock-images\vendor_boot.img"
if errorlevel 1 goto gagal

echo [3/4] vbmeta stock (slot a) ...
fastboot flash vbmeta_a "stock-images\vbmeta.img"
if errorlevel 1 goto gagal

echo [4/4] vbmeta stock (slot b) ...
fastboot flash vbmeta_b "stock-images\vbmeta.img"
if errorlevel 1 goto gagal

echo.
echo Selesai. Reboot ...
fastboot reboot
goto selesai

:gagal
echo.
echo GAGAL. Cek kabel, driver, dan pastikan di mode FASTBOOT.

:selesai
echo.
pause
