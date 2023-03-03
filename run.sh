#!/bin/bash

[ -d venv ] || python3 -m virtualenv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 rustore-apk-scanner.py
