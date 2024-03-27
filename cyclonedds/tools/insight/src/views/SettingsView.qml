import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight


Popup {
    anchors.centerIn: parent
    modal: true
    height: 150
    width: 300

    GridLayout {
        columns: 2
        anchors.fill: parent
        anchors.margins: 10
        rowSpacing: 10
        columnSpacing: 10

        Label {
            text: qsTr("Settings")
            font.bold: true
            Layout.alignment: Qt.AlignHCenter
        }
        Item {}

        Label {
            text: "CYCLONEDDS_URI:"
        }
        TextField {
            id: login
            text: CYCLONEDDS_URI
            Layout.fillWidth: true
            readOnly: true
            activeFocusOnPress: false
        }

        Label {
            text: qsTr("Appearance:")
        }
        RadioButton {
            text: "Automatic (System)"
            checked: true
            checkable: false
        }   
    }
}
