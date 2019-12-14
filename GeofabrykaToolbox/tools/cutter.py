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
from ..resources import *
from ..dialogs.cutter_settingsPanel import settingsPanel

from PyQt5.QtCore import QSettings, QCoreApplication, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor
from PyQt5.QtWidgets import  QToolButton, QMenu, QAction, QListWidgetItem, QMessageBox

from qgis.gui import QgsMapTool, QgsVertexMarker, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsGeometry, QgsProject, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsFeature, QgsVectorLayerEditUtils

class Cutter:
    def __init__(self, iface, plugin_dir, toolbar, icon_path):
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.plugin_dir = plugin_dir
        self.toolsToolbar = toolbar
        self.icon_path = icon_path

        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'qrectanglecreator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.settingsWidget = settingsPanel() 
        self.settingsWidget.showButton.clicked.connect(self.clickShowAll)
        self.settingsWidget.hideButton.clicked.connect(self.clickHideAll)

        icon = QIcon(self.icon_path + 'selectAll.svg')
        self.settingsWidget.showButton.setIcon(icon)

        icon = QIcon(self.icon_path + 'hideAll.svg')
        self.settingsWidget.hideButton.setIcon(icon)

        icon = QIcon(self.icon_path + 'geofabryka.png')
        self.settingsWidget.pushButton_geofabryka.setIcon(icon)

        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.settingsWidget)
        self.settingsWidget.hide()

        self.qgsProject = QgsProject.instance()
        self.qgsProject.layersAdded.connect(self.layerWasAdded)
        self.qgsProject.layersWillBeRemoved.connect(self.layerWasRemoved)

        self.setPolygonLayers()
        self.rebuildListWidget()
        self.rebuildComboBox()

        self.geometryClass = Cutter_geometry()
        
        self.tool = addPolygon(self.iface, None, self.geometryClass)
        self.tool.cut.connect(self.cutLayers)
        self.tool.deact.connect(self.settingsWidget.hide)

        self.initGui()

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
        checkable=False,
        checked=False,
        shortcut=None):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolsToolbar.addAction(action)

        if checkable:
            action.setCheckable(True)
            
        if checked:
            action.setChecked(1)

        if shortcut:
            action.setShortcut(shortcut)

        return action

    def cutLayers(self):
        layers = self.getLayersToCut()
        if len(layers) == 0:
            QMessageBox.warning(None,'No source layers', 'Select source layers in the settings')
            return

        t_layer_idx = self.getTargetLayer()
        if t_layer_idx == 0:
            QMessageBox.warning(None,'Missing target layer', 'Select the target layer in the settings')
            return

        source_geom = QgsGeometry(self.geometryClass.geometry)

        if source_geom.isGeosValid() == False:
            source_geom = geom.makeValid()

        if source_geom.isGeosValid() == False:
            QMessageBox.warning(None,'Geometry error', 'The source geometry is incorrect')
            return

        dest_geom = []

        for layer in layers:
            if not layer.isEditable():
                    layer.startEditing()

            geom = QgsGeometry(source_geom)

            for f in layer.getFeatures(geom.boundingBox()):
                f_geom = f.geometry()
                
                if f_geom.intersects(geom):

                    dest_geom.append(f_geom.intersection(geom))

                    f_geom = f_geom.difference(geom)
                    att = f.attributes()

                    for part in f_geom.parts():
                        part_wkt = part.asWkt()
                        part_geom = QgsGeometry.fromWkt(part_wkt)
                        
                        new_feature = QgsFeature()
                        new_feature.setGeometry(part_geom)
                        new_feature.setAttributes(att)
                        layer.addFeature(new_feature)   

                    layer.deleteFeature(f.id())

        if len(dest_geom) > 0:
            target_geom = QgsGeometry().unaryUnion(dest_geom)
            target_layer = self.polygonLayers[t_layer_idx - 1 ][0]

            for part in target_geom.parts():
                part_wkt = part.asWkt()
                part_geom = QgsGeometry.fromWkt(part_wkt)
                self.addTopologicalPointsForActiveLayers(part_geom)

                feature = QgsFeature(target_layer.fields())
                feature.setGeometry(part_geom)
                target_layer.addFeature(feature)  

    def addTopologicalPointsForActiveLayers(self, geometry):
        geometry = QgsGeometry(geometry)
        layers = self.polygonLayers

        for l in layers:
            layer = l[0]
            if not layer.isEditable():
                layer.startEditing()

            topology = QgsVectorLayerEditUtils(layer)
            vertices = [v for v in geometry.vertices()]

            for v in vertices:
                point = v.asWkt()
                point = QgsGeometry.fromWkt(point)
                point = point.asPoint()
                topology.addTopologicalPoints(point)  
        return True

    def clickShowAll(self):
        for i in range(0, len(self.polygonLayers)):
            item = self.settingsWidget.listWidget.item(i)
            item.setCheckState(2)

    def clickHideAll(self):
        for i in range(0, len(self.polygonLayers)):
            item = self.settingsWidget.listWidget.item(i)
            item.setCheckState(0)

    def geometryCrs2Crs(self,geometry, source_crs, destination_crs):
        geometry = QgsGeometry(geometry)
        src_crs = QgsCoordinateReferenceSystem(source_crs)
        dest_crs = QgsCoordinateReferenceSystem(destination_crs)
        crs2crs = QgsCoordinateTransform(src_crs, dest_crs, QgsProject.instance())
        geometry.transform(crs2crs)
        return geometry

    def getLayersToCut(self):
        layers = []
        for i in range(0, len(self.polygonLayers)):
            item = self.settingsWidget.listWidget.item(i)
            if item.checkState() == 2:
                layers.append(self.polygonLayers[i][0])
        return layers

    def getTargetLayer(self):
        idx = self.settingsWidget.comboBox.currentIndex()
        return idx

    def getLayerListId(self, layerid):
        i = 0
        for l in self.polygonLayers:
            if l[1] == layerid:
                return i
            i += 1

    def layerWasAdded(self,layers):
        for l in layers:
            if  l.type() == 0:
                if l.geometryType() == 2:
                    self.polygonLayers.append([l,l.id()])
                    item = QListWidgetItem(l.name())
                    item.setCheckState(Qt.Unchecked)
                    self.settingsWidget.listWidget.addItem(item)
                    self.settingsWidget.comboBox.addItem(l.name())

    def layerWasRemoved(self, layers):
        try:
            for l in layers:
                l_id = self.getLayerListId(l)
                item = self.settingsWidget.listWidget.takeItem(l_id)
                self.settingsWidget.comboBox.removeItem(l_id+1)
                self.removeLayer(l)

                if l_id + 1 == self.settingsWidget.comboBox.currentIndex():
                    self.settingsWidget.comboBox.setCurrentIndex(0)
        except:
            pass

    def initGui(self):
        self.toolButton = self.add_action(
            self.icon_path + 'cut.svg',
            'Cut elements',
            self.run,
            checkable=True
            )
        self.tool.action = self.toolButton

        self.first_start = True

    def rebuildListWidget(self):
        self.settingsWidget.listWidget.clear()
        for l in self.polygonLayers:
            item = QListWidgetItem(l[0].name())
            item.setCheckState(Qt.Unchecked)
            self.settingsWidget.listWidget.addItem(item)

    def rebuildComboBox(self):
        self.settingsWidget.comboBox.clear()
        self.settingsWidget.comboBox.addItem(None)
        for l in self.polygonLayers:
            self.settingsWidget.comboBox.addItem(l[0].name())

    def removeLayer(self, layer):
        i = 0
        for l in self.polygonLayers:
            if l[1] == layer:
                self.polygonLayers.pop(i)
            i += 1

    def run(self):
        if self.toolButton.isChecked():
            self.iface.mapCanvas().setMapTool(self.tool)
            self.settingsWidget.show()
        else:
            self.iface.mapCanvas().unsetMapTool(self.tool)
            self.settingsWidget.hide()

    def setPolygonLayers(self):
        self.polygonLayers = []
        for l in self.qgsProject.mapLayers():
            layer = self.qgsProject.mapLayer(l)
            if  layer.type() == 0: # 0 = Vector layer
                if layer.geometryType() == 2: # 2 = Polygon layer
                    self.polygonLayers.append([layer,layer.id()])
                    
    def tr(self, message):
        return QCoreApplication.translate('Cutter', message)

