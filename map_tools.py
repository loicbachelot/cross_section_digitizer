# -*- coding: utf-8 -*-
"""
Map tools for the CrossSectionDigitizer plugin
"""

from qgis.PyQt.QtCore import Qt, QPoint
from qgis.PyQt.QtGui import QColor, QPen, QBrush
from qgis.PyQt.QtWidgets import QGraphicsEllipseItem
from qgis.gui import QgsMapTool, QgsMapToolEmitPoint, QgsRubberBand, QgsVertexMarker
from qgis.core import QgsWkbTypes, QgsPointXY


class DigitizeMapTool(QgsMapToolEmitPoint):
    """Map tool for digitizing points on cross-section images"""
    
    def __init__(self, canvas, callback, point_color=QColor(255, 0, 0)):
        super().__init__(canvas)
        self.callback = callback
        self.point_color = point_color
        self.points = []
        self.markers = []
        
    def canvasPressEvent(self, event):
        """Handle canvas press events"""
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.add_point(point)
            self.callback(point)
            
    def add_point(self, point):
        """Add a point to the visual display"""
        self.points.append(point)
        
        # Create a vertex marker (plus sign)
        marker = QgsVertexMarker(self.canvas())
        marker.setCenter(point)
        marker.setColor(self.point_color)
        marker.setIconSize(8)
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setPenWidth(2)
        self.markers.append(marker)
        
    def clear_points(self):
        """Clear all points"""
        self.points.clear()
        for marker in self.markers:
            self.canvas().scene().removeItem(marker)
        self.markers.clear()
        
    def set_point_color(self, color):
        """Update color of all markers"""
        self.point_color = color
        for marker in self.markers:
            marker.setColor(color)
            
    def deactivate(self):
        """Clean up when tool is deactivated"""
        super().deactivate()
        self.clear_points()


class ReferencePointTool(QgsMapToolEmitPoint):
    """Map tool for setting reference points"""
    
    def __init__(self, canvas, callback, point_type, point_color=QColor(0, 255, 0)):
        super().__init__(canvas)
        self.callback = callback
        self.point_type = point_type
        self.point_color = point_color
        self.marker = None
        
    def canvasPressEvent(self, event):
        """Handle canvas press events"""
        if event.button() == Qt.LeftButton:
            point = self.toMapCoordinates(event.pos())
            self.set_reference_point(point)
            self.callback(point, self.point_type)
            
    def set_reference_point(self, point):
        """Set the reference point"""
        # Remove previous marker
        if self.marker:
            self.canvas().scene().removeItem(self.marker)
            
        # Create new marker
        self.marker = QgsVertexMarker(self.canvas())
        self.marker.setCenter(point)
        self.marker.setColor(self.point_color)
        self.marker.setIconSize(10)
        self.marker.setIconType(QgsVertexMarker.ICON_CROSS)
        self.marker.setPenWidth(3)
        
    def clear_point(self):
        """Clear the reference point"""
        if self.marker:
            self.canvas().scene().removeItem(self.marker)
            self.marker = None
            
    def deactivate(self):
        """Clean up when tool is deactivated"""
        super().deactivate()
        self.clear_point()


class PointMarkerManager:
    """Manages visual markers for digitized points"""
    
    def __init__(self, canvas):
        self.canvas = canvas
        self.series_markers = {}  # {series_name: [markers]}
        self.georef_markers = []  # For georeferencing points
        self.reference_markers = {}  # For reference points
        
    def add_data_point(self, series_name, point, is_active=True):
        """Add a marker for a data series point"""
        if series_name not in self.series_markers:
            self.series_markers[series_name] = []
            
        color = QColor(0, 0, 0) if is_active else QColor(128, 128, 128)
        
        marker = QgsVertexMarker(self.canvas)
        marker.setCenter(point)
        marker.setColor(color)
        marker.setIconSize(6)
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setPenWidth(2)
        
        self.series_markers[series_name].append(marker)
        
    def add_georef_point(self, point, point_type):
        """Add a marker for georeferencing points"""
        marker = QgsVertexMarker(self.canvas)
        marker.setCenter(point)
        marker.setColor(QColor(255, 0, 0))  # Red
        marker.setIconSize(8)
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setPenWidth(3)
        
        self.georef_markers.append(marker)
        
    def add_reference_point(self, point, ref_type):
        """Add a marker for reference points"""
        if ref_type in self.reference_markers:
            # Remove old marker
            self.canvas.scene().removeItem(self.reference_markers[ref_type])
            
        color_map = {
            'origin': QColor(0, 255, 0),    # Green
            'x_ref': QColor(0, 0, 255),     # Blue  
            'y_ref': QColor(255, 165, 0)    # Orange
        }
        
        marker = QgsVertexMarker(self.canvas)
        marker.setCenter(point)
        marker.setColor(color_map.get(ref_type, QColor(0, 255, 0)))
        marker.setIconSize(10)
        marker.setIconType(QgsVertexMarker.ICON_CROSS)
        marker.setPenWidth(3)
        
        self.reference_markers[ref_type] = marker
        
    def update_series_colors(self, active_series):
        """Update colors based on active series"""
        for series_name, markers in self.series_markers.items():
            is_active = (series_name == active_series)
            color = QColor(0, 0, 0) if is_active else QColor(128, 128, 128)
            
            for marker in markers:
                marker.setColor(color)
                
    def clear_series(self, series_name):
        """Clear all markers for a series"""
        if series_name in self.series_markers:
            for marker in self.series_markers[series_name]:
                self.canvas.scene().removeItem(marker)
            del self.series_markers[series_name]
            
    def clear_georef_points(self):
        """Clear all georeferencing markers"""
        for marker in self.georef_markers:
            self.canvas.scene().removeItem(marker)
        self.georef_markers.clear()
        
    def clear_reference_points(self):
        """Clear all reference markers"""
        for marker in self.reference_markers.values():
            self.canvas.scene().removeItem(marker)
        self.reference_markers.clear()
        
    def clear_all(self):
        """Clear all markers"""
        # Clear series markers
        for markers in self.series_markers.values():
            for marker in markers:
                self.canvas.scene().removeItem(marker)
        self.series_markers.clear()
        
        # Clear georef markers
        self.clear_georef_points()
        
        # Clear reference markers
        self.clear_reference_points()


