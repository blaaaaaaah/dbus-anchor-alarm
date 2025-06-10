# Get the current Git revision (short hash)
git_revision=$(git rev-parse --short HEAD)

# Write the revision to the VERSION file
echo "$git_revision" > VERSION

rsync -vr --exclude=".*" * root@victron.matsu:/data/dbus-anchor-alarm

# on first time, ssh into the cerbo and run /data/dbus-anchor-alarm/setup.sh to install symlinks

# run as service by doing
# cd /opt/victronenergy/service/
# svc -u dbus-anchor-alarm

# or run directly python3 anchor_alarm_service.py