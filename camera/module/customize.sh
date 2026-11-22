#!/system/bin/sh

ui_print "- Memasang MiuiCamera (com.android.camera) untuk tanzanite"
ui_print "- Sumber: LineageOS 24.0 flourite (MiuiCamera.apk 198 MB)"
if [ -n "$KSU" ] || [ -d "/data/adb/ksu" ]; then
    ui_print "- Root: KernelSU (metamodule opsional, tidak wajib)"
elif [ -d "/data/adb/magisk" ]; then
    ui_print "- Root: Magisk"
else
    ui_print "- Root: Magisk/KernelSU compatible"
fi

set_perm_recursive "$MODPATH/system/priv-app/MiuiCamera" 0 0 0755 0644
set_perm_recursive "$MODPATH/system/lib64" 0 0 0755 0644
set_perm_recursive "$MODPATH/system/etc" 0 0 0755 0644

ui_print "- Reboot untuk mengaktifkan module."
