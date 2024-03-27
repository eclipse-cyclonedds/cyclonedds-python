import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight

ToolBar {
    topPadding: 10
    bottomPadding: 10
    leftPadding: 10
    rightPadding: 10

    background: Rectangle {
        anchors.fill: parent
        color: rootWindow.isDarkMode ? Constants.darkHeaderBackground : Constants.lightHeaderBackground
    }

    RowLayout {
        anchors.fill: parent
        Image {
            source: "qrc:/res/images/cyclonedds.png"
            sourceSize.width: 30
            sourceSize.height: 30
        }
        Label {
            text: rootWindow.title
        }
        Item {
            Layout.fillWidth: true
        }
        ToolButton {
            text: "Settings"
            onClicked: {
                settingsDialog.open()
            }
        }
    }
}
