"""Location Tracking for Internet of Things [AICTE QIP STC]"""
import enum
import math
import sys

# Import QApplication and the required widgets from PyQt5.QtWidgets
import lmfit
import numpy as np
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QRect, QSize, QPoint, pyqtSignal
from PyQt5.QtGui import QIcon, QPainter, QPen, QPalette, QVector2D, QBrush, QColor, QFont, QPixmap
from PyQt5.QtWidgets import QApplication, QAction, QSlider, QLabel, QFrame, QLCDNumber, QPushButton
from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QWidget

__version__ = '0.1'
__author__ = 'Shibobrota Das'


class Type(enum.Enum):
    Anchor = 1
    Point = 2


def distance(point1, point2):
    x1 = point1[0]
    y1 = point1[1]
    x2 = point2[0]
    y2 = point2[1]
    distance = math.sqrt(math.pow(x1 - x2, 2) + (math.pow(y1 - y2, 2)))
    return distance


def cost_value(location, anchor_range_loc):
    '''
    Cost function
    Inputs :
        i) Location of the point under consideration
        ii) Anchor locations & True distance between the node and anchor points
    Outputs :
        i) An array conatining square of errors corresponding to each anchor
    '''
    anchors = anchor_range_loc[0]
    ranges = anchor_range_loc[1]
    k = 0
    error_sq = np.empty(anchors.shape[0])
    for i in anchors:
        error_sq[k] = math.pow(distance(i, (location['x'], location['y'])) - ranges[k], 2)
        k += 1
    return error_sq


class Label(QLabel):
    def __init__(self, *args):
        super(Label, self).__init__(*args)
        self.setStyleSheet('''
        QLabel {
            background-color: white;
            padding: 10px;
        }
        ''')
        self.setMaximumHeight(50)
        self.font = QFont()
        self.font.setPointSize(13)
        self.setFont(self.font)

    def setPointSize(self, size):
        self.font.setPointSize(size)
        self.setFont(self.font)


class Button(QPushButton):
    def __init__(self, *args):
        super(Button, self).__init__(*args)
        self.setStyleSheet('''
            QPushButton {
                background-color: white;
                padding: 7px;
            }
        ''')


class Slider(QSlider):
    # create our our signal that we can connect to if necessary
    doubleValueChanged = pyqtSignal(float)

    def __init__(self, decimals=3, *args, **kargs):
        super(Slider, self).__init__(*args, **kargs)
        self._multi = 10 ** decimals

        self.valueChanged.connect(self.emitDoubleValueChanged)

    def emitDoubleValueChanged(self):
        value = float(super(Slider, self).value()) / self._multi
        self.doubleValueChanged.emit(value)

    def value(self):
        return float(super(Slider, self).value()) / self._multi

    def setMinimum(self, value):
        return super(Slider, self).setMinimum(value * self._multi)

    def setMaximum(self, value):
        return super(Slider, self).setMaximum(value * self._multi)

    def setSingleStep(self, value):
        return super(Slider, self).setSingleStep(value * self._multi)

    def singleStep(self):
        return float(super(Slider, self).singleStep()) / self._multi

    def setValue(self, value):
        super(Slider, self).setValue(int(value * self._multi))


class SliderView(QFrame):
    def __init__(self, callback, min, max, title):
        super(SliderView, self).__init__()
        self._layout = QVBoxLayout()
        self._slider = Slider(2, Qt.Horizontal, self)
        self._slider.setMaximum(max)
        self._slider.setMinimum(min)
        self._slider.doubleValueChanged.connect(self.onValueChanged)
        self._lcdText = QLCDNumber()
        self.sliderHorizontalView = QHBoxLayout()
        self._minLabel = QLabel(str(min))
        self._font = QFont()
        self._font.setPointSize(13)
        self._minLabel.setFont(self._font)
        self.resetButton = Button()
        self.resetButton.setText("Reset")
        self.resetButton.clicked.connect(self.resetValue)
        self.sliderHorizontalView.addWidget(self._minLabel)
        self.sliderHorizontalView.addWidget(self._slider)
        self._maxLabel = QLabel(str(max))
        self._maxLabel.setFont(self._font)
        self.sliderHorizontalView.addWidget(self._maxLabel)
        self.sliderHorizontalView.addWidget(self.resetButton)
        self._title = QLabel(title)
        self._title.setMaximumHeight(20)
        self.setFont(self._font)
        self._layout.addWidget(self._title)
        self._layout.addWidget(self._lcdText)
        self._layout.addLayout(self.sliderHorizontalView)
        self.setLayout(self._layout)
        self.callback = callback
        self.setFixedHeight(170)

    def onValueChanged(self, val):
        self._lcdText.display(str(val).strip(" "))
        self.callback(val)

    def resetValue(self):
        self._slider.setValue(0.)


