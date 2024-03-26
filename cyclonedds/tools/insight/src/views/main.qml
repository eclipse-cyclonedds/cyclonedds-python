import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight


ApplicationWindow {
    id: rootWindow
    width: 1100
    height: 650
    visible: true
    title: "CycloneDDS Insight"

    property bool isDarkMode: false

    header: HeaderToolBar {}

    SystemPalette {
        id: mySysPalette
        onDarkChanged: {
            rootWindow.isDarkMode = getDarkMode()
        }
    }

    function getDarkMode() {
        var isDarkModeVal = (mySysPalette.windowText.hsvValue > mySysPalette.window.hsvValue)
        console.log("qt build in darkmode check: isDarkMode", isDarkModeVal)
        return isDarkModeVal
    }

    Component.onCompleted: {
        console.log("Running on platform.os:", Qt.platform.os)
        rootWindow.isDarkMode = getDarkMode()
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            id: domainSplit
            implicitWidth: 350
            SplitView.minimumWidth: 50
            color: rootWindow.isDarkMode ? Constants.darkOverviewBackground : Constants.lightOverviewBackground

            TopicOverview {}
        }
        Rectangle {
            id: centerItem
            SplitView.minimumWidth: 50
            SplitView.fillWidth: true
            color: rootWindow.isDarkMode ? Constants.darkMainContentBackground : Constants.lightMainContentBackground

           /* TabBar {
                id: bar
                width: parent.width
                TabButton {
                    text: qsTr("Overview")
                }
                TabButton {
                    text: qsTr("Data")
                }
            }

            StackLayout {
                width: parent.width
                currentIndex: bar.currentIndex
                Item {
                    id: overviewTab
                }
                Item {
                    id: dataTab
                }
            }*/
        }
    }

    SettingsView {
        id: settingsDialog
    }
}
