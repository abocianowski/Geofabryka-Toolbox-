# -*- coding: utf-8 -*-

# ***************************************************************************
#   This program is free software; you can redistribute it and/or modify    *
#   it under the terms of the GNU General Public License as published by    *
#   the Free Software Foundation; either version 2 of the License, or       *
#   (at your option) any later version.                                     *
# ***************************************************************************
#     begin                : 2019-09-17                                     *
#     copyright            : (C) 2019 by Adrian Bocianowski                 *
#     email                : adrian at bocianowski.com.pl                   *
# ***************************************************************************

import os
import webbrowser

from PyQt5.QtCore import QCoreApplication

from .tools.cutter import Cutter
from .tools.oneSideBuffer import OneSideBuffer
from .tools.painter import Painter
from .dialogs.about import aboutPanel
from .tools.attributesJoinByLine import AttributesJoinByLine

class GeofabrykaToolbox:
    def __init__(self, iface):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = os.path.dirname(__file__)

        self.mainToolbar = self.iface.addToolBar(u'Geofabryka Toolbox')
        self.actions = []
        self.icon_path = ':/plugins/GeofabrykaToolbox/icons/'
        self.cutter = Cutter(self.iface,self.plugin_dir,self.mainToolbar,self.icon_path)
        self.buffer = OneSideBuffer(self.iface,self.plugin_dir,self.mainToolbar,self.icon_path)
        self.painter = Painter(self.iface,self.plugin_dir,self.mainToolbar,self.icon_path)
        self.attJoinByLine = AttributesJoinByLine(self.iface,self.plugin_dir,self.mainToolbar,self.icon_path)
        self.aboutTab = aboutPanel()

        self.cutter.settingsWidget.pushButton_geofabryka.pressed.connect(self.openBrowser)
        self.buffer.settingsWidget.pushButton_geofabryka.pressed.connect(self.openBrowser)
        self.painter.settingsWidget.pushButton_geofabryka.pressed.connect(self.openBrowser)

        self.cutter.settingsWidget.about.pressed.connect(self.showAbout)
        self.buffer.settingsWidget.about.pressed.connect(self.showAbout)
        self.painter.settingsWidget.about.pressed.connect(self.showAbout)

    def initGui(self):
        self.first_start = True

    def openBrowser(self):
        webbrowser.open('http://geofabryka.pl/')

    def showAbout(self):
        self.aboutTab.show()

    def tr(self, message):
        return QCoreApplication.translate('Geofabryka Toolbox', message)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Geofabryka Toolbox'),
                action)
            self.iface.removeToolBarIcon(action)