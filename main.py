import sys
import cv2
import pyrealsense2 as rs
import numpy as np
from PySide6.QtWidgets import *
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer
from PySide6 import QtCore
import pyqtgraph as pg
import os
from mobbo_stream import MobboCom

import msgpack as mp
import msgpack_numpy as mpn

class VideoStreamApp(QWidget):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Multi-Camera Stream")
        self.setGeometry(100, 100, 640, 480)
        
        
        self.hospital_id_line = QLineEdit()
        
        # Layouts
        main_layout = QVBoxLayout()
        sub_layout = QHBoxLayout()
        video_layout = QHBoxLayout()
        button_layout = QVBoxLayout()

        force_layout = QVBoxLayout()
        
        bottom_layout = QHBoxLayout()     
        # Video Labels
        self.labels = [QLabel(self) for _ in range(3)]
        for label in self.labels:
            label.setFixedSize(400, 350)
            label.setStyleSheet("border: 1px solid black;")
            video_layout.addWidget(label)
        
        self.hospital_id_line.textChanged.connect(self.get_hid)
        
        # Buttons
        self.start_button = QPushButton("Start")
        self.stop_button = QPushButton("Stop")
        
        self.start_record_button = QPushButton('Record')
        self.stop_record_button = QPushButton('Stop Recording')
        self.broadcast_button =  QPushButton('Boardcast')

        self.start_button.clicked.connect(self.start_streams)
        self.stop_button.clicked.connect(self.stop_streams)
        self.start_record_button.clicked.connect(self.start_recording)
        self.stop_record_button.clicked.connect(self.stop_recording)
        self.broadcast_button.clicked.connect(self.send_broadcast)
        
        button_layout.addWidget(self.hospital_id_line)
        button_layout.addWidget(self.start_button)
        
        button_layout.addWidget(self.start_record_button)
        button_layout.addWidget(self.stop_record_button)
        button_layout.addWidget(self.broadcast_button)
        button_layout.addWidget(self.stop_button)
        
        sub_layout.addLayout(video_layout)
        sub_layout.addLayout(button_layout)      
        
        self.graphicsView_1 = pg.PlotWidget()
        self.graphicsView_1.setFixedHeight(200)
        self.graphicsView_2 = pg.PlotWidget()
        self.graphicsView_2.setFixedHeight(200)

        
        self.graphicsView_1.getAxis("bottom").setStyle(showValues=False)
        self.graphicsView_1.getAxis("left").setStyle(showValues=False)
        self.graphicsView_1.getAxis("top").setStyle(showValues=False)
        self.graphicsView_1.getAxis("right").setStyle(showValues=False)
        
        self.graphicsView_2.getAxis("bottom").setStyle(showValues=False)
        self.graphicsView_2.getAxis("left").setStyle(showValues=False)
        self.graphicsView_2.getAxis("top").setStyle(showValues=False)
        self.graphicsView_2.getAxis("right").setStyle(showValues=False)
        
        self.cop_graphicsView1 = pg.PlotWidget()
        self.cop_graphicsView1.setFixedWidth(420)
        self.cop_graphicsView1.setXRange(-30, 30)
        self.cop_graphicsView1.setYRange(-22.5,22.5)
        
        self.cop_graphicsView2 = pg.PlotWidget()
        self.cop_graphicsView2.setFixedWidth(420)
        self.cop_graphicsView2.setXRange(-30,30)
        self.cop_graphicsView2.setYRange(-22.5, 22.5)
        
        force_layout.addWidget(self.graphicsView_1)
        force_layout.addWidget(self.graphicsView_2)
        
        bottom_layout.addLayout(force_layout)
        bottom_layout.addWidget(self.cop_graphicsView1)
        bottom_layout.addWidget(self.cop_graphicsView2)
        

        main_layout.addLayout(sub_layout)
        main_layout.addLayout(bottom_layout)
        # main_layout.addLayout(sub_layout)
        # main_layout.addWidget(self.graphicsView_1)
        # main_layout.addWidget(self.graphicsView_2)

        self.setLayout(main_layout)
        
        ctx = rs.context()
        self.serials = []
        for i in range(len(ctx.devices)):
            sn = ctx.devices[i].get_info(rs.camera_info.serial_number)
            print(sn)
            self.serials.append(sn)
        
        # RealSense camera variables
        self.pipelines = [None, None, None]
        self.running = False
        self.timer = QTimer()
        self.plot_timer = QTimer()
        
        self.timer.timeout.connect(self.update_frames)
        
        self.plot_timer.timeout.connect(self.update_plot)

        
        self.red_pen = pg.mkPen(color=(255, 0, 0), width=3)
        self.green_pen = pg.mkPen(color=(0, 255, 0), width=3)
        self.blue_pen = pg.mkPen(color=(0, 255, 255), width=3)
        self.orange_pen = pg.mkPen(color=(255, 165, 0), width=3)
        
        self.mobbo_x = np.linspace(0, 1000, 1000)
        
        
        self.data_line1_1 = self.graphicsView_1.plot(self.mobbo_x, np.zeros((1000)), pen=self.red_pen, name='ax')
        self.data_line1_2 = self.graphicsView_1.plot(self.mobbo_x, np.zeros((1000)), pen=self.green_pen, name='ay')
        self.data_line1_3 = self.graphicsView_1.plot(self.mobbo_x, np.zeros((1000)), pen=self.blue_pen, name='az')
        self.data_line1_4 = self.graphicsView_1.plot(self.mobbo_x, np.zeros((1000)), pen=self.orange_pen, name='gx')
        
        self.data_line2_1 = self.graphicsView_2.plot(self.mobbo_x, np.zeros((1000)), pen=self.red_pen, name='ax')
        self.data_line2_2 = self.graphicsView_2.plot(self.mobbo_x, np.zeros((1000)), pen=self.green_pen, name='ay')
        self.data_line2_3 = self.graphicsView_2.plot(self.mobbo_x, np.zeros((1000)), pen=self.blue_pen, name='az')
        self.data_line2_4 = self.graphicsView_2.plot(self.mobbo_x, np.zeros((1000)), pen=self.orange_pen, name='gx')
        
        self.cop_plot1 = self.cop_graphicsView1.plot([0],[0], pen=None, symbol='o')
        self.cop_plot2 = self.cop_graphicsView2.plot([0], [0], pen=None, symbol='o')
    
        self.camera_frames = [None, None, None]

        self.mobbo_stream = MobboCom()
        self.mobbo_stream.run()
        
        self.start_record_camera = False
    
    def send_broadcast(self):
        self.mobbo_stream.send_broadcast()
    
    def open_camera_files(self):
        
        if not os.path.exists(os.path.join('data', self.hospital_id)):
            os.makedirs(os.path.join('data', self.hospital_id))
        self.camera_file1 = open(os.path.join('data', self.hospital_id, 'camera1.msgpack'), 'wb')
        self.camera_file2 = open(os.path.join('data', self.hospital_id, 'camera2.msgpack'), 'wb')
        self.camera_file3 = open(os.path.join('data', self.hospital_id, 'camera3.msgpack'), 'wb')
        
        self.camera_files = [self.camera_file1, self.camera_file2, self.camera_file3]
        print('opening camera files')
        
    def get_hid(self, text):
        self.hospital_id = text
        
        
    def start_recording(self):
        if self.hospital_id == '':
            return
        else:
            self.mobbo_stream.hospital_id = self.hospital_id
            self.mobbo_stream.record_stream()
            self.open_camera_files()
            self.start_record_camera = True
        
    def stop_recording(self):
        self.start_record_camera = False
        self.mobbo_stream.stop_recording()
        for file in self.camera_files:
            file.close()
        print('stopping recording')
    
    def closeEvent(self, event):
        self.mobbo_stream.stop_streaming()
        
    def update_plot(self):

        data1 = self.mobbo_stream.plot_data_id1
        data2 = self.mobbo_stream.plot_data_id2
        
        cop1 = self.mobbo_stream.cop1
        cop2 = self.mobbo_stream.cop2

        self.data_line1_1.setData(self.mobbo_x, data1[0, :])
        self.data_line1_2.setData(self.mobbo_x, data1[1, :])
        self.data_line1_3.setData(self.mobbo_x, data1[2, :])
        self.data_line1_4.setData(self.mobbo_x, data1[3, :])
        
        self.data_line2_1.setData(self.mobbo_x, data2[0, :])
        self.data_line2_2.setData(self.mobbo_x, data2[1, :])
        self.data_line2_3.setData(self.mobbo_x, data2[2, :])
        self.data_line2_4.setData(self.mobbo_x, data2[3, :])

        # self.cop_plot1.setData([cop1[0]], [cop1[1]])
        # se
    
        """plot a single point"""
        self.cop_plot2.setData([cop1[0]], [cop1[1]])
        self.cop_plot1.setData([cop2[0]], [cop2[1]])
    
    def start_streams(self):
        
        self.plot_timer.start()

        if not self.running:
            self.running = True
            for i in range(3):
                self.pipelines[i] = rs.pipeline()
                config = rs.config()
                config.enable_device(self.serials[i])
                config.enable_stream(rs.stream.color, 1280, 720, rs.format.rgb8, 30)
                self.pipelines[i].start(config)
            self.timer.start(30)  # 30 ms interval
    
    def stop_streams(self):
        
        self.plot_timer.stop()
        self.running = False
        self.timer.stop()
        for i in range(3):
            if self.pipelines[i] is not None:
                self.pipelines[i].stop()
                self.pipelines[i] = None
                self.labels[i].clear()
    
    def update_frames(self):
        for i in range(3):
            if self.pipelines[i] is not None:
                frames = self.pipelines[i].wait_for_frames()
                
                color_frame = frames.get_color_frame() 
                frame_array = np.asanyarray(color_frame.get_data())    
                resized_frame = cv2.resize(frame_array, (640,480))

                if self.start_record_camera:
                    self.camera_files[i].write(mp.packb(frame_array, default=mpn.encode))
                
                if color_frame:
                    h, w, ch = resized_frame.shape
                    bytes_per_line = ch * w
                    qt_img = QImage(resized_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.labels[i].setPixmap(QPixmap.fromImage(qt_img))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = VideoStreamApp()
    window.show()
    sys.exit(app.exec())
