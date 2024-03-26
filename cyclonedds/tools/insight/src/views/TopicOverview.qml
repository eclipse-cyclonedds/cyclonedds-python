import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight


TreeView {
    id: treeView
    anchors.fill: parent
    anchors.margins: 10
    clip: true
    selectionModel: ItemSelectionModel {}
    model: treeModel

    delegate: Item {
        implicitWidth: domainSplit.width
        implicitHeight: label.implicitHeight * 1.5

        readonly property real indentation: 20
        readonly property real padding: 5

        // Assigned to by TreeView:
        required property TreeView treeView
        required property bool isTreeNode
        required property bool expanded
        required property int hasChildren
        required property int depth
        required property int row
        required property int column
        required property bool current

        // Rotate indicator when expanded by the user
        // (requires TreeView to have a selectionModel)
        property Animation indicatorAnimation: NumberAnimation {
            target: indicator
            property: "rotation"
            from: expanded ? 0 : 90
            to: expanded ? 90 : 0
            duration: 100
            easing.type: Easing.OutQuart
        }
        TableView.onPooled: indicatorAnimation.complete()
        TableView.onReused: if (current) indicatorAnimation.start()
        onExpandedChanged: {
            indicator.rotation = expanded ? 90 : 0
        }

        onCurrentChanged: {
            console.log("onCurrentChanged", row, column, model.display, treeView.currentRow)
        }

        Rectangle {
            id: background
            anchors.fill: parent
            visible: row === treeView.currentRow
            color: rootWindow.isDarkMode ? Constants.darkSelectionBackground : Constants.lightSelectionBackground
            opacity: 0.3
        }

        Label {
            id: indicator
            x: padding + (depth * indentation)
            anchors.verticalCenter: parent.verticalCenter
            visible: isTreeNode && hasChildren
            text: "▶"

            TapHandler {
                onSingleTapped: {
                    let index = treeView.index(row, column)

                    treeView.selectionModel.setCurrentIndex(index, ItemSelectionModel.NoUpdate)
                    treeView.toggleExpanded(row)
                }
            }
        }

        Label {
            id: label
            x: padding + (isTreeNode ? (depth + 1) * indentation : 0)
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width - padding - x
            clip: true
            text: model.is_domain ? "Domain " + model.display : model.display 

/*
            MouseArea {
                anchors.fill: parent
                onClicked: {
                    console.log("clicked", row, column)
                }
            }*/
        }

        Menu {
            id: contextMenuDomain
            MenuItem {
                text: "Remove Domain " + model.display
                onClicked: console.log("Clicked remove domain")
            }
        }

    }
}