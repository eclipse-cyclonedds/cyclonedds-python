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

    header: ToolBar {
        topPadding: 10
        bottomPadding: 10
        leftPadding: 10
        rightPadding: 10

        background: Rectangle {
            anchors.fill: parent
            color: "#e5e5e5"
        }

        RowLayout {
            anchors.fill: parent
            Image {
                source: "./../res/cyclonedds.png"
                sourceSize.width: 30
                sourceSize.height: 30
            }
            Label {
                text: "CycloneDDS"
            }
            Item { Layout.fillWidth: true }
            ToolButton {
                text: "Settings"
            }
        }
    }

    SplitView {
        anchors.fill: parent
        orientation: Qt.Horizontal

        Rectangle {
            id: domainSplit
            implicitWidth: 350
            SplitView.minimumWidth: 50
            color: "#f3f3f3"

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
                        text: model.is_domain ? "Domain " + model.display : model.display 

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

/*
            ListView {
                id: domainListView
                anchors.fill: parent
                clip: true
                model: domainModel
                spacing: 0

                delegate: Rectangle {

                    width: domainSplit.width
                    height: isOpen ? topicListView.contentHeight + domainRectangle.height + 10 : domainRectangle.height
                    //height: 500
                    border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                    border.width: 0.5

                    property bool isOpen: false
                    property int rotationAngle: 0

                    TopicModel {
                        id: topicModel
                        Component.onCompleted: {
                            topicModel.setDomainId(domain_id)
                        }
                    }

                    ColumnLayout {

                        anchors.fill: parent
                        spacing: 0

                        Rectangle {
                            id: domainRectangle
                            color: "red"
                            Layout.preferredHeight: 50
                            RowLayout {
                                id: domainLayout
                                anchors.fill: parent

                                Label {
                                    id: labelTurnItem
                                    text: "▶"
                                    leftPadding: 10
                                    transform: Rotation {
                                        origin.x: labelTurnItem.width / 2
                                        origin.y: labelTurnItem.height / 2
                                        angle: rotationAngle
                                    }
                                }
                                Label {
                                    id: labelItem
                                    text: "Domain " + domain_id

                                    MouseArea {
                                        id: mouseAreaDel
                                        anchors.fill: parent
                                        onClicked: {
                                            isOpen = !isOpen
                                            if (isOpen) {
                                                rotationAngle += 90;
                                            } else {
                                                rotationAngle -= 90;
                                            }
                                            
                                        }
                                    }
                                }
                            }
                        }

                        ListView {
                            id: topicListView
                            visible: isOpen
                            width: parent.width
                            height: topicListView.contentHeight
                            clip: true
                            model: topicModel
                            spacing: 0
                            interactive: false

                            delegate: Rectangle {
                                width: domainSplit.width
                                height: 20
                                color: rootWindow.isDarkMode ? mouseAreaTopicDel.pressed ? Constants.darkPressedColor : Constants.darkCardBackgroundColor : mouseAreaTopicDel.pressed ? Constants.lightPressedColor : Constants.lightCardBackgroundColor

                                Label {
                                    id: topicLabel
                                    text: "Topic Name: " + topic_name
                                    leftPadding: 30
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignLeft
                                    verticalAlignment: Text.AlignVCenter
                                }

                                MouseArea {
                                    id: mouseAreaTopicDel
                                    anchors.fill: parent
                                    onClicked: {
                                        console.log("clicked on topic" + topic_name)
                                        
                                    }
                                }
                                
                            }
                        }

                        Item {
                            visible: isOpen
                            Layout.preferredHeight: 10
                        }


                    }



                }
            }*/
            

        }
        Rectangle {
            id: centerItem
            SplitView.minimumWidth: 50
            SplitView.fillWidth: true
            color: "lightgray"



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

}
