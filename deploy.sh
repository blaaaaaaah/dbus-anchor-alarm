#find . | grep -E "(/__pycache__$|\.pyc$|\.pyo$)" | xargs rm -rf
scp -r * root@victron.matsu:~/dbus-anchor-alarm