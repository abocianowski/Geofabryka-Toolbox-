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
from ..dialogs.painter_settingsPanel import settingsPanel

from PyQt5.QtCore import QSettings, QCoreApplication, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QCursor
from PyQt5.QtWidgets import  QToolButton, QMenu, QAction, QListWidgetItem, QMessageBox

from qgis.gui import QgsMapTool, QgsVertexMarker, QgsRubberBand
from qgis.core import QgsWkbTypes, QgsGeometry, QgsProject, QgsFeature, QgsVectorLayerEditUtils, QgsVectorLayerUtils

class Painter:
    def __init__(self, iface, plugin_dir, toolbar, icon_path):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.toolsToolbar = toolbar
        self.icon_path = icon_path

        self.canvas = iface.mapCanvas()

        self.qgsProject = QgsProject.instance()
        self.qgsProject.layersAdded.connect(self.layerWasAdded)
        self.qgsProject.layersWillBeRemoved.connect(self.layerWasRemoved)
        
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'painter_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        self.actions = []

        self.geometry_class = Painters_geometry()

        self.tool = addPolygon(self.iface, None, self.geometry_class)
        self.tool.pos.connect(self.clickTool)
        self.tool.res.connect(self.reset)
        
        self.settingsWidget = settingsPanel()
        self.settingsWidget.checkBox_allLayers.stateChanged.connect(self.clickAllLayers)
        self.settingsWidget.checkBox_onlyVisible.stateChanged.connect(self.clickOnlyVisibleLayers)
        self.settingsWidget.checkBox_selectedByUser.stateChanged.connect(self.clickSelectedByUser)
        self.settingsWidget.checkBox_askTargetLayer.stateChanged.connect(self.clickAskTargetLayer)
        self.settingsWidget.listWidget.setEnabled(False)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.settingsWidget)
        self.settingsWidget.label_target_layer.setEnabled(False)
        self.settingsWidget.comboBox_targetLayer.setEnabled(False)
        self.settingsWidget.showButton.setEnabled(False)
        self.settingsWidget.hideButton.setEnabled(False)
        self.settingsWidget.showButton.clicked.connect(self.clickShowAll)
        self.settingsWidget.hideButton.clicked.connect(self.clickHideAll)
        self.settingsWidget.checkBoxPolygon.stateChanged.connect(self.rebuildListWidget)
        self.settingsWidget.checkBoxLine.stateChanged.connect(self.rebuildListWidget)
        self.settingsWidget.hide()

        icon = QIcon(self.icon_path + 'selectAll.svg')
        self.settingsWidget.showButton.setIcon(icon)

        icon = QIcon(self.icon_path + 'hideAll.svg')
        self.settingsWidget.hideButton.setIcon(icon)

        icon = QIcon(self.icon_path + 'geofabryka.png')
        self.settingsWidget.pushButton_geofabryka.setIcon(icon)

        self.tool.deact.connect(self.settingsWidget.hide)

        obj_color = QColor(254,0,0)
        obj_color_alpha = QColor(254,0,0)
        obj_color_alpha.setAlpha(60)

        self.rubberBand = QgsRubberBand(self.canvas,QgsWkbTypes.GeometryType(3))
        self.rubberBand.setWidth(1)
        self.rubberBand.setStrokeColor(obj_color)
        self.rubberBand.setFillColor(obj_color_alpha)

        self.setLayers()
        self.rebuildListWidget()
        self.rebuildComboBox()

        self.first_start = None
        
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

        self.actions.append(action)

        return action

    def addFeature(self, layer):
        feature = QgsVectorLayerUtils.createFeature(layer)
        feature.setGeometry(self.target_geom)
        layer.addFeature(feature)
        self.addTopologicalPoints(self.target_geom)
        self.canvas.refresh()
        self.reset()
        self.iface.openFeatureForm(layer, feature, False)

    def addMenu(self):
        menu = QMenu()
        for i in self.layers:
            if i[2] == 2:
                action = menu.addAction(i[0].name())
                action.triggered.connect(lambda ch, i=i: self.addFeature(i[0]))
        menu.exec_(QCursor.pos())
        self.reset()

    def addTopologicalPoints(self, geometry):
        geometry = QgsGeometry(geometry)
        layers = self.getLayers(2)

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

    def clickAllLayers(self):
        if self.settingsWidget.checkBox_allLayers.isChecked():
            self.settingsWidget.checkBox_onlyVisible.setChecked(False) 
            self.settingsWidget.checkBox_selectedByUser.setChecked(False) 
            self.settingsWidget.listWidget.setEnabled(False)

    def clickAskTargetLayer(self):
        if self.settingsWidget.checkBox_askTargetLayer.isChecked():
            self.settingsWidget.label_target_layer.setEnabled(False)
            self.settingsWidget.comboBox_targetLayer.setEnabled(False)

        else:
            self.settingsWidget.label_target_layer.setEnabled(True)
            self.settingsWidget.comboBox_targetLayer.setEnabled(True)

    def clickOnlyVisibleLayers(self):
        if self.settingsWidget.checkBox_onlyVisible.isChecked():
            self.settingsWidget.checkBox_allLayers.setChecked(False) 
            self.settingsWidget.checkBox_selectedByUser.setChecked(False)
            self.settingsWidget.listWidget.setEnabled(False)

    def clickSelectedByUser(self):
        if self.settingsWidget.checkBox_selectedByUser.isChecked():
            self.settingsWidget.checkBox_allLayers.setChecked(False) 
            self.settingsWidget.checkBox_onlyVisible.setChecked(False) 
            self.settingsWidget.listWidget.setEnabled(True)
            self.settingsWidget.showButton.setEnabled(True)
            self.settingsWidget.hideButton.setEnabled(True)
        else:
            self.settingsWidget.listWidget.setEnabled(False)
            self.settingsWidget.showButton.setEnabled(False)
            self.settingsWidget.hideButton.setEnabled(False)

    def clickShowAll(self):
        for i in range(0, 10000):
            try:
                item = self.settingsWidget.listWidget.item(i)
                item.setCheckState(2)
            except AttributeError:
                break

    def clickHideAll(self):
        for i in range(0, 10000):
            try:
                item = self.settingsWidget.listWidget.item(i)
                item.setCheckState(0)
            except AttributeError:
                break
            
    def clickTool(self):
        self.rubberBand.reset(QgsWkbTypes.GeometryType(3))
        click_point_geom = QgsGeometry.fromPointXY(self.geometry_class.geometry)
        buffer_geom = click_point_geom.buffer(self.settingsWidget.spinBox_searchArea.value(),20)

        lines_layers = self.getLayers(1)
        polygons_layers = self.getLayers(2)
        len_line_layers = 0
        len_polygon_layers = 0

        try:
            len_line_layers += len(lines_layers)
        except TypeError:
            pass

        try:
            len_polygon_layers += len(polygons_layers)
        except TypeError:
            pass

        if len_polygon_layers == 0 and len_line_layers == 0:
            QMessageBox.warning(None,'Missing restrictive layers', 'Select one of the settings')
            return

        self.target_geom = None

        # Polygon layers
        if self.settingsWidget.checkBoxPolygon.isChecked() and len_polygon_layers > 0:
            for l in polygons_layers:
                poly_layer = l[0]
                
                for f in poly_layer.getFeatures(buffer_geom.boundingBox()):
                    f_geom = f.geometry()
                    if f_geom.intersects(click_point_geom):
                        QMessageBox.warning(None,'No space to fill', 'No space to fill, choose a different location')
                        return
                        
                    if f_geom.intersects(buffer_geom):
                        buffer_geom = buffer_geom.difference(f_geom)

                if not poly_layer.isEditable():
                    poly_layer.startEditing()
                
                for part in buffer_geom.parts():
                    part_wkt = part.asWkt()
                    part_geom = QgsGeometry.fromWkt(part_wkt)
                    if part_geom.intersects(click_point_geom):
                        target_geom = part_geom
                        break 

        # Line layers
        if self.settingsWidget.checkBoxLine.isChecked():
            for l in lines_layers:
                line_layer = l[0]
                features = [i.geometry() for i in line_layer.getFeatures(buffer_geom.boundingBox())]
                buffer_geom_linestring = self.polygon2Linestring(buffer_geom)
                if buffer_geom_linestring != None:
                    features.append(buffer_geom_linestring)
                features_unary_geom = QgsGeometry.unaryUnion(features)
                features_unary_geom_parts = [QgsGeometry.fromWkt(i.asWkt()) for i in features_unary_geom.parts()]
                features_polygonize = QgsGeometry.polygonize(features_unary_geom_parts)

                for part in features_polygonize.parts():
                    part_geom = QgsGeometry.fromWkt(part.asWkt())
                    if part_geom.intersects(click_point_geom):
                        if target_geom == None:
                            target_geom = part_geom
                        else:
                            target_geom = target_geom.intersection(part_geom)
                        break 

        target_geom.convertGeometryCollectionToSubclass(2)

        for part in target_geom.parts():
            if part != None:
                part_geom = QgsGeometry.fromWkt(part.asWkt())
                if part_geom.intersects(click_point_geom):
                    self.target_geom = part_geom

        if self.target_geom != None:
            self.rubberBand.setToGeometry(self.target_geom,None)

            if self.settingsWidget.checkBox_askTargetLayer.isChecked():
                self.addMenu()
            else:
                t_layer = self.getTargetLayer()

                if t_layer == None:
                    QMessageBox.warning(None,'Missing target layer', 'Select one of the settings')
                    return
                else:
                    self.addFeature(t_layer)

    def getLayerListId(self, layerid, layer_type = 'All'):
        if layer_type == 'All':
            i = 0
            for l in self.layers:
                if l[1] == layerid:
                    return i
                i += 1

        elif layer_type == 'Poly':
            i = 0
            for l in self.layers:
                if l[0].geometryType() == 2:
                    if l[1] == layerid:
                        return i
                    i += 1

    def getLayers(self, geometry_type):
        layers = []

        # All Layers
        if self.settingsWidget.checkBox_allLayers.isChecked():
            for l in self.qgsProject.mapLayers():
                layer = self.qgsProject.mapLayer(l)
                if layer.type() == 0: # 0 = vector layer
                    if layer.geometryType() == geometry_type:
                        layers.append([layer,layer.id()])
            return layers

        # Visible Layers
        elif self.settingsWidget.checkBox_onlyVisible.isChecked():
            for l in self.canvas.layers():
                layer = l
                if layer.type() == 0: # 0 = vector layer
                    if layer.geometryType() == geometry_type:
                        layers.append([layer,layer.id()])
            return layers

        elif self.settingsWidget.checkBox_selectedByUser.isChecked():
            for i in range(0, len(self.layers)):
                item = self.settingsWidget.listWidget.item(i)
                if item.checkState() == 2:
                    layer = self.layers[i][0]
                    if layer.geometryType() == geometry_type:
                        layers.append([layer,layer.id()])
            return layers

    def getTargetLayer(self):
        idx = self.settingsWidget.comboBox_targetLayer.currentIndex()
        layers = [l[0] for l in self.layers if l[2] == 2]
        if idx != 0:
            layer = layers[idx -1]
            return layer
            
    def initGui(self):
        self.toolButton = self.add_action(
            self.icon_path + 'paint.svg',
            'Fill the empty spaces',
            self.run,
            checkable=True
            )
        self.tool.action = self.toolButton

        self.first_start = True

    def layersTypeChanged(self):
        if self.settingsWidget.checkBoxPolygon.isChecked():
            poly_checked = False
        else:
            poly_checked = True

        if self.settingsWidget.checkBoxLine.isChecked():
            line_checked = False
        else:
            line_checked = True

        for i in range(0,len(self.layers)):
            item = self.settingsWidget.listWidget.item(i)
            if self.layers[i][2] == 1:
                item.setHidden (line_checked)
            elif self.layers[i][2] == 2:
                item.setHidden (poly_checked)

    def layerWasAdded(self,layers):
        if self.settingsWidget.checkBoxPolygon.isChecked():
            poly_checked = False
        else:
            poly_checked = True

        if self.settingsWidget.checkBoxLine.isChecked():
            line_checked = False
        else:
            line_checked = True

        for l in layers:
            if  l.type() == 0:
                if l.geometryType() == 1 or l.geometryType() == 2:
                    self.layers.append([l,l.id(),l.geometryType()])

                    item = QListWidgetItem(l.name())
                    item.setCheckState(Qt.Unchecked)
                    self.settingsWidget.listWidget.addItem(item)

                    if l.geometryType() == 1:
                        item.setHidden (line_checked)
                    elif l.geometryType() == 2:
                        item.setHidden (poly_checked)    
                        self.settingsWidget.comboBox_targetLayer.addItem(l.name())                  

    def layerWasRemoved(self, layers):
        for l in layers:
            l_id = self.getLayerListId(l)
            l_trg_combo_id = self.getLayerListId(l, 'Poly')

            try:
                item = self.settingsWidget.listWidget.takeItem(l_id)
                if l_trg_combo_id + 1 == self.settingsWidget.comboBox_targetLayer.currentIndex():
                    self.settingsWidget.comboBox_targetLayer.setCurrentIndex(0)
            except TypeError:
                pass
                
            self.removeLayer(l)

            try:
                self.settingsWidget.comboBox_targetLayer.removeItem(l_trg_combo_id + 1 )
            except TypeError:
                pass
        
    def polygon2Linestring(self, poly_geom):
        p_geom = None
        geom_parts = [p for p in poly_geom.parts()]

        for p in geom_parts:
            p_geom = QgsGeometry.fromWkt(p.asWkt())
            p_geom = QgsGeometry.fromPolyline([p for p in p_geom.vertices()])

        return p_geom
            
    def rebuildComboBox(self):
        self.settingsWidget.comboBox_targetLayer.clear()
        self.settingsWidget.comboBox_targetLayer.addItem(None)
        for l in self.layers:
            if l[0].geometryType() == 2:
                self.settingsWidget.comboBox_targetLayer.addItem(l[0].name())

    def rebuildListWidget(self):
        self.settingsWidget.listWidget.clear()
        if self.settingsWidget.checkBoxPolygon.isChecked():
            poly_checked = False
        else:
            poly_checked = True

        if self.settingsWidget.checkBoxLine.isChecked():
            line_checked = False
        else:
            line_checked = True

        for l in self.layers:
            item = QListWidgetItem(l[0].name())
            item.setCheckState(Qt.Unchecked)
            self.settingsWidget.listWidget.addItem(item)

            if l[2] == 1:
                item.setHidden (line_checked)
            elif l[2] == 2:
                item.setHidden (poly_checked)

    def removeLayer(self, layer):
        i = 0
        for l in self.layers:
            if l[1] == layer:
                self.layers.pop(i)
            i += 1
            
    def reset(self):
        self.rubberBand.hide()

    def run(self):
        if self.toolButton.isChecked():
            self.iface.mapCanvas().setMapTool(self.tool)
            self.settingsWidget.show()
        else:
            self.iface.mapCanvas().unsetMapTool(self.tool)
            self.settingsWidget.hide()
    
    def setLayers(self):
        self.layers = []
        for l in self.qgsProject.mapLayers():
            layer = self.qgsProject.mapLayer(l)
            if  layer.type() == 0: # 0 = vector layer
                if layer.geometryType() in [1,2]:
                    self.layers.append([layer,layer.id(),layer.geometryType()])

    def tr(self, message):
        return QCoreApplication.translate('Painter', message)

    def unload(self):
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Painter'),
                action)
            self.iface.removeToolBarIcon(action)

