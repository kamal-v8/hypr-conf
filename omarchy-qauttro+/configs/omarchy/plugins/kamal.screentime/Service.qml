import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland

Item {
  id: root
  property var shell: null
  
  IdleMonitor {
    id: idleMonitor
    timeout: 60000 // 1 minute in milliseconds wait, IdleMonitor takes seconds or ms?
    respectInhibitors: true
  }

  // Timer to record every minute
  Timer {
    id: recordTimer
    interval: 60000
    repeat: true
    running: true
    onTriggered: {
      if (!idleMonitor.isIdle) {
        recordProcess.running = true
      }
    }
  }

  Process {
    id: recordProcess
    command: ["python3", "/home/kamal/.config/omarchy/plugins/kamal.screentime/tracker.py", "record"]
  }

  Component.onCompleted: {
    console.log("Screentime service started.")
    // idleMonitor timeout is in seconds, let's fix it
    idleMonitor.timeout = 60
  }
}
