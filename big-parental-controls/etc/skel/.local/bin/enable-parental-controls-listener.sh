#!/bin/bash

systemctl --user enable parental-controls-listener.service
systemctl --user start parental-controls-listener.service

SELF="$(readlink -f "$0")"
rm -f "$SELF"
rm -f ~/.config/autostart/parental-controls.desktop