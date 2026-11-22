#!/bin/bash
set -e
R=$(cd "$(dirname "$0")/.." && pwd)
cd "$R"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt
chmod +x deploy/update.sh deploy/install.sh

for u in dragonfist.service dragonfist-splash.service dragonfist-update.service dragonfist-update.timer; do
  systemctl --user link "$R/deploy/$u"
done
systemctl --user daemon-reload
systemctl --user enable dragonfist.service dragonfist-splash.service dragonfist-update.timer
systemctl --user start dragonfist-update.timer
sudo loginctl enable-linger "$USER"

C=/etc/gdm3/custom.conf
sudo sed -i '/^AutomaticLogin/d' $C
sudo sed -i "/^\[daemon\]/a AutomaticLoginEnable=true\nAutomaticLogin=$USER" $C

gsettings set org.gnome.desktop.screensaver lock-enabled false
gsettings set org.gnome.desktop.screensaver idle-activation-enabled false
gsettings set org.gnome.desktop.session idle-delay 0
gsettings set org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type nothing
gsettings set org.gnome.desktop.notifications show-banners false
gsettings set org.gnome.desktop.background picture-options none
gsettings set org.gnome.desktop.background primary-color '#000000'
gsettings set org.gnome.desktop.background color-shading-type solid
gsettings set org.gnome.shell.extensions.ding show-home false 2>/dev/null || true
gsettings set org.gnome.shell.extensions.ding show-trash false 2>/dev/null || true
gsettings set org.gnome.shell.extensions.dash-to-dock dock-fixed false 2>/dev/null || true
gsettings set org.gnome.shell.extensions.dash-to-dock autohide true 2>/dev/null || true
gsettings set org.gnome.shell.extensions.dash-to-dock intellihide false 2>/dev/null || true
echo "ok – restart to test: sudo reboot"
