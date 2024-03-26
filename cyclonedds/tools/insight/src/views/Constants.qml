pragma Singleton

import QtCore
import QtQuick

Item {
    // Light mode
    property color lightHeaderBackground: "#e5e5e5"
    property color lightOverviewBackground: "#f3f3f3"
    property color lightMainContentBackground: "lightgray"
    property color lightSelectionBackground: "black"

    // Dark mode
    property color darkHeaderBackground: "#323233"
    property color darkOverviewBackground: "#252526"
    property color darkMainContentBackground: "#1e1e1e"
    property color darkSelectionBackground: "white"
}
