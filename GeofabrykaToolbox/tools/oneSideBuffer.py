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
from ..dialogs.buffer_settingsPanel import settingsPanel

from PyQt5 import QtWidgets
from PyQt5.QtCore import QSettings, QCoreApplication, Qt, pyqtSignal
from PyQt5.QtGui import QIcon, QColor, QCursor
from PyQt5.QtWidgets import QMenu, QAction, QToolTip

from qgis.gui import  QgsMapToolIdentify, QgsRubberBand, QgsVertexMarker
from qgis.core import QgsProject, QgsFeature, QgsGeometry, QgsWkbTypes, QgsVectorLayerEditUtils, QgsPolygon, QgsVectorLayerUtils

class OneSideBuffer:
    def __init__(self, iface, plugin_dir, toolbar, icon_path):
        self.iface = iface
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
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.settingsWidget)
        self.settingsWidget.hide()
        self.tool = OneSideBuffer_tool(self.iface,None,self.plugin_dir, self.settingsWidget.spinBox_tolerance)
        self.tool.deact.connect(self.settingsWidget.hide)
        self.first_start = None
        
        icon = QIcon(self.icon_path + 'geofabryka.png')
        self.settingsWidget.pushButton_geofabryka.setIcon(icon)
        
        self.initGui()

    def tr(self, message):
        return QCoreApplication.translate('One Side Buffer', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            toolbar,
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
                toolbar.addAction(action)

            if checkable:
                action.setCheckable(True)
                
            if checked:
                action.setChecked(1)

            if shortcut:
                action.setShortcut(shortcut)

            return action

    def initGui(self):
        self.mainButton = self.add_action(
            self.icon_path + 'buffer.svg',
            text=self.tr(u'Add Buffer'),
            callback=self.run,
            parent=self.iface.mainWindow(),
            toolbar = self.toolsToolbar,
            enabled_flag = True,
            checkable= True)

        self.tool.action = self.mainButton

        self.first_start = True

    def run(self):
        if self.mainButton.isChecked():
            self.iface.mapCanvas().setMapTool(self.tool)
            self.settingsWidget.show()
        else:
            self.iface.mapCanvas().unsetMapTool(self.tool)
            self.settingsWidget.hide()

class OneSideBuffer_tool(QgsMapToolIdentify):
    deact = pyqtSignal()
    def __init__(self, iface, action, plugin_dir, spinbox):
        self.canvas = iface.mapCanvas()
        self.iface = iface
        self.action = action
        self.icon_path = os.path.join(plugin_dir,"icons")
        self.spinbox = spinbox

        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.GeometryType(3))
        self.rubberBand.setWidth(3)
        self.rubberBand.setStrokeColor(QColor(254,0,0))

        self.snap_mark = QgsVertexMarker(self.canvas)
        self.snap_mark.setColor(QColor(0, 0, 255))
        self.snap_mark.setPenWidth(2)
        self.snap_mark.setIconType(QgsVertexMarker.ICON_BOX)
        self.snap_mark.setIconSize(10)

        QgsMapToolIdentify.__init__(self, self.canvas)

        self.selectFeatureMode = True
        self.firstPointMode = False
        self.secondPointMode = False
        self.objectSizeMode = False

        self.firstPoint_locate = None
        self.linestring = None

        self.dist = self.spinbox.value()

        self.canvas.layersChanged.connect(self.setPolygonLayers)

    def activate(self):
        self.setCursor(Qt.CrossCursor)
        self.setPolygonLayers()

    def addMenu(self):
        menu = QMenu()
        self.setPolygonLayers()
        for i in self.getVisibleLayers():
            action = menu.addAction(i.name())
            action.triggered.connect(lambda ch, i=i: self.addFeature(i))
        menu.exec_(QCursor.pos())

    def addFeature(self, dest_layer):
        geometry_canvas = self.geom_poly

        for l in self.getVisibleLayers():
            geometry_canvas = self.getDifferenceGeometry(geometry_canvas, l)

        # dump geom if it s multipart
        geometry_parts = [p for p in geometry_canvas.parts()]
        for part in geometry_parts:
            part_wkt = part.asWkt()
            part_geom = QgsGeometry.fromWkt(part_wkt)

            if part_geom.isGeosValid() == False:
                part_geom = part_geom.makeValid()

            if part_geom.isGeosValid() == True and part_geom.area() > 0.1:
                self.addTopologicalPointsForActiveLayers(part_geom)

                feature = QgsVectorLayerUtils.createFeature(dest_layer)
                feature.setGeometry(part_geom)

                height_col_idx = dest_layer.fields().indexFromName('SZEROKOSC')

                if height_col_idx != -1:
                    feature.setAttribute(height_col_idx, self.dist)

                if not dest_layer.isEditable():
                    dest_layer.startEditing()

                dest_layer.addFeature(feature)

                self.iface.openFeatureForm(dest_layer, feature, False)

    def addTopologicalPointsForActiveLayers(self, geometry):
        geometry = QgsGeometry(geometry)
        layers = self.getVisibleLayers()
        for layer in layers:
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
    
    def calculateSide(self , linestring, point):
        segment = linestring.closestSegmentWithContext(point.asPoint())
        if segment[3] < 0:
            return 2
        else:
            return 1
     
    def canvasMoveEvent(self, e ):
        if self.firstPointMode == True or self.secondPointMode == True:
            self.snapPoint = self.checkSnapToPoint(e.pos())

            if self.snapPoint[0]:
                self.snap_mark.setCenter(self.snapPoint[1])
                self.snap_mark.show()
                self.point = QgsGeometry.fromPointXY (self.snapPoint[1])
            else:
                self.snap_mark.hide()
                self.point = QgsGeometry.fromPointXY (self.toMapCoordinates(e.pos()))

        if self.secondPointMode:
            self.secondPoint_locate = self.linestring.lineLocatePoint(self.point)
            self.output_geom = self.lineSubstring(self.linestring,self.firstPoint_locate,self.secondPoint_locate)

            if self.output_geom != None:
                self.rubberBand.setToGeometry(self.output_geom, None)
                self.rubberBand.show()

        if self.objectSizeMode:
            s_point = QgsGeometry.fromPointXY (self.toMapCoordinates(e.pos()))

            #if round(abs(self.output_geom.distance(s_point) - self.dist),1) >= self.spinbox.value():
            #self.dist = round(self.output_geom.distance(s_point)/self.spinbox.value(),1)
            self.dist = int(self.output_geom.distance(s_point)/self.spinbox.value())
            self.dist = self.dist * self.spinbox.value()
            QToolTip.showText( self.canvas.mapToGlobal( self.canvas.mouseLastXY() ), str(round(self.dist,2)), self.canvas )

            left_or_right = self.calculateSide(self.output_geom, s_point)
            self.geom_poly = self.output_geom.singleSidedBuffer(self.dist,20,left_or_right,2)
            self.rubberBand.setToGeometry(self.geom_poly, None)
            self.rubberBand.show()

    def canvasPressEvent (self, e):
        if e.button() == Qt.LeftButton:
            layerType = getattr(QgsMapToolIdentify,'VectorLayer')
            results = self.identify(e.x(), e.y(), self.TopDownStopAtFirst ,layerType)

            if self.selectFeatureMode:
                if len(results) == 0 or results[0].mLayer not in [l for l in self.polygonLayers]:
                    for l in self.polygonLayers:
                        l.removeSelection()

                elif len(results) > 0:
                    for l in self.polygonLayers:
                        try:
                            l.removeSelection()
                        except:
                            pass
                    self.current_layer = self.cur_lyr = results[0].mLayer
                    self.current_feature = QgsFeature(results[0].mFeature)
                    self.current_layer.select(self.current_feature.id())
                    self.iface.setActiveLayer(self.current_layer)

                    self.selectFeatureMode = False
                    self.firstPointMode = True

            elif self.firstPointMode:
                self.linestring = self.polygon2Linestring(self.current_feature.geometry(), e.pos())
                self.firstPoint_locate = self.linestring.lineLocatePoint(self.point)
                self.firstPointMode = False
                self.secondPointMode = True

            elif self.secondPointMode:
                self.secondPointMode = False
                self.objectSizeMode = True
                self.dist = self.spinbox.value()

            elif self.objectSizeMode:
                self.objectSizeMode = False
                self.addMenu()
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
        self.rubberBand.hide()
        self.deact.emit()

    def getDifferenceGeometry(self, geometry, layer):
        geometry = QgsGeometry(geometry)
        bbox = geometry.boundingBox()

        for f in layer.getFeatures(bbox):
            f_geom = f.geometry()

            if f_geom.isGeosValid() == False:
                f_geom = f_geom.makeValid()

            if f_geom.isGeosValid() == True: 
                if geometry.intersects(f_geom):
                    geometry = geometry.difference(f_geom)

        return geometry

    def getVisibleLayers(self):
        array = []
        root = QgsProject.instance().layerTreeRoot()
        for l in self.polygonLayers:
            node = root.findLayer(l.id())
            if node:
                visible = node.isVisible ()
                if visible:
                    array.append(l)
        return array

    def keyPressEvent (self,e):
        if e.key() == Qt.Key_Escape:
            self.reset()

    def lineSubstring(self, linestring, start, end):
        array = [linestring.lineLocatePoint(QgsGeometry.fromWkt(i.asWkt())) for i in linestring.vertices()]
        one_array = []
        second_array = []
        # 1 Geom
        if start < end:
            one_array.append(start)
            for i in array:
                if i > start and i < end:
                    one_array.append(i)
            one_array.append(end)
        else:
            one_array.append(start)
            for i in array:
                if i > start:
                    one_array.append(i)
            one_array.append(0.0)
            for i in array:
                if i < end and i > 0:
                    one_array.append(i)
            one_array.append(end)

        # 2 Geom
        if start < end:
            second_array.append(end)
            for i in array:
                if i > end:
                    second_array.append(i)
            second_array.append(0.0)
            for i in array:
                if i < start and i > 0:
                    second_array.append(i)
            second_array.append(start)
        else:
            second_array.append(end)
            for i in array:
                if i > end and i < start:
                    second_array.append(i)
            second_array.append(start)

        one_geom = QgsGeometry.fromPolylineXY([linestring.interpolate(i).asPoint() for i in one_array])
        second_geom = QgsGeometry.fromPolylineXY([linestring.interpolate(i).asPoint() for i in second_array])

        if second_geom.length() < one_geom.length():
            self.linestring_rev = True
            return (second_geom)
        else:
            self.linestring_rev = False
            return(one_geom)

    def point2LayerCoordinate(self, pos, layer):
        layer_crs = layer.crs().authid()
        canvas_crs = self.canvas.mapSettings().destinationCrs().authid()

        point = self.toMapCoordinates(pos)
        point = QgsGeometry.fromPointXY(point)
        point = self.geometryCrs2Crs(point, canvas_crs, layer_crs)
        return point

    def polygon2Linestring(self, poly_geom, pos):
        geom_parts = [p for p in poly_geom.parts()]
        pos_geom = QgsGeometry.fromPointXY (self.toMapCoordinates(pos))

        cur_dist = None
        cur_geom = None
        for p in geom_parts:
            p_geom = QgsGeometry.fromWkt(p.asWkt())
            p_geom = QgsGeometry.fromPolyline([p for p in p_geom.vertices()])
            p_geom_dist = p_geom.distance(pos_geom)

            if cur_dist == None or p_geom_dist < cur_dist:
                cur_geom = p_geom
                cur_dist = p_geom_dist

        return cur_geom

    def reset(self):
        self.current_layer.removeSelection()
        self.selectFeatureMode = True
        self.firstPointMode = False
        self.secondPointMode = False
        self.firstPoint_locate = None
        self.linestring = None
        self.objectSizeMode = False
        self.snap_mark.hide()
        self.rubberBand.hide()
        self.dist = self.spinbox.value()

    def setPolygonLayers(self):
        self.polygonLayers = []
        for l in QgsProject.instance().mapLayers():
            layer = QgsProject.instance().mapLayer(l)
            if  layer.type() == 0: # 0 = Vector layer
                if layer.geometryType() == 2: # 2 = Polygon layer
                    self.polygonLayers.append(layer)