class Cutter_geometry():
    geometry = None
    geoemtry_crs = None

class addPolygon(QgsMapTool):
    cut = pyqtSignal()
    deact = pyqtSignal()
    def __init__(self, iface, action, geometryClass):
        self.canvas = iface.mapCanvas()
        self.iface = iface
        self.action = action
        self.geometryClass = geometryClass

        obj_color = QColor(254,0,0)
        obj_color_alpha = QColor(254,0,0)
        obj_color_alpha.setAlpha(60)
        vert_color = QColor(0, 0, 255)

        QgsMapTool.__init__(self, self.canvas)

        self.rubberBand = QgsRubberBand(self.canvas,QgsWkbTypes.GeometryType(3))
        self.rubberBand.setWidth(1)
        self.rubberBand.setStrokeColor(obj_color)
        self.rubberBand.setFillColor(obj_color_alpha)

        self.rubberBand_click = QgsRubberBand(self.canvas,QgsWkbTypes.GeometryType(3))
        self.rubberBand_click.setWidth(0)
        self.rubberBand_click.setFillColor(obj_color_alpha)

        # snap marker
        self.snap_mark = QgsVertexMarker(self.canvas)
        self.snap_mark.setColor(vert_color)
        self.snap_mark.setPenWidth(2)
        self.snap_mark.setIconType(QgsVertexMarker.ICON_BOX)
        self.snap_mark.setIconSize(10)

        self.points = []

    def activate(self):
        self.action.setChecked(True)
        self.setCursor(Qt.CrossCursor)

    def canvasMoveEvent( self, e ):
        self.snap_mark.hide()
        self.snapPoint = False
        self.snapPoint = self.checkSnapToPoint(e.pos())

        if self.snapPoint[0]:
            self.snap_mark.setCenter(self.snapPoint[1])
            self.snap_mark.show()

        if len(self.points) > 0:
            self.rubberBand.reset(QgsWkbTypes.GeometryType(3))
            point = self.toMapCoordinates(self.canvas.mouseLastXY())   
            temp_points = self.points[:]
            temp_points.append(point)
            polygon = QgsGeometry.fromPolygonXY([temp_points])
            self.rubberBand.setToGeometry(polygon,None)
            self.rubberBand.show()

    def canvasPressEvent (self, e):
        # Left mouse button
        if e.button() == Qt.LeftButton:
            if self.snapPoint[0]:
                point = self.snapPoint[1]
            else:
                point = self.toMapCoordinates(self.canvas.mouseLastXY())

            self.points.append(point)
            polygon = QgsGeometry.fromPolygonXY([self.points])
            self.rubberBand_click.reset(QgsWkbTypes.GeometryType(3))
            self.rubberBand_click.setToGeometry(polygon,None)
            self.rubberBand_click.show()

        # Right mouse button
        if e.button() == Qt.RightButton:
            geometry = QgsGeometry.fromPolygonXY([self.points])
            self.geometryClass.geometry = geometry
            self.cut.emit()
            self.reset()

    def checkSnapToPoint(self, point):
        snapped = False
        snap_point = self.toMapCoordinates(point)
        snapper = self.canvas.snappingUtils()
        snapMatch = snapper.snapToMap(point)
        if snapMatch.hasVertex():
            snap_point = snapMatch.point()
            snapped = True
        return snapped, snap_point

    def deactivate(self):
        self.action.setChecked(False)
        self.reset()
        self.deact.emit()

    def keyPressEvent (self,e):
        if e.key() == Qt.Key_Escape:
            self.reset()

    def reset(self):
        self.rubberBand_click.reset(QgsWkbTypes.GeometryType(3))
        self.rubberBand.reset(QgsWkbTypes.GeometryType(3))
        self.snap_mark.hide()
        self.points = []
