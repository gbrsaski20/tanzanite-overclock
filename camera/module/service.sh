#!/system/bin/sh
# Grant runtime permissions for MiuiCamera after boot so the user does not have
# to accept the same dialogs on every cold start.

MODDIR=${0%/*}
LOG=/data/local/tmp/miuicamera_grants.log
PKG=com.android.camera

# MiuiCamera requests MediaTek MFNR, whose OpenCL kernel build aborts
# camerahalserver in libanc_mfnr.so on tanzanite.  Put the ANC/YUVSIQ
# checker into "empty SDK" mode so the HAL skips that path.
RESETPROP=""
if command -v resetprop >/dev/null 2>&1; then
    RESETPROP=$(command -v resetprop)
elif [ -x /data/adb/magisk/resetprop ]; then
    RESETPROP=/data/adb/magisk/resetprop
elif [ -x /data/adb/ksu/bin/resetprop ]; then
    RESETPROP=/data/adb/ksu/bin/resetprop
elif [ -x /data/adb/ap/bin/resetprop ]; then
    RESETPROP=/data/adb/ap/bin/resetprop
fi
if [ -n "$RESETPROP" ]; then
    "$RESETPROP" debug.anc.yuvsiq.emptysdk 1
fi

# Wait for the framework to be ready.
i=0
while [ "$(getprop sys.boot_completed)" != "1" ] && [ $i -lt 90 ]; do
    sleep 2
    i=$((i + 1))
done

: > "$LOG"
echo "boot_completed after ${i} polls" >> "$LOG"

for p in \
    android.permission.CAMERA \
    android.permission.RECORD_AUDIO \
    android.permission.ACCESS_FINE_LOCATION \
    android.permission.ACCESS_COARSE_LOCATION \
    android.permission.READ_MEDIA_IMAGES \
    android.permission.READ_MEDIA_VIDEO \
    android.permission.READ_MEDIA_AUDIO \
    android.permission.POST_NOTIFICATIONS
do
    echo "grant $p: $(pm grant $PKG $p 2>&1)" >> "$LOG"
done

echo "appops: $(appops set $PKG MANAGE_EXTERNAL_STORAGE allow 2>&1)" >> "$LOG"
echo "done" >> "$LOG"
