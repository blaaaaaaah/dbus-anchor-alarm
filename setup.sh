#!/bin/bash

# unpack this diretory into /data/dbus-anchor-alarm

# once only setup
chmod 1755 /data/dbus-anchor-alarm
chmod 755 /data/dbus-anchor-alarm/service/run
chmod 755 /data/dbus-anchor-alarm/service/log/run
chmod 755 /data/dbus-anchor-alarm/anchor_alarm_service.py

ln -s /data/dbus-anchor-alarm/service /opt/victronenergy/service/dbus-anchor-alarm
ln -s /usr/lib/node_modules/signalk-server/node_modules/ /data/dbus-anchor-alarm/node_modules
ln -s /data/dbus-anchor-alarm/pwa /var/www/venus/anchor


# Define the rc.local file path
RC_LOCAL="/data/rc.local"

# Define the commands to check/add
COMMAND1="ln -s /data/dbus-anchor-alarm/service /opt/victronenergy/service/dbus-anchor-alarm"
COMMAND2="ln -s /usr/lib/node_modules/signalk-server/node_modules/ /data/dbus-anchor-alarm/node_modules"
COMMAND3="ln -s /data/dbus-anchor-alarm/pwa /var/www/venus/anchor"

# Check if rc.local exists; if not, create it with the shebang
if [ ! -f "$RC_LOCAL" ]; then
    echo "Creating $RC_LOCAL with #!/bin/bash"
    echo "#!/bin/bash" > "$RC_LOCAL"
    chmod +x "$RC_LOCAL"  # Make the script executable
fi

# Function to add a command if it's not already in the file
add_command_if_missing() {
    local command="$1"
    if ! grep -Fxq "$command" "$RC_LOCAL"; then
        echo "Adding command: $command"
        echo "$command" >> "$RC_LOCAL"
    else
        echo "Command already exists: $command"
    fi
}

# Check and add commands
add_command_if_missing "$COMMAND1"
add_command_if_missing "$COMMAND2"
add_command_if_missing "$COMMAND3"

echo "Done processing $RC_LOCAL."