class Node(QRect):
    def __init__(self, point, size, type):
        super(Node, self).__init__(point, size)
        self.type = type
        self.distError = 0.0


class Canvas(QWidget):
    def __init__(self, callback):
        super(Canvas, self).__init__()
        self.drag_position = QtCore.QPoint()
        self.nodes = []
        self.idx = None
        self.nodeSize = QSize(20, 20)
        palette = self.palette()
        palette.setColor(QPalette.Background, Qt.white)
        self.setAutoFillBackground(True)
        self.setPalette(palette)
        self.selectedType = Type.Anchor
        self.pointCount = 0
        self.nodeMeanError = 0.
        self.nodeErrorStdDeviation = 0.
        self.onPosChange = callback
        self.location = None
        self.lastKnownUncertainity = 0.

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        point = None
        anchors = []
        for rect in self.nodes:
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
                pen = QPen(QColor(255, 255, 0, 50), 2 * self.nodeErrorStdDeviation, QtCore.Qt.SolidLine)
                if 2 * self.nodeErrorStdDeviation == 0:
                    pen = QPen(QColor(0, 0, 255, 50), 1, QtCore.Qt.SolidLine)
                painter.setPen(pen)
                painter.setBrush(QBrush())
                rect = QRect(QPoint(a.x() + a.width() // 2 - (dist + self.nodeMeanError // 2),
                                    a.y() + a.height() // 2 - (dist + self.nodeMeanError // 2)),
                             QSize((2 * dist) + self.nodeMeanError, (2 * dist) + self.nodeMeanError))
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
            print(anchors, point)
            node_loc_estimate = None
            if len(anchors) > 1:
                ranges = [math.dist((point.center().x(), point.center().y()), (a.center().x(), a.center().y())) + a.distError for a in
                          anchors]
                x = [np.array([(a.center().x(), a.center().y()) for a in anchors]), np.array(ranges)]
                loc_estimate = lmfit.minimize(cost_value, self.location, args=(x,))
                node_loc_estimate = (round(loc_estimate.params['x'].value), round(loc_estimate.params['y'].value))
                print(node_loc_estimate)
            if self.lastKnownUncertainity != self.nodeMeanError + 2 * self.nodeErrorStdDeviation:
                self.lastKnownUncertainity = self.nodeMeanError + 2 * self.nodeErrorStdDeviation
                for a in anchors:
                    a.distError = np.random.normal(self.nodeMeanError, self.nodeErrorStdDeviation)
            if node_loc_estimate is not None:
                painter.setPen(QPen(Qt.lightGray, 1, QtCore.Qt.SolidLine))
                painter.setBrush(QColor(0, 0, 255, 50))
                estimatedNode = Node(QPoint(-1, -1), QSize(point.width()+10, point.height()+10), Type.Point)
                estimatedNode.moveCenter(QPoint(node_loc_estimate[0], node_loc_estimate[1]))
                painter.drawEllipse(estimatedNode)
                painter.setPen(QPen(Qt.blue, 1, QtCore.Qt.SolidLine))
                painter.drawText(estimatedNode.topLeft() + QPoint(-12, -10), f"{node_loc_estimate}")
                painter.drawText(estimatedNode.topLeft() + QPoint(-17, -25), "Estimated Pos")
                errorInPos = round(math.dist(node_loc_estimate, (point.center().x(), point.center().y())), 2)
                self.onPosChange(node_loc_estimate, errorInPos)
            else:
                self.onPosChange("--", "--")

    def mousePressEvent(self, event):
        for i in range(len(self.nodes)):
            if 2 * QVector2D(event.pos() - self.nodes[i].center()).length() < self.nodes[i].width():
                if event.button() == Qt.LeftButton:
                    self.drag_position = event.pos() - self.nodes[i].topLeft()
                    self.idx = i
                elif event.button() == Qt.RightButton:
                    if self.nodes[i].type == Type.Point:
                        self.pointCount -= 1
                    self.nodes.pop(i)
                break
        if self.drag_position.isNull() and event.button() == Qt.LeftButton:
            if (self.selectedType == Type.Point and self.pointCount == 0) or self.selectedType == Type.Anchor:
                if self.selectedType == Type.Point: self.pointCount += 1
                self.nodes.append(
                    Node(event.pos() - QPoint(self.nodeSize.width() // 2, self.nodeSize.height() // 2), self.nodeSize,
                         self.selectedType))
                self.drag_position = event.pos() - self.nodes[-1].topLeft()
                self.nodes[-1].distError = np.random.normal(self.nodeMeanError, self.nodeErrorStdDeviation)
                self.idx = len(self.nodes) - 1
        super().mousePressEvent(event)
        self.update()

    def mouseMoveEvent(self, event):
        if not self.drag_position.isNull():
            self.nodes[self.idx].moveTopLeft(event.pos() - self.drag_position)
            self.nodes[self.idx].distError = np.random.normal(self.nodeMeanError, self.nodeErrorStdDeviation)
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
        self.location = None
        self._nodeMeanError = 0.0
        self._nodeErrorStdDeviation = 0.0

        # Set some main window's properties
        self.setWindowTitle('Location Tracking for Internet of Things (Sense Lab)')
        screenSize = app.primaryScreen().size()
        self.setMinimumSize(int(screenSize.width() * 0.75), int(screenSize.height() * 0.75))
        self._canvas = Canvas(self.estimatePos)

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

        self._meanSlider = SliderView(self.onMeanValueChanged, -100, 100, "Mean Error (centre)")
        self._standardDeviationSlider = SliderView(self.onStandardDeviationValueChanged, 0, 100,
                                                   "Standard Deviation (spread or width)")
        self._distanceErrorLabel = Label("Estimated Pos: --")
        self._estimatedPosLabel = Label("Error in position: --")

        # Developer Details
        self._senseLabLogoPixMap = QPixmap("senselab_logo_small.png")
        self._senseLabLogo = QLabel()
        self._senseLabLogo.setPixmap(self._senseLabLogoPixMap)
        self._developerDetails = Label("Developed By: Shibobrota Das (SENSE Lab @iitm)")
        self._developerDetails.setPointSize(7)

        self.addToolBar(Qt.LeftToolBarArea, self._toolBar)
        # Construct Central Widget
        self._centralWidget = QWidget()
        self._centralWidgetLayout = QHBoxLayout()
        self._leftLayout = QVBoxLayout()
        self._rightLayout = QVBoxLayout()
        self._rightTopLayout = QVBoxLayout()
        self._rightBottomLayout = QVBoxLayout()
        self._rightMiddleLayout = QVBoxLayout()
        self._rightTopLayout.addWidget(self._meanSlider)
        self._rightTopLayout.addWidget(self._standardDeviationSlider)
        self._rightTopLayout.addWidget(self._distanceErrorLabel)
        self._rightTopLayout.addWidget(self._estimatedPosLabel)
        self._rightMiddleLayout.addWidget(QFrame())
        self._rightBottomLayout.addWidget(self._senseLabLogo, alignment=Qt.AlignHCenter)
        self._rightBottomLayout.addWidget(self._developerDetails)
        self._rightLayout.addLayout(self._rightTopLayout)
        self._rightLayout.addLayout(self._rightMiddleLayout)
        self._rightLayout.addLayout(self._rightBottomLayout)
        self._leftLayout.addWidget(self._canvas)
        self._centralWidgetLayout.addLayout(self._leftLayout, 7)
        self._centralWidgetLayout.addLayout(self._rightLayout, 3)
        self._centralWidget.setLayout(self._centralWidgetLayout)
        # Set the central widget
        self.setCentralWidget(self._centralWidget)

    def onAnchorButtonCheckedChanged(self, event):
        if event: self._canvas.selectedType = Type.Anchor

    def onPointButtonCheckedChanged(self, event):
        if event: self._canvas.selectedType = Type.Point

    def onMeanValueChanged(self, val):
        print("mean error", val)
        self._nodeMeanError = val
        self._canvas.nodeMeanError = self._nodeMeanError
        self._canvas.nodeErrorStdDeviation = self._nodeErrorStdDeviation
        self._canvas.update()

    def onStandardDeviationValueChanged(self, val):
        print(val)
        self._nodeErrorStdDeviation = val
        self._canvas.nodeMeanError = self._nodeMeanError
        self._canvas.nodeErrorStdDeviation = self._nodeErrorStdDeviation
        self._canvas.update()

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
        self.showCanvasSize()

    def resizeEvent(self, event):
        print(event.size())
        self.showCanvasSize()

    def showCanvasSize(self):
        self.statusBar().showMessage(f"Canvas: {self._canvas.width()}x{self._canvas.height()} px")
        self._canvas.location = lmfit.Parameters()
        self._canvas.location.add('x', value=self._canvas.width() / 2, max=self._canvas.width(), min=0.0)
        self._canvas.location.add('y', value=self._canvas.height() / 2, max=self._canvas.height(), min=0.0)

    def estimatePos(self, node_loc_estimate, error):
        self._distanceErrorLabel.setText(f"Estimated Pos: {str(node_loc_estimate)}")
        self._estimatedPosLabel.setText(
            f"Error in position: {error}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    # Show the app's GUI
    view = MainWindow(app)
    view.show()
    view.setup()
    # Execute the app's main loop
    sys.exit(app.exec_())
