import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts

import org.eclipse.cyclonedds.insight


Rectangle {
    id: topicEndpointView
    color: rootWindow.isDarkMode ? Constants.darkMainContent : Constants.lightMainContent

    property int domainId
    property string topicName

    EndpointModel {
        id: endpointWriterModel
    }

    EndpointModel {
        id: endpointReaderModel
    }

    Component.onCompleted: {
        console.log("TopicEndpointView for topic:", topicName, ", domainId:", domainId)
        endpointWriterModel.setDomainId(parseInt(domainId), topicName, 4)
        endpointReaderModel.setDomainId(parseInt(domainId), topicName, 3)
    }

    Column {
        anchors.fill: parent
        padding: 10

        ScrollView {
            contentWidth: topicEndpointView.width
            height: topicEndpointView.height

            Column {
                width: parent.width - 20
                spacing: 10

                Label {
                    text: "Domain Id: " + domainId
                }
                Label {
                    text: "Topic Name: " + topicName
                }

                Row {
                    width: parent.width - 10

                    Column {
                        width: parent.width / 2

                        Label {
                            text: "Writer"
                        }

                        ListView {
                            id: listViewWriter
                            model: endpointWriterModel
                            width: parent.width
                            height: contentHeight
                            clip: true
                            interactive: false

                            delegate: Item {
                                height: 50
                                width: listViewWriter.width

                                Rectangle {
                                    id: writerRec
                                    property bool showTooltip: false

                                    anchors.fill: parent
                                    color: rootWindow.isDarkMode ? mouseAreaEndpointWriter.pressed ? Constants.darkPressedColor : Constants.darkCardBackgroundColor : mouseAreaEndpointWriter.pressed ? Constants.lightPressedColor : Constants.lightCardBackgroundColor
                                    border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                                    border.width: 0.5
                                    Column {
                                        spacing: 0
                                        padding: 10

                                        Label {
                                            text: endpoint_key
                                            font.pixelSize: 14
                                        }
                                        Label {
                                            text: endpoint_process_name + ":" + endpoint_process_id + "@" + endpoint_hostname
                                            font.pixelSize: 12
                                        }
                                    }
                                    MouseArea {
                                        id: mouseAreaEndpointWriter
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onEntered: {
                                            writerRec.showTooltip = true
                                        }
                                        onExited: {
                                            writerRec.showTooltip = false
                                        }
                                    }
                                    ToolTip {
                                        id: writerTooltip
                                        parent: writerRec
                                        visible: writerRec.showTooltip
                                        delay: 200
                                        text: "Key: " +endpoint_key + "\nParticipant Key:" + endpoint_participant_key + "\nInstance Handle: " + endpoint_participant_instance_handle + "\nTopic Name:" + endpoint_topic_name + "\nTopic Type: " + endpoint_topic_type + "\nQos:\n" + endpoint_qos + "\nType Id: " + endpoint_type_id
                                        contentItem: Label {
                                            text: writerTooltip.text
                                        }
                                        background: Rectangle {
                                            border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                                            border.width: 1
                                            color: rootWindow.isDarkMode ? Constants.darkCardBackgroundColor : Constants.lightCardBackgroundColor
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        width: 10
                        height: 10
                    }

                    Column {
                        width: parent.width / 2

                        Label {
                            text: "Reader"
                        }
                        ListView {
                            id: listViewReader
                            model: endpointReaderModel
                            width: parent.width
                            height: contentHeight
                            clip: true
                            interactive: false

                            delegate: Item {
                                height: 50
                                width: listViewReader.width

                                Rectangle {
                                    anchors.fill: parent
                                    color: rootWindow.isDarkMode ? mouseAreaEndpointReader.pressed ? Constants.darkPressedColor : Constants.darkCardBackgroundColor : mouseAreaEndpointReader.pressed ? Constants.lightPressedColor : Constants.lightCardBackgroundColor
                                    border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                                    border.width: 0.5
                                    id: readerRec
                                    property bool showTooltip: false

                                    Column {
                                        spacing: 0
                                        padding: 10

                                        Label {
                                            text: endpoint_key
                                            font.pixelSize: 14
                                        }
                                        Label {
                                            text: endpoint_process_name + ":" + endpoint_process_id + "@" + endpoint_hostname
                                            font.pixelSize: 12
                                        }
                                    }
                                    MouseArea {
                                        id: mouseAreaEndpointReader
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onEntered: {
                                            readerRec.showTooltip = true
                                        }
                                        onExited: {
                                            readerRec.showTooltip = false
                                        }
                                    }
                                    ToolTip {
                                        id: readerTooltip
                                        parent: readerRec
                                        visible: readerRec.showTooltip
                                        delay: 200
                                        text: "Key: " + endpoint_key + "\nParticipant Key:" + endpoint_participant_key + "\nInstance Handle: " + endpoint_participant_instance_handle + "\nTopic Name:" + endpoint_topic_name + "\nTopic Type: " + endpoint_topic_type + "\nQos:\n" + endpoint_qos + "\nType Id: " + endpoint_type_id
                                        contentItem: Label {
                                            text: readerTooltip.text
                                        }
                                        background: Rectangle {
                                            border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                                            border.width: 1
                                            color: rootWindow.isDarkMode ? Constants.darkCardBackgroundColor : Constants.lightCardBackgroundColor
                                        }
                                    }
                                }
                            }
                        }
                    }
                }            
            }
        }
    }
}
