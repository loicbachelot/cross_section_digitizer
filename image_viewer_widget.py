# -*- coding: utf-8 -*-
"""
Image viewer widget for cross-section digitizing
Inspired by QGIS Georeferencer tool
"""

from qgis.PyQt.QtCore import Qt, QPointF, QRectF, pyqtSignal, QSizeF, QSize
from qgis.PyQt.QtGui import (QPixmap, QPen, QBrush, QColor, QTransform, 
                            QWheelEvent, QPainter, QCursor, QIcon)
from qgis.PyQt.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QToolBar,
                                QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
                                QAction, QLabel, QGraphicsEllipseItem, QGraphicsLineItem,
                                QSizePolicy, QGraphicsItem)
import os


class CrossGraphicsItem(QGraphicsItem):
    """Custom graphics item for cross markers"""
    
    def __init__(self, center, size=8, color=QColor(255, 0, 0), pen_width=2):
        super().__init__()
        self.center = center
        self.size = size
        self.color = color
        self.pen_width = pen_width
        self.setPos(center)
        self.setZValue(1000)  # Always on top
        
    def boundingRect(self):
        half_size = self.size / 2.0
        return QRectF(-half_size - self.pen_width, -half_size - self.pen_width,
                      self.size + 2 * self.pen_width, self.size + 2 * self.pen_width)
    
    def paint(self, painter, option, widget):
        pen = QPen(self.color, self.pen_width)
        painter.setPen(pen)
        
        half_size = self.size / 2.0
        # Draw cross
        painter.drawLine(QPointF(-half_size, 0), QPointF(half_size, 0))
        painter.drawLine(QPointF(0, -half_size), QPointF(0, half_size))


