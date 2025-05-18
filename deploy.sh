# Get the current Git revision (short hash)
git_revision=$(git rev-parse --short HEAD)

# Write the revision to the VERSION file
echo "$git_revision" > VERSION

rsync -vr --exclude=".*" * root@victron.matsu:/data/dbus-anchor-alarm

# run by doing :
# cd /opt/victronenergy/services
# svc -u dbus-anchor-alarm