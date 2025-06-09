#!/bin/bash

echo "Downloading latest release..."
wget -qO - https://github.com/blaaaaaaah/dbus-anchor-alarm/archive/latest.tar.gz | tar -xzf - -C /data
mv -f /data/dbus-anchor-alarm-latest /data/dbus-anchor-alarm

echo "Running setup script..."
chmod u+x /data/dbus-anchor-alarm/setup.sh
/data/dbus-anchor-alarm/setup.sh


echo "Starting service..."
ln -s /data/dbus-anchor-alarm/service /service/dbus-anchor-alarm
cd /service
sleep 5
svc -u dbus-anchor-alarm
