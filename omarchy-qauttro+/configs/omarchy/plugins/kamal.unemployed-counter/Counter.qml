import QtQuick
import Quickshell
import qs.Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "kamal.unemployed-counter"

  property int daysUnemployed: 0

  function updateDays() {
    var now = new Date()
    var past = new Date(2026, 5, 27) 
    var diffTime = now - past
    daysUnemployed = Math.max(0, Math.floor(diffTime / (1000 * 60 * 60 * 24)))
  }

  Timer {
    interval: 60000
    running: true
    repeat: true
    onTriggered: root.updateDays()
  }

  Component.onCompleted: root.updateDays()

  visible: !vertical
  implicitWidth: visible ? labelText.implicitWidth + 16 : 0
  implicitHeight: barSize

  Text {
    id: labelText
    anchors.centerIn: parent
    text: "󰜎 " + root.daysUnemployed + " days"
     color: "#EF4444"
    font.family: root.bar ? root.bar.fontFamily : Style.font.family
    font.pixelSize: Style.font.body
    font.bold: true
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    onEntered: if (root.bar) root.bar.showTooltip(root, "Unemployed since June 27th")
    onExited: if (root.bar) root.bar.hideTooltip(root)
  }
}
