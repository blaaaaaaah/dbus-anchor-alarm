#!/bin/bash

#TODO : do simlink for node_modules ?
# ln -s /usr/lib/node_modules/signalk-server/node_modules/ /data/dbus-anchor-alarm/node_modules

#unpack this diretory into /data/dbus-anchor-alarm
# once only setup
chmod 1755 /data/dbus-anchor-alarm
chmod 755 /data/dbus-anchor-alarm/service/run
chmod 755 /data/dbus-anchor-alarm/service/log/run

cat > /data/rc.local << EOF
#!/bin/bash

ln -s /data/dbus-anchor-alarm/service /opt/victronenergy/service/dbus-anchor-alarm
echo "Enabled dbus-anchor-alarm"

EOF