class CoordinateTransform:
    """Helper class for coordinate transformations"""
    
    def __init__(self):
        self.reference_points = {}
        self.reference_values = {}
        
    def set_reference_point(self, point_type, pixel_coords, real_coords=None):
        """Set a reference point
        
        Args:
            point_type: 'origin', 'x_ref', or 'y_ref'
            pixel_coords: (x, y) pixel coordinates
            real_coords: (x, y) real world coordinates (for origin point)
        """
        self.reference_points[point_type] = pixel_coords
        if real_coords:
            self.reference_values[point_type] = real_coords
            
    def set_reference_value(self, point_type, value):
        """Set reference value for x_ref or y_ref points
        
        Args:
            point_type: 'x_ref' or 'y_ref'  
            value: reference coordinate value
        """
        self.reference_values[point_type] = value
        
    def pixel_to_real(self, pixel_x, pixel_y):
        """Convert pixel coordinates to real coordinates
        
        Args:
            pixel_x, pixel_y: pixel coordinates
            
        Returns:
            (real_x, real_y) or None if transformation not possible
        """
        if not self.is_calibrated():
            return None
            
        # Get reference points
        origin_px, origin_py = self.reference_points['origin']
        x_ref_px, x_ref_py = self.reference_points['x_ref']
        y_ref_px, y_ref_py = self.reference_points['y_ref']
        
        # Get reference values
        origin_x, origin_y = self.reference_values['origin']
        x_ref_val = self.reference_values['x_ref']
        y_ref_val = self.reference_values['y_ref']
        
        # Calculate scale factors
        x_scale = (x_ref_val - origin_x) / (x_ref_px - origin_px) if x_ref_px != origin_px else 1
        y_scale = (y_ref_val - origin_y) / (y_ref_py - origin_py) if y_ref_py != origin_py else 1
        
        # Transform coordinates
        real_x = origin_x + (pixel_x - origin_px) * x_scale
        real_y = origin_y + (pixel_y - origin_py) * y_scale
        
        return (real_x, real_y)
        
    def is_calibrated(self):
        """Check if transformation is properly calibrated"""
        required_points = ['origin', 'x_ref', 'y_ref']
        required_values = ['origin', 'x_ref', 'y_ref']
        
        return (all(pt in self.reference_points for pt in required_points) and
                all(val in self.reference_values for val in required_values))
                
    def clear(self):
        """Clear all reference points and values"""
        self.reference_points.clear()
        self.reference_values.clear()


class CoordinateTransform:
    """Helper class for coordinate transformations"""
    
    def __init__(self):
        self.reference_points = {}
        self.reference_values = {}
        
    def set_reference_point(self, point_type, pixel_coords, real_coords=None):
        """Set a reference point
        
        Args:
            point_type: 'origin', 'x_ref', or 'y_ref'
            pixel_coords: (x, y) pixel coordinates
            real_coords: (x, y) real world coordinates (for origin point)
        """
        self.reference_points[point_type] = pixel_coords
        if real_coords:
            self.reference_values[point_type] = real_coords
            
    def set_reference_value(self, point_type, value):
        """Set reference value for x_ref or y_ref points
        
        Args:
            point_type: 'x_ref' or 'y_ref'  
            value: reference coordinate value
        """
        self.reference_values[point_type] = value
        
    def pixel_to_real(self, pixel_x, pixel_y):
        """Convert pixel coordinates to real coordinates
        
        Args:
            pixel_x, pixel_y: pixel coordinates
            
        Returns:
            (real_x, real_y) or None if transformation not possible
        """
        if not self.is_calibrated():
            return None
            
        # Get reference points
        origin_px, origin_py = self.reference_points['origin']
        x_ref_px, x_ref_py = self.reference_points['x_ref']
        y_ref_px, y_ref_py = self.reference_points['y_ref']
        
        # Get reference values
        origin_x, origin_y = self.reference_values['origin']
        x_ref_val = self.reference_values['x_ref']
        y_ref_val = self.reference_values['y_ref']
        
        # Calculate scale factors
        x_scale = (x_ref_val - origin_x) / (x_ref_px - origin_px) if x_ref_px != origin_px else 1
        y_scale = (y_ref_val - origin_y) / (y_ref_py - origin_py) if y_ref_py != origin_py else 1
        
        # Transform coordinates
        real_x = origin_x + (pixel_x - origin_px) * x_scale
        real_y = origin_y + (pixel_y - origin_py) * y_scale
        
        return (real_x, real_y)
        
    def is_calibrated(self):
        """Check if transformation is properly calibrated"""
        required_points = ['origin', 'x_ref', 'y_ref']
        required_values = ['origin', 'x_ref', 'y_ref']
        
        return (all(pt in self.reference_points for pt in required_points) and
                all(val in self.reference_values for val in required_values))
                
    def clear(self):
        """Clear all reference points and values"""
        self.reference_points.clear()
        self.reference_values.clear()