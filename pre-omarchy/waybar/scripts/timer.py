#!/usr/bin/env python3
import sys
import os
import json
import time
import subprocess
import re
import threading
import math

STATE_FILE = os.path.expanduser('~/.cache/waybar-timer.json')

def load_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "state": "idle",
        "duration": 0,
        "end_time": 0.0,
        "paused_remaining": 0.0,
        "label": ""
    }

def save_state(state):
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    except Exception:
        pass

def format_time(seconds):
    if seconds <= 0:
        return "00:00"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    else:
        return f"{m:02d}:{s:02d}"

def get_progress_bar(percent, length=10):
    filled_length = int(round(length * percent / 100))
    bar = '█' * filled_length + '░' * (length - filled_length)
    return bar

def get_remaining(state_dict):
    current = time.time()
    if state_dict["state"] == "running":
        rem = state_dict["end_time"] - current
        if rem <= 0:
            return 0.0
        return rem
    elif state_dict["state"] == "paused":
        return state_dict["paused_remaining"]
    else:
        return 0.0

def parse_duration(s):
    s = s.strip().lower()
    if not s:
        return 0.0
    # Try format: HH:MM:SS or MM:SS
    if ":" in s:
        parts = s.split(":")
        try:
            if len(parts) == 2:
                return float(parts[0]) * 60 + float(parts[1])
            elif len(parts) == 3:
                return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except ValueError:
            pass
    
    # Try format: 1h30m10s
    matches = re.findall(r'(\d+)\s*([hms]?)', s)
    if matches:
        total = 0.0
        for val, unit in matches:
            try:
                val = float(val)
                if unit == 'h':
                    total += val * 3600
                elif unit == 'm':
                    total += val * 60
                elif unit == 's':
                    total += val
                else:
                    # Default to minutes if no unit is given
                    total += val * 60
            except ValueError:
                pass
        return total
    
    try:
        return float(s) * 60
    except ValueError:
        return 0.0

# Sound loop and notification management
alarm_playing = False
alarm_thread = None
notif_id = None

def play_sound_loop():
    global alarm_playing
    sound_path = "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"
    if not os.path.exists(sound_path):
        return
    while alarm_playing:
        proc = subprocess.Popen(["paplay", sound_path])
        # Wait for the sound to finish or alarm_playing to become False
        while proc.poll() is None:
            if not alarm_playing:
                proc.terminate()
                try:
                    proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return
            time.sleep(0.1)
        # 0.5s pause between loops
        time.sleep(0.5)