class ImageGraphicsView(QGraphicsView):
    """Custom QGraphicsView for image display and interaction"""
    
    # Signals
    mousePositionChanged = pyqtSignal(QPointF)  # Emits image coordinates
    mouseClicked = pyqtSignal(QPointF, int)  # Emits image coordinates and button
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup view properties
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Interaction modes
        self.pan_mode = False
        self.digitize_mode = False
        
        # For panning
        self._pan_start_pos = None
        
        # Crosshair lines for digitizing
        self.h_line = None
        self.v_line = None
        self.crosshair_visible = False
        
    def create_crosshair_lines(self):
        """Create crosshair lines for digitizing mode"""
        if not self.h_line:
            pen = QPen(QColor(128, 128, 128), 0.5, Qt.DashLine)
            self.h_line = self.scene().addLine(0, 0, 0, 0, pen)
            self.v_line = self.scene().addLine(0, 0, 0, 0, pen)
            self.h_line.setZValue(999)  # Below markers but above image
            self.v_line.setZValue(999)
            self.h_line.hide()
            self.v_line.hide()
            
    def update_crosshair(self, scene_pos):
        """Update crosshair position"""
        if self.digitize_mode and self.h_line and self.v_line:
            # Get scene rect bounds
            rect = self.sceneRect()
            
            # Update horizontal line
            self.h_line.setLine(rect.left(), scene_pos.y(), rect.right(), scene_pos.y())
            
            # Update vertical line
            self.v_line.setLine(scene_pos.x(), rect.top(), scene_pos.x(), rect.bottom())
            
            if not self.crosshair_visible:
                self.h_line.show()
                self.v_line.show()
                self.crosshair_visible = True
        elif self.h_line and self.v_line and self.crosshair_visible:
            self.h_line.hide()
            self.v_line.hide()
            self.crosshair_visible = False
        
    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        # Get the zoom factor
        zoom_in_factor = 1.15
        zoom_out_factor = 1.0 / zoom_in_factor
        
        # Save the scene pos
        old_pos = self.mapToScene(event.pos())
        
        # Zoom
        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor
            
        self.scale(zoom_factor, zoom_factor)
        
        # Get the new position
        new_pos = self.mapToScene(event.pos())
        
        # Move scene to old position
        delta = new_pos - old_pos
        self.translate(delta.x(), delta.y())
        
    def mousePressEvent(self, event):
        """Handle mouse press events"""
        scene_pos = self.mapToScene(event.pos())
        
        if self.digitize_mode and event.button() == Qt.LeftButton:
            # Emit click for digitizing
            self.mouseClicked.emit(scene_pos, event.button())
        elif event.button() == Qt.MiddleButton or (event.button() == Qt.LeftButton and self.pan_mode):
            # Start panning
            self._pan_start_pos = event.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        else:
            super().mousePressEvent(event)
            
    def mouseMoveEvent(self, event):
        """Handle mouse move events"""
        scene_pos = self.mapToScene(event.pos())
        self.mousePositionChanged.emit(scene_pos)
        
        # Update crosshair
        self.update_crosshair(scene_pos)
        
        if self._pan_start_pos:
            # Panning
            delta = event.pos() - self._pan_start_pos
            self._pan_start_pos = event.pos()
            
            # Update scroll bars
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
        else:
            super().mouseMoveEvent(event)
            
    def mouseReleaseEvent(self, event):
        """Handle mouse release events"""
        if self._pan_start_pos:
            self._pan_start_pos = None
            if self.pan_mode:
                self.setCursor(QCursor(Qt.OpenHandCursor))
            else:
                self.setCursor(QCursor(Qt.ArrowCursor))
        else:
            super().mouseReleaseEvent(event)
            
    def set_pan_mode(self, enabled):
        """Enable/disable pan mode"""
        self.pan_mode = enabled
        if enabled:
            self.digitize_mode = False
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(QCursor(Qt.OpenHandCursor))
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            
    def set_digitize_mode(self, enabled):
        """Enable/disable digitize mode"""
        self.digitize_mode = enabled
        if enabled:
            self.pan_mode = False
            self.setDragMode(QGraphicsView.NoDrag)
            self.setCursor(QCursor(Qt.CrossCursor))
            # Create crosshair lines if needed
            self.create_crosshair_lines()
        else:
            self.setCursor(QCursor(Qt.ArrowCursor))
            # Hide crosshair
            if self.h_line and self.v_line:
                self.h_line.hide()
                self.v_line.hide()
                self.crosshair_visible = False
            
    def fit_to_window(self):
        """Fit the image to the view"""
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        
    def setScene(self, scene):
        """Override to ensure crosshair lines are created when scene is set"""
        super().setScene(scene)
        if self.digitize_mode:
            self.create_crosshair_lines()


