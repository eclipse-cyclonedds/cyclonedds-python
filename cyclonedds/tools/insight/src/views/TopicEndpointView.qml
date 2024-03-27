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
        id: endpointPublisherModel
    }

    EndpointModel {
        id: endpointSubscriberModel
    }

    Component.onDestruction: {
        console.log("Destoryed")
    }

    Component.onCompleted: {
        console.log("TopicEndpointView for topic:", topicName, ", domainId:", domainId)
        endpointPublisherModel.setDomainId(parseInt(domainId), topicName, true)
        endpointSubscriberModel.setDomainId(parseInt(domainId), topicName, false)
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
                            text: "Publisher"
                        }

                    ListView {
                        id: listViewPub
                        model: endpointPublisherModel
                        width: parent.width
                        height: contentHeight
                        clip: true
                        interactive: false

                        delegate: Item {
                            height: 50
                            width: listViewPub.width

                            Rectangle {
                                id: pubRec
                                property bool showTooltip: false

                                anchors.fill: parent
                                color: rootWindow.isDarkMode ? mouseAreaEndpointPub.pressed ? Constants.darkPressedColor : Constants.darkCardBackgroundColor : mouseAreaEndpointPub.pressed ? Constants.lightPressedColor : Constants.lightCardBackgroundColor
                                border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                                border.width: 0.5
Column {
        spacing: 0
    padding: 10
                                    Label {
                                    text: endpoint_key
     
                                }
                                Label {
                                    text: "todo@host"
                            
                                }
}
                                MouseArea {
                                    id: mouseAreaEndpointPub
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: {
                                        pubRec.showTooltip = true
                                    }
                                    onExited: {
                                        pubRec.showTooltip = false
                                    }
                                }
                                ToolTip {
                                    id: pubTooltip
                                    parent: pubRec
                                    visible: pubRec.showTooltip
                                    delay: 200
                                    text: "Key: " +endpoint_key + "\nParticipant Key:" + endpoint_participant_key + "\nInstance Handle: " + endpoint_participant_instance_handle + "\nTopic Name:" + endpoint_topic_name + "\nTopic Type: " + endpoint_topic_type + "\nQos:\n" + endpoint_qos + "\nType Id: " + endpoint_type_id
                                    contentItem: Label {
                                        text: pubTooltip.text
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
                            text: "Subscriber"
                        }
                    ListView {
                        id: listViewSub
                        model: endpointSubscriberModel
                        width: parent.width
                        height: contentHeight
                        clip: true
                        interactive: false

                        delegate: Item {
                            height: 50
                            width: listViewSub.width

                            Rectangle {
                                anchors.fill: parent
                                color: rootWindow.isDarkMode ? mouseAreaEndpointSub.pressed ? Constants.darkPressedColor : Constants.darkCardBackgroundColor : mouseAreaEndpointSub.pressed ? Constants.lightPressedColor : Constants.lightCardBackgroundColor
                                border.color: rootWindow.isDarkMode ? Constants.darkBorderColor : Constants.lightBorderColor
                                border.width: 0.5
                                id: subRec
                                property bool showTooltip: false
Column {
    spacing: 0
    padding: 10
                                    Label {
                                    text: endpoint_key
                                    
                                }
                                Label {
                                    text: "todo@host"
                                    
                                }
                                    }
                                    MouseArea {
                                        id: mouseAreaEndpointSub
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onEntered: {
                                            subRec.showTooltip = true
                                        }
                                        onExited: {
                                            subRec.showTooltip = false
                                        }
                                    }
                                    ToolTip {
                                        id: subTooltip
                                        parent: subRec
                                        visible: subRec.showTooltip
                                        delay: 200
                                        text: "Key: " + endpoint_key + "\nParticipant Key:" + endpoint_participant_key + "\nInstance Handle: " + endpoint_participant_instance_handle + "\nTopic Name:" + endpoint_topic_name + "\nTopic Type: " + endpoint_topic_type + "\nQos:\n" + endpoint_qos + "\nType Id: " + endpoint_type_id
                                        contentItem: Label {
                                            text: subTooltip.text
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
