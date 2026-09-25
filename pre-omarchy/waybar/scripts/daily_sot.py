#!/usr/bin/env python3
import os, json, time

CACHE_FILE = os.path.expanduser('~/.cache/waybar_daily_sot.json')
today = time.strftime('%Y-%m-%d')

try:
    with open('/proc/stat') as f:
        btime = int([line.split()[1] for line in f if line.startswith('btime')][0])
except:
    btime = 0

try:
    with open('/proc/uptime') as f:
        uptime = float(f.read().split()[0])
except:
    uptime = 0

data = {'date': today, 'previous_sessions_uptime': 0, 'current_session_uptime': 0, 'last_btime': btime}

if os.path.exists(CACHE_FILE):
    try:
        with open(CACHE_FILE) as f:
            saved_data = json.load(f)
            if saved_data.get('date') == today:
                data = saved_data
    except:
        pass

# If the boot time changed, it means the system rebooted.
# We add the last recorded uptime from the previous session to the accumulated total.
if data.get('last_btime') != btime:
    data['previous_sessions_uptime'] += data.get('current_session_uptime', 0)
    data['last_btime'] = btime

# Always update the current session's uptime
data['current_session_uptime'] = uptime

with open(CACHE_FILE, 'w') as f:
    json.dump(data, f)

total_seconds = data['previous_sessions_uptime'] + uptime

hours = int(total_seconds // 3600)
minutes = int((total_seconds % 3600) // 60)

if hours > 0:
    print(f"{hours}h {minutes}m")
else:
    print(f"{minutes}m")
