#!/bin/bash
set -e
R=$(cd "$(dirname "$0")/.." && pwd)
cd "$R"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -U pip
.venv/bin/pip install -q -r requirements.txt -r requirements-dev.txt
chmod +x deploy/update.sh deploy/install.sh

for u in dragonfist.service dragonfist-update.service dragonfist-update.timer; do
  systemctl --user link "$R/deploy/$u"
done
systemctl --user daemon-reload
systemctl --user enable dragonfist.service dragonfist-update.timer
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
echo "ok – restart to test: sudo reboot"