def start_alarm_and_notification():
    global alarm_playing, alarm_thread, notif_id
    if alarm_playing:
        return
    alarm_playing = True
    notif_id = None
    
    # Start sound loop thread
    alarm_thread = threading.Thread(target=play_sound_loop, daemon=True)
    alarm_thread.start()
    
    # Start notification thread
    def notif_task():
        global notif_id, alarm_playing
        try:
            proc = subprocess.Popen(
                [
                    "notify-send",
                    "-t", "0",
                    "-p",
                    "-w",
                    "-u", "critical",
                    "-i", "alarm-symbolic",
                    "Timer Finished!",
                    "Your timer has completed successfully."
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            # Read notification ID
            try:
                line = proc.stdout.readline()
                if line:
                    notif_id = int(line.strip())
            except Exception:
                pass
            proc.wait()
        except Exception:
            pass
        finally:
            alarm_playing = False
            # Transition state to idle if still finished
            try:
                state = load_state()
                if state["state"] == "finished":
                    state["state"] = "idle"
                    save_state(state)
            except Exception:
                pass

    threading.Thread(target=notif_task, daemon=True).start()

def stop_alarm_and_close_notification():
    global alarm_playing, notif_id
    alarm_playing = False
    if notif_id is not None:
        try:
            # Close the notification via DBus
            subprocess.Popen([
                "gdbus", "call", "--session",
                "--dest", "org.freedesktop.Notifications",
                "--object-path", "/org/freedesktop/Notifications",
                "--method", "org.freedesktop.Notifications.CloseNotification",
                str(notif_id)
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        notif_id = None

def cmd_status():
    # If daemon starts and state is finished, reset to idle
    state = load_state()
    if state["state"] == "finished":
        state["state"] = "idle"
        save_state(state)
        
    last_mtime = -1
    last_json_str = ""
    state = None
    last_state_name = ""
    
    while True:
        try:
            mtime = os.path.getmtime(STATE_FILE) if os.path.exists(STATE_FILE) else 0
        except Exception:
            mtime = 0
            
        if mtime != last_mtime or state is None:
            state = load_state()
            last_mtime = mtime
            
        current_time = time.time()
        st = state["state"]
        
        # Check if state transitioned away from finished
        if last_state_name == "finished" and st != "finished":
            stop_alarm_and_close_notification()
            
        last_state_name = st
        
        if st == "running":
            rem = state["end_time"] - current_time
            if rem <= 0:
                # Timer finished!
                state["state"] = "finished"
                state["paused_remaining"] = 0.0
                save_state(state)
                # Update last_mtime to prevent reloading state file in this loop iteration
                try:
                    last_mtime = os.path.getmtime(STATE_FILE) if os.path.exists(STATE_FILE) else 0
                except Exception:
                    pass
                st = "finished"
                rem = 0.0
                # Trigger alarm and notification
                start_alarm_and_notification()
        else:
            rem = get_remaining(state)
            
        # Build JSON for Waybar
        data = {}
        if st == "idle":
            data["text"] = "󰔚"
            data["tooltip"] = "Timer Idle\n\nLeft-click: Open Menu\nScroll up/down: Start quick timer (+/- 1 min)"
            data["class"] = "idle"
            data["percentage"] = 0
        elif st == "running":
            display_rem = int(math.ceil(rem))
            text_time = format_time(display_rem)
            data["text"] = f"󱎫 {text_time}"
            
            duration = state.get("duration", 1.0) or 1.0
            elapsed = duration - rem
            pct = min(100, max(0, int((elapsed / duration) * 100)))
            bar = get_progress_bar(pct)
            
            data["tooltip"] = (
                f"Timer Running\n"
                f"Remaining: {text_time} / {format_time(int(duration))}\n"
                f"Progress: [{bar}] {pct}%\n\n"
                f"Left-click: Pause\n"
                f"Right-click: Reset\n"
                f"Scroll: +/- 1 minute"
            )
            data["class"] = "running"
            data["percentage"] = pct
        elif st == "paused":
            display_rem = int(math.ceil(rem))
            text_time = format_time(display_rem)
            data["text"] = f"󰔛 {text_time}"
            
            duration = state.get("duration", 1.0) or 1.0
            elapsed = duration - rem
            pct = min(100, max(0, int((elapsed / duration) * 100)))
            bar = get_progress_bar(pct)
            
            data["tooltip"] = (
                f"Timer Paused\n"
                f"Remaining: {text_time} / {format_time(int(duration))}\n"
                f"Progress: [{bar}] {pct}%\n\n"
                f"Left-click: Resume\n"
                f"Right-click: Reset\n"
                f"Scroll: +/- 1 minute"
            )
            data["class"] = "paused"
            data["percentage"] = pct
        elif st == "finished":
            data["text"] = "󰂞 Time's Up!"
            data["tooltip"] = "Timer Finished!\n\nLeft-click or Right-click to dismiss"
            data["class"] = "finished"
            data["percentage"] = 100
            
        json_str = json.dumps(data)
        if json_str != last_json_str:
            print(json_str)
            sys.stdout.flush()
            last_json_str = json_str
            
        time.sleep(0.1)

def cmd_toggle():
    state = load_state()
    st = state["state"]
    current = time.time()
    
    if st == "idle" or st == "finished":
        state["state"] = "idle"
        state["duration"] = 0.0
        state["end_time"] = 0.0
        state["paused_remaining"] = 0.0
        save_state(state)
        cmd_menu()
    elif st == "running":
        rem = max(0.0, state["end_time"] - current)
        state["state"] = "paused"
        state["paused_remaining"] = rem
        save_state(state)
    elif st == "paused":
        rem = state["paused_remaining"]
        state["state"] = "running"
        state["end_time"] = current + rem
        save_state(state)

def cmd_reset():
    state = {
        "state": "idle",
        "duration": 0.0,
        "end_time": 0.0,
        "paused_remaining": 0.0,
        "label": ""
    }
    save_state(state)

def cmd_add(delta):
    state = load_state()
    st = state["state"]
    current = time.time()
    
    if st == "running":
        rem = max(0.0, state["end_time"] - current)
        new_rem = rem + delta
        if new_rem <= 0:
            state["state"] = "finished"
            state["paused_remaining"] = 0.0
            save_state(state)
        else:
            state["end_time"] = current + new_rem
            if new_rem > state["duration"]:
                state["duration"] = new_rem
            save_state(state)
    elif st == "paused":
        new_rem = state["paused_remaining"] + delta
        if new_rem <= 0:
            state["state"] = "idle"
            state["paused_remaining"] = 0.0
            save_state(state)
        else:
            state["paused_remaining"] = new_rem
            if new_rem > state["duration"]:
                state["duration"] = new_rem
            save_state(state)
    elif st == "idle" or st == "finished":
        if delta > 0:
            cmd_start(delta)

def cmd_menu():
    presets = [
        "5 Min",
        "10 Min",
        "15 Min",
        "25 Min (Pomodoro)",
        "30 Min",
        "45 Min",
        "60 Min",
        "Custom..."
    ]
    menu_input = "\n".join(presets)
    
    # Compact, modern black & white theme options for fuzzel, anchored below Waybar
    fuzzel_theme = [
        "fuzzel",
        "-d",
        "-w", "20",
        "-f", "JetBrainsMono Nerd Font:weight=bold:size=11",
        "-a", "center",
        "--minimal-lines",
        "-b", "00000099",               # Pure black base with 60% opacity
        "-t", "cdd6f4ff",               # Text color
        "--prompt-color=89b4faff",      # Blue prompt color
        "-m", "f38ba8ff",               # Match color (Red)
        "-s", "313244ff",               # Selection background
        "-S", "89b4faff",               # Selected text color (Blue)
        "-M", "f38ba8ff",               # Selected match color
        "-B", "2",                      # Border width
        "-r", "12",                     # Border radius (Rounded corners)
        "-C", "cba6f7aa",               # Border color
        "-x", "14",                     # Compact horizontal padding
        "-y", "14"                      # Compact vertical padding
    ]
    
    try:
        proc = subprocess.Popen(
            fuzzel_theme + ["-p", "Select Preset: "],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True
        )
        stdout, _ = proc.communicate(input=menu_input)
        choice = stdout.strip()
    except Exception:
        choice = ""
    
    if not choice:
        return
        
    if choice == "Custom...":
        custom_input = "5m (5 minutes)\n10m (10 minutes)\n15m (15 minutes)\n25m (25 minutes)\n30m (30 minutes)\n1h30m (1.5 hours)\n1:30 (90 seconds)\n1:30:00 (1.5 hours)"
        try:
            custom_proc = subprocess.Popen(
                fuzzel_theme + ["-p", "Enter Duration: "],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True
            )
            out, _ = custom_proc.communicate(input=custom_input)
            val = out.strip()
            if val:
                # Clean up suggestions descriptions in parenthesis
                val = re.sub(r'\(.*?\)', '', val).strip()
                seconds = parse_duration(val)
                if seconds > 0:
                    cmd_start(seconds)
        except Exception:
            pass
    else:
        m = re.search(r'(\d+)\s*Min', choice)
        if m:
            minutes = int(m.group(1))
            cmd_start(minutes * 60)

def cmd_start(seconds):
    current = time.time()
    state = {
        "state": "running",
        "duration": seconds,
        "end_time": current + seconds,
        "paused_remaining": 0.0,
        "label": ""
    }
    save_state(state)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        cmd_status()
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd == "status":
        cmd_status()
    elif cmd == "toggle":
        cmd_toggle()
    elif cmd == "reset":
        cmd_reset()
    elif cmd == "menu":
        cmd_menu()
    elif cmd == "add":
        if len(sys.argv) >= 3:
            try:
                val = int(sys.argv[2])
                cmd_add(val)
            except ValueError:
                pass
    elif cmd == "start":
        if len(sys.argv) >= 3:
            try:
                val = int(sys.argv[2])
                cmd_start(val)
            except ValueError:
                pass