class Painters_geometry():
    geometry = None        

class addPolygon(QgsMapTool):
    pos = pyqtSignal()
    deact = pyqtSignal()
    res = pyqtSignal()
    def __init__(self, iface, action, geometry_class):
        self.canvas = iface.mapCanvas()
        self.iface = iface
        self.action = action
        self.geometry_class = geometry_class

        obj_color = QColor(254,0,0)
        obj_color_alpha = QColor(254,0,0)
        obj_color_alpha.setAlpha(60)
        vert_color = QColor(0, 0, 255)

        QgsMapTool.__init__(self, self.canvas)

        # snap marker
        self.snap_mark = QgsVertexMarker(self.canvas)
        self.snap_mark.setColor(vert_color)
        self.snap_mark.setPenWidth(2)
        self.snap_mark.setIconType(QgsVertexMarker.ICON_BOX)
        self.snap_mark.setIconSize(10)

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
            point = self.snapPoint[1]
        else:
            point = self.toMapCoordinates(self.canvas.mouseLastXY())

    def canvasPressEvent (self, e):
        if e.button() == Qt.LeftButton:
            if self.snapPoint[0]:
                point = self.snapPoint[1]
            else:
                point = self.toMapCoordinates(self.canvas.mouseLastXY())

            self.geometry_class.geometry = point
            self.pos.emit()

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
        self.snap_mark.hide()
        self.res.emit()