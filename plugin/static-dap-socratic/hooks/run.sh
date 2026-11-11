#!/bin/sh
# Find a Python 3 interpreter even when the GUI app's PATH is minimal.
for py in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /usr/bin/python3; do
    if command -v "$py" >/dev/null 2>&1; then
        exec "$py" "$@"
    fi
done
exit 0
