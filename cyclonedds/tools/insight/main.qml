import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

Window {
    width: 1100
    height: 650
    visible: true
    title: "CycloneDDS Insight"

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            id: domainSplit
            implicitWidth: 350
            SplitView.minimumWidth: 50
            color: "lightblue"

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
                        console.log("onCurrentChanged", row, column, model.display)
                    }

                    Rectangle {
                        id: background
                        anchors.fill: parent
                        visible: row === treeView.currentRow
                        color: "black"
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
                        text: model.display

/*
                        MouseArea {
                            anchors.fill: parent
                            onClicked: {
                                console.log("clicked", row, column)
                            }
                        }*/
                    }
                }
            }


        }
        Rectangle {
            id: centerItem
            SplitView.minimumWidth: 50
            SplitView.fillWidth: true
            color: "lightgray"

            TabBar {
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
            }

        }
    }

}
