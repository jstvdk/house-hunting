#!/bin/sh
# Runs the scraper forever, restarting it if it crashes.

echo "starting run"

python3 scraper.py

echo "scraper exited, restarting"

sh run.sh
