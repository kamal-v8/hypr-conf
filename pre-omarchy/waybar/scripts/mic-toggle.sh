#!/bin/bash

# Get current mic status
STATUS=$(wpctl get-volume @DEFAULT_AUDIO_SOURCE@)

if [[ "$STATUS" == *"MUTED"* ]]; then
  # Unmute
  wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 0
  notify-send -i microphone-sensitivity-high "Microphone" "Microphone unmuted" -t 1500
else
  # Mute
  wpctl set-mute @DEFAULT_AUDIO_SOURCE@ 1
  notify-send -i microphone-sensitivity-muted "Microphone" "Microphone muted" -t 1500
fi

# Force waybar to refresh this module
pkill -RTMIN+8 waybar
