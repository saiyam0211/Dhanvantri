#!/bin/bash
# Simple health check
if [ -f "/app/main.py" ] && [ -x "/usr/bin/python3" ]; then
    exit 0
else
    exit 1
fi
