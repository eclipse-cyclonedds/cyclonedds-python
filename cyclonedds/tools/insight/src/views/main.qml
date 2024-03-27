import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

import org.eclipse.cyclonedds.insight


ApplicationWindow {
    id: rootWindow
    width: 1100
    height: 650
    visible: true
    title: "CycloneDDS Insight"

    property bool isDarkMode: false
    property var childView

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

            StackView {
                id: stackView
                anchors.fill: parent

            }
        }
    }

    SettingsView {
        id: settingsDialog
    }

    AddDomainView {
        id: addDomainView
    }

    MessageDialog {
        id: noDomainSelectedDialog
        title: qsTr("Alert");
        text: qsTr("No Domain selected!");
        buttons: MessageDialog.Ok;
    }

    function showTopicEndpointView(domainId, topicName) {
        stackView.clear()
        if (childView) {
            childView.destroy()
        }
        var childComponent = Qt.createComponent("qrc:/src/views/TopicEndpointView.qml")
        if (childComponent.status === Component.Ready) {
            childView = childComponent.createObject(
                        stackView, {
                            domainId: domainId,
                            topicName: topicName
                        });
            stackView.replace(childView);
        } else {
            console.log("Failed to create component TopicEndpointView")
        }
    }
}
