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

from PyQt5 import uic
from PyQt5 import QtWidgets
from PyQt5.QtCore import pyqtSignal

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'buffer_settingsPanel.ui'))

class settingsPanel(QtWidgets.QDockWidget, FORM_CLASS):
    closingPanel = pyqtSignal()

    def __init__(self, parent=None):
        super(settingsPanel, self).__init__(parent)
        self.setupUi(self)

    def closeEvent(self, event):
        self.closingPanel.emit()
        event.accept()
