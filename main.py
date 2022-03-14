"""Location Tracking for Internet of Things [AICTE QIP STC]"""
import enum
import sys

# Import QApplication and the required widgets from PyQt5.QtWidgets
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QRect, QSize, QPoint
from PyQt5.QtGui import QIcon, QPainter, QPen, QPalette, QVector2D, QBrush, QColor, QFont
from PyQt5.QtWidgets import QApplication, QAction, QSlider, QLabel
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QWidget

__version__ = '0.1'
__author__ = 'Shibobrota Das'


class Type(enum.Enum):
    Anchor = 1
    Point = 2


class Node(QRect):
    def __init__(self, point, size, type):
        super(Node, self).__init__(point, size)
        self.type = type


class Canvas(QWidget):
    def __init__(self):
        super(Canvas, self).__init__()
        self.drag_position = QtCore.QPoint()
        self.rects = []
        self.idx = None
        self.nodeSize = QSize(20, 20)
        palette = self.palette()
        palette.setColor(QPalette.Background, Qt.white)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.selectedType = Type.Anchor
        self.pointCount = 0
        self.nodeUncertainity = 0

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        point = None
        anchors = []
        for rect in self.rects:
            if rect.type == Type.Anchor:
                anchors.append(rect)
                colour = Qt.red
                painter.setPen(QPen(colour, 1, QtCore.Qt.SolidLine))
                painter.setBrush(colour)
                painter.drawRect(rect)
                painter.setPen(QPen(Qt.black, 1, QtCore.Qt.SolidLine))
                painter.drawText(rect.bottomLeft() + QPoint(-17, 20), f"({rect.center().x()}, {rect.center().y()})")
            else:
                point = rect
        if point is not None:
            for a in anchors:
                dist = QVector2D(point.center() - a.center()).length()
                pen = QPen(QColor(255, 255, 0, 50), self.nodeUncertainity, QtCore.Qt.SolidLine)
                if self.nodeUncertainity == 0:
                    pen = QPen(QColor(0, 0, 255, 50), 1, QtCore.Qt.SolidLine)
                painter.setPen(pen)
                painter.setBrush(QBrush())
                rect = QRect(QPoint(a.x() + a.width() // 2 - dist, a.y() + a.height() // 2 - dist),
                             QSize(2 * dist, 2 * dist))
                painter.drawEllipse(rect)

                painter.setPen(QPen(Qt.red, 1, QtCore.Qt.SolidLine))
                painter.drawLine(a.center(), point.center())

                painter.setPen(QPen(Qt.black, 1, QtCore.Qt.SolidLine))
                painter.drawText((a.center() + point.center()) / 2, str(round(dist, 1)))

            colour = Qt.black
            painter.setPen(QPen(colour, 1, QtCore.Qt.SolidLine))
            painter.setBrush(colour)
            painter.drawEllipse(point)
            painter.setPen(QPen(Qt.black, 1, QtCore.Qt.SolidLine))
            painter.drawText(point.bottomLeft() + QPoint(-17, 20), f"({point.center().x()}, {point.center().y()})")

    def mousePressEvent(self, event):
        for i in range(len(self.rects)):
            if 2 * QVector2D(event.pos() - self.rects[i].center()).length() < self.rects[i].width():
                if event.button() == Qt.LeftButton:
                    self.drag_position = event.pos() - self.rects[i].topLeft()
                    self.idx = i
                elif event.button() == Qt.RightButton:
                    if self.rects[i].type == Type.Point:
                        self.pointCount -= 1
                    self.rects.pop(i)
                break
        if self.drag_position.isNull() and event.button() == Qt.LeftButton:
            if (self.selectedType == Type.Point and self.pointCount == 0) or self.selectedType == Type.Anchor:
                if self.selectedType == Type.Point: self.pointCount += 1
                self.rects.append(
                    Node(event.pos() - QPoint(self.nodeSize.width() // 2, self.nodeSize.height() // 2), self.nodeSize,
                         self.selectedType))
                self.drag_position = event.pos() - self.rects[-1].topLeft()
                self.idx = len(self.rects) - 1
        super().mousePressEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        if not self.drag_position.isNull():
            self.rects[self.idx].moveTopLeft(event.pos() - self.drag_position)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_position = QtCore.QPoint()
        super().mouseReleaseEvent(event)


# Create a subclass of QMainWindow to setup the app GUI
class MainWindow(QMainWindow):

    def __init__(self, app):
        """View initializer."""
        super().__init__()

        self._nodeRadius = 10.0
        self._nodes = []
        self.idx = None
        self.dragPosition = QPoint()

        # Set some main window's properties
        self.setWindowTitle('Location Tracking for Internet of Things')
        screenSize = app.primaryScreen().size()
        self.setMinimumSize(int(screenSize.width() * 0.75), int(screenSize.height() * 0.75))
        self._canvas = Canvas()

        # Add Toolbar
        self._toolBar = QtWidgets.QToolBar("toolBar")
        self._toolBar.setMovable(False)
        self._anchorButton = QtWidgets.QToolButton(self)
        self._anchorButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self._anchorButton.setDefaultAction(
            QAction(QIcon("square.png"), "ANCHOR", self, triggered=self.onAnchorButtonCheckedChanged, checkable=True,
                    checked=True))
        self._pointButton = QtWidgets.QToolButton(self)
        self._pointButton.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self._pointButton.setDefaultAction(
            QAction(QIcon("circle.png"), "POINT", self, triggered=self.onPointButtonCheckedChanged, checkable=True,
                    checked=False))
        self._buttonGroup = QtWidgets.QButtonGroup(self, exclusive=True)

        for button in [self._anchorButton, self._pointButton]:
            self._toolBar.addWidget(button)
            self._buttonGroup.addButton(button)

        for action in self._toolBar.actions():
            widget = self._toolBar.widgetForAction(action)
            widget.setFixedSize(70, 70)

        self._slider = QSlider(Qt.Horizontal, self)
        self._slider.valueChanged[int].connect(self.onSliderValueChanged)
        self._textFont = QFont()
        self._sliderValueLabel = QLabel("Error Value: 0")
        self._sliderValueLabel.setMaximumHeight(40)
        self._textFont.setPointSize(12)
        self._sliderValueLabel.setFont(self._textFont)
        self._sliderLabel = QLabel("Error in Range")
        self._sliderLabel.setMaximumHeight(40)
        self._textFont.setPointSize(10)
        self._sliderLabel.setFont(self._textFont)

        self._canvasWidthLabel = QLabel()
        self._canvasWidthLabel.setFont(self._textFont)
        self._canvasWidthLabel.setMaximumHeight(20)
        self._canvasHeightLabel = QLabel()
        self._canvasHeightLabel.setFont(self._textFont)
        self._canvasHeightLabel.setMaximumHeight(20)

        self.addToolBar(Qt.LeftToolBarArea, self._toolBar)
        # Construct Central Widget
        self._centralWidget = QWidget()
        self._centralWidgetLayout = QHBoxLayout()
        self._leftLayout = QVBoxLayout()
        self._rightLayout = QVBoxLayout()
        self._rightTopLayout = QVBoxLayout()
        self._rightBottomLayout = QVBoxLayout()
        self._rightTopLayout.addWidget(self._sliderLabel)
        self._rightTopLayout.addWidget(self._slider)
        self._rightTopLayout.addWidget(self._sliderValueLabel)
        self._rightTopLayout.addWidget(self._canvasWidthLabel)
        self._rightTopLayout.addWidget(self._canvasHeightLabel)
        self._rightBottomLayout.addWidget(Canvas())
        self._rightLayout.addLayout(self._rightTopLayout)
        self._rightLayout.addLayout(self._rightBottomLayout)
        self._leftLayout.addWidget(self._canvas)
        self._centralWidgetLayout.addLayout(self._leftLayout, 5)
        self._centralWidgetLayout.addLayout(self._rightLayout, 3)
        self._centralWidget.setLayout(self._centralWidgetLayout)
        # Set the central widget
        self.setCentralWidget(self._centralWidget)

    def onAnchorButtonCheckedChanged(self, event):
        if event: self._canvas.selectedType = Type.Anchor

    def onPointButtonCheckedChanged(self, event):
        if event: self._canvas.selectedType = Type.Point

    def onSliderValueChanged(self, val):
        print(val)
        self._canvas.nodeUncertainity = val
        self._canvas.update()
        self._sliderValueLabel.setText(f"Error Value: {val * 2}")

    def paintEvent(self, event):
        super(MainWindow, self).paintEvent(event)
        painter = QPainter(self._canvas)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(QPen(Qt.black, 10, Qt.SolidLine))
        # painter.setBrush(Qt.black)
        for node in self._nodes:
            painter.drawEllipse(node)

    def mousePressEvent(self, event):
        for i in range(len(self._nodes)):
            if 2 * QVector2D(event.pos() - self._nodes[i].center()).length() < self._nodes[i].width():
                self.dragPosition = event.pos() - self._nodes[i].topLeft()
                self.idx = i
        if self.dragPosition.isNull():
            self._nodes.append(Node(event.pos(), QtCore.QSize(100, 100), Type.Anchor))
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self.dragPosition.isNull():
            self._nodes[self.idx].moveTopLeft(event.pos() - self.dragPosition)
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragPosition = QtCore.QPoint()
        self.idx = None
        super().mouseReleaseEvent(event)

    def setup(self):
        self._canvasWidthLabel.setText(f"Canvas Width: {self._canvas.width()}")
        self._canvasHeightLabel.setText(f"Canvas Height: {self._canvas.height()}")

    def resizeEvent(self, event):
        print(event.size())
        self._canvasWidthLabel.setText(f"Canvas Width: {self._canvas.width()}")
        self._canvasHeightLabel.setText(f"Canvas Height: {self._canvas.height()}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    # Show the app's GUI
    view = MainWindow(app)
    view.show()
    view.setup()
    # Execute the app's main loop
    sys.exit(app.exec_())
