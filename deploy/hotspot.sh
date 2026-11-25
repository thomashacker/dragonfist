#!/bin/bash
# Handy-Hotspot als Ersatz-WLAN speichern: verbindet von selbst, wenn das Haupt-WLAN fehlt; in der App unter EINSTELLUNGEN > WLAN wählbar
set -e
read -rp "Hotspot-Name (SSID): " SSID
read -rsp "Hotspot-Passwort: " PSK
echo
if nmcli -t -f NAME con show | grep -qxF "$SSID"; then
    sudo nmcli con modify "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK"
else
    sudo nmcli con add type wifi con-name "$SSID" ssid "$SSID" wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$PSK" \
        connection.autoconnect yes connection.autoconnect-priority -10 >/dev/null
fi
echo "Gespeichert: $SSID"
nmcli -t -f NAME,AUTOCONNECT-PRIORITY con show | grep -F "$SSID"
