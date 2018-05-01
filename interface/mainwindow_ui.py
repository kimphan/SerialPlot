from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import Qt, QEvent, pyqtSignal, pyqtSlot
from interface.graph_ui import GraphUI
from manage.manager import PlotManager
from helper.serial_scanner import SerialScan
from manage.worker import Worker
from functools import partial
import os, signal,serial


class MainWindow(QMainWindow):
    LABELFONT = 15
    add_button = pyqtSignal('QGridLayout', int, int, int, str, str, str, int)

    def __init__(self):
        super(MainWindow, self).__init__()
        self.w = 1300
        self.h = 700
        self.setMinimumHeight(self.h+100)
        self.setMinimumWidth(self.w)
        self.center()
        self.statusBar().showMessage('Ready')
        self.setWindowTitle('Channel Plot')

        self.key = 0
        self.plot_count = 0
        self.add = 0
        self.splot_count = 0
        self.splot = -1
        self.addtopbottom = False
        self.scan = SerialScan()
        self.clist = [] # Channel list
        self.funcList = []  # Function list
        self.plotDictionary = dict() # Plot widget
        self.isReady = False

        self.store_graph = dict()
        self.store_plot = dict()
        self.store_subplot = dict()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.windowLayout = QHBoxLayout()
        self.windowLayout.setAlignment(Qt.AlignLeft)
        self.central_widget.setLayout(self.windowLayout)
        self.loadui()

    # Setup UI for main window
    def loadui(self):
        # Widgets
        self.ports_list = QComboBox()
        self.ports_list.currentTextChanged.connect(self.port_selection)
        self.baudrate = QLineEdit()
        self.baudrate.setText('115200')
        self.scan_btn = self.button('Scan Port',self.get_available_port)
        self.show_btn = self.button('Show',self.show_plot)
        self.stop_btn = self.button('Stop',self.serial_stop)

        # Get available serial port
        # self.get_available_port()

        vertical_menu = QVBoxLayout()
        vertical_menu.setAlignment(Qt.AlignLeft)
        vertical_menu.SetFixedSize

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.stop_btn)
        buttonLayout.addWidget(self.show_btn)

        # Serial Setup Box
        serial_box = QGroupBox('Serial Setup')
        serial_box.setStyleSheet('font-size: 12pt; color: 606060;')
        serial_form = QFormLayout()
        serial_form.addRow('Port',self.ports_list)
        serial_form.addRow('Baudrate',self.baudrate)
        serial_form.addRow('',self.scan_btn)
        serial_box.setLayout(serial_form)
        serial_box.setFixedWidth(self.w/7)
        serial_box.setFixedHeight(self.h/5)

        # Function Box
        func1 = QCheckBox('Raw Data')
        func1.setObjectName('Raw Data')
        func1.setChecked(True)
        func2 = QCheckBox('Autocorrelation')
        func2.setObjectName('Autocorrelation')
        func3 = QCheckBox('Heart Beat')
        func3.setObjectName('Heart Beat')
        self.funcList.append(func1)
        self.funcList.append(func2)
        self.funcList.append(func3)

        function_box = QGroupBox('Function')
        function_box.setStyleSheet('font-size: 12pt; color: 606060;')
        function_form = QFormLayout()
        for f in self.funcList:
            function_form.addRow(f)

        function_form.addRow(self.stop_btn,self.show_btn)
        function_box.setLayout(function_form)
        function_box.setFixedWidth(self.w/7)
        function_box.setFixedHeight(self.h*2/5)

        # Channel Box
        channel_box = QGroupBox('Channel List')
        channel_box.setStyleSheet('font-size: 12pt; color: 606060;')
        self.channel = QFormLayout()
        channel_box.setLayout(self.channel)
        channel_box.setFixedWidth(self.w/7)

        vertical_menu.addWidget(serial_box)
        vertical_menu.addWidget(function_box)
        vertical_menu.addWidget(channel_box)

        # Display box
        self.graph_display = QGridLayout()
        self.graph_display.setAlignment(Qt.AlignTop)
        self.graph_display.SetFixedSize

        self.windowLayout.addLayout(vertical_menu)
        self.windowLayout.addLayout(self.graph_display)

        self.windowLayout.addStretch()

    # Put the application window in the center of the screen
    def center(self):
        frame = self.frameGeometry()  # specifying geometry of the main window with a rectangle 'qr'
        cp = QDesktopWidget().availableGeometry().center()  # screen size resolution+get the center point
        frame.moveCenter(cp)  # set the rectangle center to the center of the screen
        self.move(frame.topLeft())  # move the top-left point of the application window to the 'qr'
        
    # Button and event handling
    def button(self,name, handler, fontsize=12):
        btn = QPushButton(name)
        btn.setStyleSheet('font-size: {}pt;'.format(fontsize))
        btn.pressed.connect(handler)
        return btn

    def alert(self,message):
        m = QMessageBox.information(self, 'Message', message, QMessageBox.Ok)
        if QMessageBox.Ok:
            pass

    def get_available_port(self):
        plist = self.scan.scan_serial_port()
        self.ports_list.clear()
        if len(plist) == 0:
            self.alert('Cannot find the serial port')
        else:
            for p in plist:
                self.ports_list.addItem(p)

    def port_selection(self, currPort):
        self.clear_clist()
        if not self.scan.open_port(currPort,self.baudrate.text()):
            self.alert('Cannot find a serial port!')
        else:
            line = self.scan.line
            if line != 0:
                # List all the channels read from serial port
                for c in range(line):
                    entry = QCheckBox('Channel '+str(c))
                    entry.setObjectName(str(c))
                    entry.setChecked(True)
                    self.clist.append(entry)
                    self.channel.addRow(entry)
            self.isReady = True

    def serial_stop(self):
        print('Stop serial port.')

    def clear_clist(self):
        row_count = self.channel.rowCount()
        self.isReady = False
        self.scan.line = 0
        self.clist.clear()
        while row_count >= 0:
            self.channel.removeRow(row_count)
            row_count -= 1

    def show_plot(self):
        if self.isReady:
            for f in self.funcList:
                funcName = f.objectName()
                if f.isChecked() and funcName not in self.plotDictionary.keys():
                    plot_widget = GraphUI(self.w*6/7).addgraph(funcName)
                    self.graph_display.addWidget(plot_widget,self.plot_count, 0, Qt.AlignLeft)
                    self.plotDictionary.update({funcName:plot_widget})
                    self.plot_count +=1

        else:
            self.alert('Serial port is not selected! Please select a port!')


    def channel_display(self):
        display = []
        for c in self.clist:
            if c.isChecked():
                display.append(c.objectName())
        return display