class ImageViewerWidget(QWidget):
    """Main image viewer widget with toolbar and graphics view"""
    
    # Signals
    mousePositionChanged = pyqtSignal(float, float)  # Image coordinates
    mouseClicked = pyqtSignal(float, float, int)  # Image coordinates and button
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Setup UI
        self.setup_ui()
        
        # Image item
        self.image_item = None
        self.image_pixmap = None
        
        # Marker management
        self.reference_markers = {}  # {marker_type: QGraphicsItem}
        self.series_markers = {}  # {series_name: [QGraphicsItems]}
        self.georef_markers = []  # [QGraphicsItems]
        
        # Coordinate transformation callback
        self.coordinate_transform_callback = None
        
    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create toolbar
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(16, 16))
        
        # Add toolbar actions
        self.action_zoom_in = QAction("Zoom In", self)
        self.action_zoom_in.setShortcut("Ctrl++")
        self.action_zoom_in.triggered.connect(self.zoom_in)
        self.toolbar.addAction(self.action_zoom_in)
        
        self.action_zoom_out = QAction("Zoom Out", self)
        self.action_zoom_out.setShortcut("Ctrl+-")
        self.action_zoom_out.triggered.connect(self.zoom_out)
        self.toolbar.addAction(self.action_zoom_out)
        
        self.action_zoom_fit = QAction("Fit to Window", self)
        self.action_zoom_fit.setShortcut("Ctrl+0")
        self.action_zoom_fit.triggered.connect(self.fit_to_window)
        self.toolbar.addAction(self.action_zoom_fit)
        
        self.action_zoom_actual = QAction("Actual Size", self)
        self.action_zoom_actual.setShortcut("Ctrl+1")
        self.action_zoom_actual.triggered.connect(self.zoom_actual)
        self.toolbar.addAction(self.action_zoom_actual)
        
        self.toolbar.addSeparator()
        
        self.action_pan = QAction("Pan", self)
        self.action_pan.setCheckable(True)
        self.action_pan.triggered.connect(self.toggle_pan_mode)
        self.toolbar.addAction(self.action_pan)
        
        self.action_digitize = QAction("Digitize", self)
        self.action_digitize.setCheckable(True)
        self.action_digitize.triggered.connect(self.toggle_digitize_mode)
        self.toolbar.addAction(self.action_digitize)
        
        layout.addWidget(self.toolbar)
        
        # Create graphics view and scene
        self.scene = QGraphicsScene()
        self.view = ImageGraphicsView()
        self.view.setScene(self.scene)
        
        # Connect view signals
        self.view.mousePositionChanged.connect(self._on_mouse_position_changed)
        self.view.mouseClicked.connect(self._on_mouse_clicked)
        
        layout.addWidget(self.view)
        
        # Status bar with pixel and plot coordinates
        self.status_layout = QHBoxLayout()
        self.coord_label = QLabel("X: 0.0, Y: 0.0")
        self.plot_coord_label = QLabel("Plot X: --, Plot Z: --")
        self.plot_coord_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        
        self.status_layout.addWidget(self.coord_label)
        self.status_layout.addWidget(QLabel(" | "))  # Separator
        self.status_layout.addWidget(self.plot_coord_label)
        self.status_layout.addStretch()
        layout.addLayout(self.status_layout)
        
        self.setLayout(layout)
        
    def set_coordinate_transform_callback(self, callback):
        """Set callback function for coordinate transformation"""
        self.coordinate_transform_callback = callback
        
    def load_image(self, image_path):
        """Load an image into the viewer"""
        self.image_pixmap = QPixmap(image_path)
        if self.image_pixmap.isNull():
            return False
            
        # Clear existing image
        if self.image_item:
            self.scene.removeItem(self.image_item)
            
        # Add new image
        self.image_item = QGraphicsPixmapItem(self.image_pixmap)
        self.scene.addItem(self.image_item)
        
        # Update scene rect
        self.scene.setSceneRect(self.image_item.boundingRect())
        
        # Fit to window
        self.fit_to_window()
        
        return True
        
    def zoom_in(self):
        """Zoom in by a fixed factor"""
        self.view.scale(1.2, 1.2)
        
    def zoom_out(self):
        """Zoom out by a fixed factor"""
        self.view.scale(0.8, 0.8)
        
    def fit_to_window(self):
        """Fit image to window"""
        self.view.fit_to_window()
        
    def zoom_actual(self):
        """Reset to actual size"""
        self.view.resetTransform()
        
    def toggle_pan_mode(self, checked):
        """Toggle pan mode"""
        self.view.set_pan_mode(checked)
        if checked:
            self.action_digitize.setChecked(False)
            
    def toggle_digitize_mode(self, checked):
        """Toggle digitize mode"""
        self.view.set_digitize_mode(checked)
        if checked:
            self.action_pan.setChecked(False)
            
    def _on_mouse_position_changed(self, scene_pos):
        """Handle mouse position changes"""
        if self.image_item and self.image_item.contains(scene_pos):
            # Convert to image pixel coordinates
            img_pos = self.image_item.mapFromScene(scene_pos)
            self.coord_label.setText(f"X: {img_pos.x():.1f}, Y: {img_pos.y():.1f}")
            self.mousePositionChanged.emit(img_pos.x(), img_pos.y())
            
            # Update plot coordinates if transformation is available
            if self.coordinate_transform_callback:
                plot_coords = self.coordinate_transform_callback(img_pos.x(), img_pos.y())
                if plot_coords:
                    self.plot_coord_label.setText(f"Plot X: {plot_coords[0]:.3f}, Plot Z: {plot_coords[1]:.3f}")
                else:
                    self.plot_coord_label.setText("Plot X: --, Plot Z: --")
            else:
                self.plot_coord_label.setText("Plot X: --, Plot Z: --")
        else:
            self.coord_label.setText("X: --, Y: --")
            self.plot_coord_label.setText("Plot X: --, Plot Z: --")
            
    def _on_mouse_clicked(self, scene_pos, button):
        """Handle mouse clicks"""
        if self.image_item and self.image_item.contains(scene_pos):
            # Convert to image pixel coordinates
            img_pos = self.image_item.mapFromScene(scene_pos)
            self.mouseClicked.emit(img_pos.x(), img_pos.y(), button)
            
    def add_reference_marker(self, x, y, marker_type):
        """Add a reference point marker"""
        # Remove existing marker of this type
        if marker_type in self.reference_markers:
            self.scene.removeItem(self.reference_markers[marker_type])
            
        # Color coding for reference points
        colors = {
            'origin': QColor(0, 255, 0),      # Green
            'x_ref': QColor(0, 0, 255),       # Blue
            'y_ref': QColor(255, 165, 0)      # Orange
        }
        
        # Create marker
        scene_pos = self.image_item.mapToScene(QPointF(x, y))
        marker = CrossGraphicsItem(scene_pos, size=10, 
                                  color=colors.get(marker_type, QColor(255, 0, 0)),
                                  pen_width=3)
        self.scene.addItem(marker)
        self.reference_markers[marker_type] = marker
        
    def add_data_marker(self, x, y, series_name, is_active=True):
        """Add a data point marker"""
        if series_name not in self.series_markers:
            self.series_markers[series_name] = []
            
        # Color based on active state
        color = QColor(0, 0, 0) if is_active else QColor(128, 128, 128)
        
        # Create marker
        scene_pos = self.image_item.mapToScene(QPointF(x, y))
        marker = CrossGraphicsItem(scene_pos, size=6, color=color, pen_width=2)
        self.scene.addItem(marker)
        self.series_markers[series_name].append(marker)
        
    def add_georef_marker(self, x, y):
        """Add a georeferencing point marker"""
        # Create red marker
        scene_pos = self.image_item.mapToScene(QPointF(x, y))
        marker = CrossGraphicsItem(scene_pos, size=8, 
                                  color=QColor(255, 0, 0), pen_width=3)
        self.scene.addItem(marker)
        self.georef_markers.append(marker)
        
    def clear_reference_markers(self):
        """Clear all reference markers"""
        for marker in self.reference_markers.values():
            self.scene.removeItem(marker)
        self.reference_markers.clear()
        
    def clear_series_markers(self, series_name=None):
        """Clear markers for a specific series or all series"""
        if series_name:
            if series_name in self.series_markers:
                for marker in self.series_markers[series_name]:
                    self.scene.removeItem(marker)
                del self.series_markers[series_name]
        else:
            for markers in self.series_markers.values():
                for marker in markers:
                    self.scene.removeItem(marker)
            self.series_markers.clear()
            
    def clear_georef_markers(self):
        """Clear all georeferencing markers"""
        for marker in self.georef_markers:
            self.scene.removeItem(marker)
        self.georef_markers.clear()
        
    def update_series_colors(self, active_series):
        """Update marker colors based on active series"""
        for series_name, markers in self.series_markers.items():
            is_active = (series_name == active_series)
            color = QColor(0, 0, 0) if is_active else QColor(128, 128, 128)
            
            for marker in markers:
                marker.color = color
                marker.update()  # Trigger repaint

    def get_image_size(self):
        """Get the size of the loaded image in pixels"""
        if self.image_pixmap and not self.image_pixmap.isNull():
            return (self.image_pixmap.width(), self.image_pixmap.height())
        return None