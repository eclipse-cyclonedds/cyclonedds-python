pragma Singleton

import QtCore
import QtQuick

Item {
    // Light mode
    property color lightPressedColor: "lightgrey"
    property color lightBorderColor: "lightgray"
    property color lightCardBackgroundColor: "#f6f6f6"
    property color lightHeaderBackground: "#e5e5e5"
    property color lightOverviewBackground: "#f3f3f3"
    property color lightMainContentBackground: "lightgray"
    property color lightSelectionBackground: "black"
    property color lightMainContent: "white"

    // Dark mode
    property color darkPressedColor: "#262626"
    property color darkBorderColor: "black"
    property color darkCardBackgroundColor: "#323232"
    property color darkHeaderBackground: "#323233"
    property color darkOverviewBackground: "#252526"
    property color darkMainContentBackground: "#1e1e1e"
    property color darkSelectionBackground: "white"
    property color darkMainContent: "#1e1e1e"
}
