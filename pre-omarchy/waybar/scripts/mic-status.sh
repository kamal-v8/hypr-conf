#!/bin/bash

STATUS=$(wpctl get-volume @DEFAULT_AUDIO_SOURCE@)

if [[ "$STATUS" == *"MUTED"* ]]; then
  echo '{"text": "", "tooltip": "Microphone: muted", "class": "muted"}'
else
  echo '{"text": "", "tooltip": "Microphone: unmuted", "class": "unmuted"}'
fi
