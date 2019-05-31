#!/usr/bin/python
# -*- coding: utf-8 -*-

from wifi_server.access_point import AccessPoint
from arduino_communication.serial_communication import ArduinoCommunication
from imutils.video import WebcamVideoStream
from PyQt5 import QtCore, QtWidgets, QtGui
from functools import partial
from collections import deque
import pyqtgraph as pg
import numpy as np
import imutils
import math
import time
import cv2
import os


class MainApp(QtWidgets.QWidget):
    """
    Initialize all constant variables
    """
    # Defining Wiget sizes
    TEXT_SIZE = QtCore.QSize(35, 15)
    SMALL_TEXT_SIZE = QtCore.QSize(26, 15)
    LARGE_TEXT_SIZE = QtCore.QSize(85, 15)
    IMAGE_SIZE = QtCore.QSize(450, 450)
    VIDEO_SIZE = QtCore.QSize(450, 450)
    GRAPH_SIZE = QtCore.QSize(450, 210)
    BUTTON_SIZE = QtCore.QSize(120, 22)
    SLIDER_SIZE = QtCore.QSize(170, 15)
    TEXT_BOX_SIZE = QtCore.QSize(270, 25)
    COMBO_BOX_SIZE = QtCore.QSize(105, 25)

    # Physical model parameters
    BALL_DIAMETER = 0.0022
    BALL_WEIGHT = 0.031
    PLATE_FRICTION = 0.0010
    GRAVITY = -9.81

    # Defining the sample time
    TIME = 0.033

    centers_signal = QtCore.pyqtSignal(tuple, tuple)
    start_signal = QtCore.pyqtSignal(bool)

    def __init__(self, parent=None):
        """
        This is the main app class
        """
        super(MainApp, self).__init__(parent)

        self.tick_high = 0
        self.step = 0.5
        self.joystick_points = deque(maxlen=3)
        self.circle_radius = 50
        self.center_pixels = (0, 0)
        self.move_pattern = "Center"
        # Lower and Upper Threshold values
        self.threshold_ball = [0, 0, 145, 0, 0, 255]
        self.threshold_plate = [0, 178, 0, 255, 255, 218]
        # Defining setpoints
        self.setpoint_mouse = (0, 0)
        self.setpoint_joystick = (0, 0)
        self.setpoint_square = [(-90, -90), (90, -90), (90, 90), (-90, 90)]
        # Arduino input variables
        self.joystick_x = 0
        self.joystick_y = 0
        self.angle_x = 0
        self.angle_y = 0

        self.ip_value = '192.168.12.186'

        self.center_centimeters = (0, 0)
        self.setpoint_centimeters = (0, 0)

        self.without_ball = 0
        self.radius = 0

        self.constant_changed = False

        self.access_point_server = AccessPoint()
        self.start_arduino_connection = ArduinoCommunication()
        self.start_arduino_connection.make_connection(self)
        self.start_arduino_connection.toggle_communication(self)

        self.setupKalmanFilter()
        self.setupUi()
        self.setupGraphs()

    def setupUi(self):
        """
        This function sets up all the Labels used in the widget, and start all threads
        """
        # Initializing the QTimer
        self.timer = QtCore.QTimer(self)

        # Video Widgets
        self.image_label_one = QtWidgets.QLabel()
        self.image_label_one.setFixedSize(self.VIDEO_SIZE)
        self.image_label_two = QtWidgets.QLabel()
        self.image_label_two.setFixedSize(self.VIDEO_SIZE)
        self.image_label_three = QtWidgets.QLabel()
        self.image_label_three.setFixedSize(self.VIDEO_SIZE)

        # Video output ComboBox
        self.combo_box_one = QtWidgets.QComboBox()
        self.combo_box_one.addItem("Webcam")
        self.combo_box_one.addItem("USB Camera")
        self.combo_box_one.addItem("IP Camera")
        self.combo_box_one.setFixedSize(self.COMBO_BOX_SIZE)
        self.combo_box_one.activated[str].connect(self.videoChange)
        self.text_combo_box_one = QtWidgets.QLabel(text='Video Input:')
        self.text_combo_box_one.setFixedSize(self.LARGE_TEXT_SIZE)
        self.text_combo_box_one.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Pattern type ComboBox
        self.combo_box_two = QtWidgets.QComboBox()
        self.combo_box_two.addItem("Center")
        self.combo_box_two.addItem("Mouse")
        self.combo_box_two.addItem("Joystick")
        self.combo_box_two.addItem("Square")
        self.combo_box_two.addItem("Circle")
        self.combo_box_two.addItem("Lissajous")
        self.combo_box_two.setFixedSize(self.COMBO_BOX_SIZE)
        self.combo_box_two.activated[str].connect(self.modeChange)
        self.text_combo_box_two = QtWidgets.QLabel(text='Mode:')
        self.text_combo_box_two.setFixedSize(self.LARGE_TEXT_SIZE)
        self.text_combo_box_two.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Step value ComboBox
        self.combo_box_three = QtWidgets.QComboBox()
        self.combo_box_three.addItem("1")
        self.combo_box_three.addItem("2")
        self.combo_box_three.addItem("3")
        self.combo_box_three.setFixedSize(self.COMBO_BOX_SIZE)
        self.combo_box_three.activated[str].connect(self.stepChange)
        self.text_combo_box_three = QtWidgets.QLabel(text='Step time (s):')
        self.text_combo_box_three.setFixedSize(self.LARGE_TEXT_SIZE)
        self.text_combo_box_three.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Radius value ComboBox
        self.combo_box_four = QtWidgets.QComboBox()
        self.combo_box_four.addItem("2.5")
        self.combo_box_four.addItem("5.0")
        self.combo_box_four.addItem("7.5")
        self.combo_box_four.setFixedSize(self.COMBO_BOX_SIZE)
        self.combo_box_four.activated[str].connect(self.radiusChange)
        self.text_combo_box_four = QtWidgets.QLabel(text='Radius (cm):')
        self.text_combo_box_four.setFixedSize(self.LARGE_TEXT_SIZE)
        self.text_combo_box_four.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Creating the ip line edit box
        self.camera_ip_textbox = QtWidgets.QLineEdit()
        self.camera_ip_textbox.setFixedSize(self.TEXT_BOX_SIZE)
        self.camera_ip_textbox.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.camera_ip_textbox.setText(self.ip_value)
        font = self.camera_ip_textbox.font()
        font.setPointSize(12)
        self.camera_ip_textbox.setFont(font)

        # Creating the ip line edit box label
        self.camera_ip_label = QtWidgets.QLabel(text='Camera IP:')
        self.camera_ip_label.setFixedSize(self.LARGE_TEXT_SIZE)
        self.camera_ip_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Creating the Start/Pause button for the video feed
        self.start_button = QtWidgets.QPushButton("Start")
        self.start_button.setFixedSize(self.BUTTON_SIZE)
        self.start_button.clicked.connect(self.startApp)

        # Creating the Connect/Disconnect for Arduino communication
        self.serial_connect_button = QtWidgets.QPushButton("Serial connect")
        self.serial_connect_button.setFixedSize(self.BUTTON_SIZE)
        self.serial_connect_button.clicked.connect(self.connectSerial)

        # Creating the Quit button
        self.quit_button = QtWidgets.QPushButton("Quit")
        self.quit_button.setFixedSize(self.BUTTON_SIZE)
        self.quit_button.clicked.connect(self.close)

        # Creating the Threshold button for the Widget
        self.thresh_button = QtWidgets.QPushButton("Ball")
        self.thresh_button.setFixedSize(self.BUTTON_SIZE)
        self.thresh_button.clicked.connect(self.changeThresh)

        # Creating the start Acess Point button
        self.access_point_button = QtWidgets.QPushButton("Start server")
        self.access_point_button.setFixedSize(self.BUTTON_SIZE)
        self.access_point_button.clicked.connect(self.toggleAccessPoint)
        if os.name == 'posix':
            self.access_point_button.setEnabled(False)

        # Creating the set ip button
        self.select_ip_button = QtWidgets.QPushButton("Set IP")
        self.select_ip_button.setFixedSize(self.BUTTON_SIZE)
        self.select_ip_button.clicked.connect(self.setVideoIp)

        # Text labels for Sliders type
        self.text_r_low_label = QtWidgets.QLabel(text='B:')
        self.text_r_low_label.setFixedSize(self.SMALL_TEXT_SIZE)
        self.text_r_low_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.text_g_low_label = QtWidgets.QLabel(text='G:')
        self.text_g_low_label.setFixedSize(self.SMALL_TEXT_SIZE)
        self.text_g_low_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.text_b_low_label = QtWidgets.QLabel(text='R:')
        self.text_b_low_label.setFixedSize(self.SMALL_TEXT_SIZE)
        self.text_b_low_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.text_r_high_label = QtWidgets.QLabel(text='B:')
        self.text_r_high_label.setFixedSize(self.SMALL_TEXT_SIZE)
        self.text_r_high_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.text_g_high_label = QtWidgets.QLabel(text='G:')
        self.text_g_high_label.setFixedSize(self.SMALL_TEXT_SIZE)
        self.text_g_high_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.text_b_high_label = QtWidgets.QLabel(text='R:')
        self.text_b_high_label.setFixedSize(self.SMALL_TEXT_SIZE)
        self.text_b_high_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        # Text labels for Sliders values
        self.text_r_low_value_label = QtWidgets.QLabel(text=str(self.threshold_ball[0]))
        self.text_r_low_value_label.setFixedSize(self.TEXT_SIZE)
        self.text_g_low_value_label = QtWidgets.QLabel(text=str(self.threshold_ball[1]))
        self.text_g_low_value_label.setFixedSize(self.TEXT_SIZE)
        self.text_b_low_value_label = QtWidgets.QLabel(text=str(self.threshold_ball[2]))
        self.text_b_low_value_label.setFixedSize(self.TEXT_SIZE)
        self.text_r_high_value_label = QtWidgets.QLabel(text=str(self.threshold_ball[3]))
        self.text_r_high_value_label.setFixedSize(self.TEXT_SIZE)
        self.text_g_high_value_label = QtWidgets.QLabel(text=str(self.threshold_ball[4]))
        self.text_g_high_value_label.setFixedSize(self.TEXT_SIZE)
        self.text_b_high_value_label = QtWidgets.QLabel(text=str(self.threshold_ball[5]))
        self.text_b_high_value_label.setFixedSize(self.TEXT_SIZE)

        # Creating the lower threshold slider for the red color
        self.slider_r_low = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_r_low.setFixedSize(self.SLIDER_SIZE)
        self.slider_r_low.setMinimum(0)
        self.slider_r_low.setMaximum(255)
        self.slider_r_low.setValue(self.threshold_ball[0])
        self.slider_r_low.valueChanged.connect(partial(self.sliderValueChange, number=0,
                                                       text_value_label=self.text_r_low_value_label,
                                                       slider=self.slider_r_low))

        # Creating the lower threshold slider for the green color
        self.slider_g_low = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_g_low.setFixedSize(self.SLIDER_SIZE)
        self.slider_g_low.setMinimum(0)
        self.slider_g_low.setMaximum(255)
        self.slider_g_low.setValue(self.threshold_ball[1])
        self.slider_g_low.valueChanged.connect(partial(self.sliderValueChange, number=1,
                                                       text_value_label=self.text_g_low_value_label,
                                                       slider=self.slider_g_low))

        # Creating the lower threshold slider for the blue color
        self.slider_b_low = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_b_low.setFixedSize(self.SLIDER_SIZE)
        self.slider_b_low.setMinimum(0)
        self.slider_b_low.setMaximum(255)
        self.slider_b_low.setValue(self.threshold_ball[2])
        self.slider_b_low.valueChanged.connect(partial(self.sliderValueChange, number=2,
                                                       text_value_label=self.text_b_low_value_label,
                                                       slider=self.slider_b_low))

        # Creating the upper threshold slider for the red color
        self.slider_r_high = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_r_high.setFixedSize(self.SLIDER_SIZE)
        self.slider_r_high.setMinimum(0)
        self.slider_r_high.setMaximum(255)
        self.slider_r_high.setValue(self.threshold_ball[3])
        self.slider_r_high.valueChanged.connect(partial(self.sliderValueChange, number=3,
                                                        text_value_label=self.text_r_high_value_label,
                                                        slider=self.slider_r_high))

        # Creating the upper threshold slider for the green color
        self.slider_g_high = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_g_high.setFixedSize(self.SLIDER_SIZE)
        self.slider_g_high.setMinimum(0)
        self.slider_g_high.setMaximum(255)
        self.slider_g_high.setValue(self.threshold_ball[4])
        self.slider_g_high.valueChanged.connect(partial(self.sliderValueChange, number=4,
                                                        text_value_label=self.text_g_high_value_label,
                                                        slider=self.slider_g_high))

        # Creating the upper threshold slider for the blue color
        self.slider_b_high = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider_b_high.setFixedSize(self.SLIDER_SIZE)
        self.slider_b_high.setMinimum(0)
        self.slider_b_high.setMaximum(255)
        self.slider_b_high.setValue(self.threshold_ball[5])
        self.slider_b_high.valueChanged.connect(partial(self.sliderValueChange, number=5,
                                                        text_value_label=self.text_b_high_value_label,
                                                        slider=self.slider_b_high))

        # Graph 1
        self.graph_one = pg.GraphicsWindow()
        self.graph_one.setFixedSize(self.GRAPH_SIZE)

        # Graph 2
        self.graph_two = pg.GraphicsWindow()
        self.graph_two.setFixedSize(self.GRAPH_SIZE)

        # Graph 3
        self.graph_three = pg.GraphicsWindow()
        self.graph_three.setFixedSize(self.GRAPH_SIZE)

        # Creating the Layouts
        # Main Layout
        self.main_layout = QtWidgets.QVBoxLayout()
        # Top Layout
        self.top_layout = QtWidgets.QHBoxLayout()
        # Top Left
        self.top_left_layout = QtWidgets.QVBoxLayout()
        self.top_left_top_layout = QtWidgets.QHBoxLayout()
        self.top_left_mid_layout = QtWidgets.QHBoxLayout()
        self.top_left_bot_layout = QtWidgets.QHBoxLayout()
        # Top Mid
        self.top_mid_layout = QtWidgets.QVBoxLayout()
        self.top_mid_top_layout = QtWidgets.QHBoxLayout()
        self.top_mid_mid_layout = QtWidgets.QHBoxLayout()
        self.top_mid_bot_layout = QtWidgets.QHBoxLayout()
        # Top Right
        self.top_right_layout = QtWidgets.QVBoxLayout()
        self.top_right_top_layout = QtWidgets.QHBoxLayout()
        self.top_right_mid_layout = QtWidgets.QHBoxLayout()
        self.top_right_bot_layout = QtWidgets.QHBoxLayout()
        # Mid Layout
        self.mid_layout = QtWidgets.QHBoxLayout()
        # Bot Layout
        self.bot_layout = QtWidgets.QHBoxLayout()
        # Layouts configuration
        # Adding the Top-Left layout widgets
        self.top_left_top_layout.addWidget(self.start_button)
        self.top_left_top_layout.addWidget(self.quit_button)
        self.top_left_mid_layout.addWidget(self.access_point_button)
        self.top_left_mid_layout.addWidget(self.serial_connect_button)
        self.top_left_bot_layout.addWidget(self.thresh_button)
        self.top_left_bot_layout.addWidget(self.select_ip_button)
        # Adding the Top--Mid layout widgets
        self.top_mid_top_layout.addWidget(self.text_combo_box_one)
        self.top_mid_top_layout.addWidget(self.combo_box_one)
        self.top_mid_top_layout.addWidget(self.text_combo_box_two)
        self.top_mid_top_layout.addWidget(self.combo_box_two)
        self.top_mid_mid_layout.addWidget(self.text_combo_box_three)
        self.top_mid_mid_layout.addWidget(self.combo_box_three)
        self.top_mid_mid_layout.addWidget(self.text_combo_box_four)
        self.top_mid_mid_layout.addWidget(self.combo_box_four)
        self.top_mid_bot_layout.addWidget(self.camera_ip_label)
        self.top_mid_bot_layout.addWidget(self.camera_ip_textbox)
        # Adding the Top-Right-Left layout widgets
        self.top_right_top_layout.addWidget(self.text_r_low_label)
        self.top_right_top_layout.addWidget(self.slider_r_low)
        self.top_right_top_layout.addWidget(self.text_r_low_value_label)
        self.top_right_top_layout.addWidget(self.text_r_high_label)
        self.top_right_top_layout.addWidget(self.slider_r_high)
        self.top_right_top_layout.addWidget(self.text_r_high_value_label)
        # Adding the Right-Left-Bot layout widgets
        self.top_right_mid_layout.addWidget(self.text_g_low_label)
        self.top_right_mid_layout.addWidget(self.slider_g_low)
        self.top_right_mid_layout.addWidget(self.text_g_low_value_label)
        self.top_right_mid_layout.addWidget(self.text_g_high_label)
        self.top_right_mid_layout.addWidget(self.slider_g_high)
        self.top_right_mid_layout.addWidget(self.text_g_high_value_label)
        # Adding the Right-Right-Mid layout widgets
        self.top_right_bot_layout.addWidget(self.text_b_low_label)
        self.top_right_bot_layout.addWidget(self.slider_b_low)
        self.top_right_bot_layout.addWidget(self.text_b_low_value_label)
        self.top_right_bot_layout.addWidget(self.text_b_high_label)
        self.top_right_bot_layout.addWidget(self.slider_b_high)
        self.top_right_bot_layout.addWidget(self.text_b_high_value_label)
        # Adding the Mid layout widgets
        self.mid_layout.addWidget(self.image_label_one)
        self.mid_layout.addWidget(self.image_label_two)
        self.mid_layout.addWidget(self.image_label_three)
        # Adding the Bot layout widgets
        self.bot_layout.addWidget(self.graph_one)
        self.bot_layout.addWidget(self.graph_two)
        self.bot_layout.addWidget(self.graph_three)
        # Linking the Top layouts
        self.top_left_layout.addLayout(self.top_left_top_layout)
        self.top_left_layout.addLayout(self.top_left_mid_layout)
        self.top_left_layout.addLayout(self.top_left_bot_layout)
        self.top_mid_layout.addLayout(self.top_mid_top_layout)
        self.top_mid_layout.addLayout(self.top_mid_mid_layout)
        self.top_mid_layout.addLayout(self.top_mid_bot_layout)
        self.top_right_layout.addLayout(self.top_right_top_layout)
        self.top_right_layout.addLayout(self.top_right_mid_layout)
        self.top_right_layout.addLayout(self.top_right_bot_layout)
        self.top_layout.addLayout(self.top_left_layout)
        self.top_layout.addLayout(self.top_mid_layout)
        self.top_layout.addLayout(self.top_right_layout)
        # Linking the Layouts with the main Layout
        self.main_layout.addLayout(self.top_layout)
        self.main_layout.addLayout(self.mid_layout)
        self.main_layout.addLayout(self.bot_layout)
        # Defining the widget layout as the main layout
        self.setLayout(self.main_layout)

    def updateGui(self, frame, black, image):
        """
        This function update the widget custom GUI
        """
        # Setting up the FONT
        FONT = cv2.FONT_HERSHEY_SIMPLEX
        # Drawing the bounding squares in the frame
        cv2.rectangle(frame, (25, 25), (425, 425), (0, 255, 0), 2)

        # Square that limits the lateral GUI
        cv2.rectangle(frame, (500, 10), (630, 470), (0, 255, 0), 1)
        cv2.rectangle(black, (10, 10), (160, 440), (0, 255, 0), 1)
        cv2.rectangle(black, (170, 10), (440, 440), (0, 255, 0), 1)

        cv2.line(image, (self.pts_list[0][0], 0), (self.pts_list[0][0], 480), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (0, self.pts_list[0][1]), (480, self.pts_list[0][1]), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (self.pts_list[1][0], 0), (self.pts_list[1][0], 480), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (0, self.pts_list[1][1]), (480, self.pts_list[1][1]), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (self.pts_list[2][0], 0), (self.pts_list[2][0], 480), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (0, self.pts_list[2][1]), (480, self.pts_list[2][1]), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (self.pts_list[3][0], 0), (self.pts_list[3][0], 480), (0, 255, 0), 1, 8, 0)
        cv2.line(image, (0, self.pts_list[3][1]), (480, self.pts_list[3][1]), (0, 255, 0), 1, 8, 0)

        cv2.circle(image, (self.pts_list[0][0], self.pts_list[0][1]), 5, (0, 0, 255), -1)
        cv2.circle(image, (self.pts_list[1][0], self.pts_list[1][1]), 5, (0, 0, 255), -1)
        cv2.circle(image, (self.pts_list[2][0], self.pts_list[2][1]), 5, (0, 0, 255), -1)
        cv2.circle(image, (self.pts_list[3][0], self.pts_list[3][1]), 5, (0, 0, 255), -1)

        # Circulos limite do CP e SP
        cv2.circle(frame, (int(self.prediction[0][0] + self.IMAGE_SIZE.width()/2),
                           int(self.IMAGE_SIZE.height()/2 - self.prediction[1][0])), int(self.radius), (0, 255, 0), 2)

        cv2.circle(frame, (int(self.prediction[0][0] + self.IMAGE_SIZE.width()/2),
                           int(self.IMAGE_SIZE.height()/2 - self.prediction[1][0])), 5, (0, 0, 255), -1)

        cv2.putText(frame, "CP", (self.prediction[0][0].astype(int) + int(self.IMAGE_SIZE.width()/2 + 10),
                    int(self.IMAGE_SIZE.height()/2 + 20) - self.prediction[1][0].astype(int)),
                    FONT, 0.5, (0, 0, 255), 1)
        cv2.circle(frame, (self.setpoint_pixels[0] + int(self.IMAGE_SIZE.width()/2), int(self.IMAGE_SIZE.height()/2)
                           - self.setpoint_pixels[1]), 5, (255, 0, 0), -1)
        cv2.putText(frame, "SP", (self.setpoint_pixels[0] + int(self.IMAGE_SIZE.width()/2 - 20),
                    int(self.IMAGE_SIZE.height()/2 - 10) - self.setpoint_pixels[1]),
                    FONT, 0.5, (255, 0, 0), 1)

        cv2.line(frame, (25, int(self.IMAGE_SIZE.height()/2 - self.prediction[1][0])),
                        (425, int(self.IMAGE_SIZE.height()/2 - self.prediction[1][0])), (0, 0, 255), 1, 8, 0)
        cv2.line(frame, (int(self.prediction[0][0] + self.IMAGE_SIZE.width()/2), 25),
                        (int(self.prediction[0][0] + self.IMAGE_SIZE.width()/2), 425), (0, 0, 255), 1, 8, 0)

        TEXT_POS_X = [10, 55, 95, 135, 175, 222, 262, 302, 344, 380, 418]
        TEXT_POS_Y = [8, 13, 13, 13, 13, 13, 6, 6, 6, 6, 2]
        for i in range(0, 11):
            cv2.line(frame, (25 + i * 40, 425), (25 + i * 40, 415), (0, 255, 0), 1, 8, 0)
            cv2.line(frame, (25, 25 + i*40), (35, 25 + i * 40), (0, 255, 0), 1, 8, 0)
            cv2.putText(frame, str(int(-10 + 2 * i)), (TEXT_POS_X[i], 440), FONT, 0.3, (0, 255, 0), 1)
            cv2.putText(frame, str(int(10 - 2 * i)), (TEXT_POS_Y[i], 27 + i*40), FONT, 0.3, (0, 255, 0), 1)

        # Gui #1
        cv2.putText(black, "Ball Speed", (15, 30), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "dX: %+.2f m/s" % (self.d_x), (15, 50), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "dY: %+.2f m/s" % (self.d_y), (15, 65), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Set Point", (15, 85), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "X: %+.2f Cm" % (self.setpoint_centimeters[0]), (15, 105), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Y: %+.2f Cm" % (self.setpoint_centimeters[1]), (15, 120), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Current Point", (15, 140), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "X: %+.2f Cm" % (self.center_centimeters[0]), (15, 160), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Y: %+.2f Cm" % (self.center_centimeters[1]), (15, 175), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Error", (15, 195), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "X: %+.2f Cm" % (self.error_centimeters[0]), (15, 215), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Y: %+.2f Cm" % (self.error_centimeters[1]), (15, 230), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Mode", (15, 250), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "{}".format(self.move_pattern), (15, 270), FONT, 0.5, (255, 255, 0), 1)

        # Criando os gauges do gui lateral
        angle_x_text_size = int(cv2.getTextSize(str(int(self.angle_x)), FONT, 0.6, 1)[0][0] / 2)
        angle_y_text_size = int(cv2.getTextSize(str(int(self.angle_y)), FONT, 0.6, 1)[0][0] / 2)
        cv2.putText(black, "X-axis angle", (15, 292), FONT, 0.5, (0, 255, 0), 1)
        cv2.ellipse(black, (85, 350), (49, 49), 0, 180, 360, (255, 255, 255), -1)
        cv2.ellipse(black, (85, 350), (50, 50), 0, int(270 + int(3 * self.angle_x)), 180, (255, 0, 0), -1)
        cv2.ellipse(black, (85, 350), (30, 30), 0, 180, 360, (0, 0, 0), -1)
        cv2.putText(black, "{}".format(int(self.angle_x)), (85 - angle_x_text_size, 350), FONT, 0.6, (0, 255, 0), 1)
        cv2.putText(black, "Y-axis angle", (15, 370), FONT, 0.5, (0, 255, 0), 1)
        cv2.ellipse(black, (85, 430), (49, 49), 0, 180, 360, (255, 255, 255), -1)
        cv2.ellipse(black, (85, 430), (50, 50), 0, int(270 + int(3 * self.angle_y)), 180, (0, 0, 255), -1)
        cv2.ellipse(black, (85, 430), (30, 30), 0, 180, 360, (0, 0, 0), -1)
        cv2.putText(black, "{}".format(int(self.angle_y)), (85 - angle_y_text_size, 430), FONT, 0.6, (0, 255, 0), 1)

        # Gui #2
        cv2.putText(black, "System settings", (225, 35), FONT, 0.6, (0, 255, 0), 1)
        cv2.putText(black, "Mechanical constants", (180, 60), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Ball diameter: {} m".format(self.BALL_DIAMETER), (180, 85), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Ball weight: {} Kg".format(self.BALL_WEIGHT), (180, 105), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Plate friction: {} N/m".format(self.PLATE_FRICTION), (180, 125), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Gravity: {} m/s^2".format(self.GRAVITY), (180, 145), FONT, 0.5, (0, 255, 0), 1)

        # Marcador de Tempo para debugging
        # cv2.putText(black, "Sample Time: {0:.3f} s".format(self.loop_time), (180, 290), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "WiFi Server Status:", (180, 260), FONT, 0.5, (0, 255, 0), 1)
        if (self.access_point_button.text() == 'Stop server'):
            cv2.putText(black, "Online", (335, 260), FONT, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(black, "Offline", (335, 260), FONT, 0.5, (255, 0, 0), 1)
        cv2.putText(black, "Serial Status:", (180, 290), FONT, 0.5, (0, 255, 0), 1)
        if (self.serial_connect_button.text() == 'Serial disconnect'):
            cv2.putText(black, "Connected", (290, 290), FONT, 0.5, (0, 255, 0), 1)
        else:
            cv2.putText(black, "Disconnected", (290, 290), FONT, 0.5, (255, 0, 0), 1)
        cv2.putText(black, "Sample Time: {} ms".format(int(1000 * self.arduino_communication_time)), (180, 330),
                    FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Total Time: {0:.2f} s".format(time.time() - self.start_time), (180, 360),
                    FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "UFPE", (180, 390), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "DES - CTG", (180, 410), FONT, 0.5, (0, 255, 0), 1)
        cv2.putText(black, "Wilton O. de Souza Filho", (180, 430), FONT, 0.5, (0, 255, 0), 1)

    def setupGraphs(self):
        """
        This function sets up all configuration for the live graphs displayed on the widget
        """
        SAMPLE_INTERVAL = 1
        SAMPLE_WINDOW = 100

        # Creating all the 3 graphs and setting their titles
        self.my_plot_one = self.graph_one.addPlot(title='Total Error')
        self.my_plot_two = self.graph_two.addPlot(title='X - Set Point / Current Point')
        self.my_plot_three = self.graph_three.addPlot(title='Y - Set Point / Current Point')

        # self._interval = int(SAMPLE_INTERVAL*1000)
        bufsize = int(SAMPLE_WINDOW/SAMPLE_INTERVAL)
        self.data_buffer_one = deque([0.0]*bufsize, bufsize)
        self.data_buffer_two = deque([0.0]*bufsize, bufsize)
        self.data_buffer_three = deque([0.0]*bufsize, bufsize)
        self.data_buffer_four = deque([0.0]*bufsize, bufsize)
        self.data_buffer_five = deque([0.0]*bufsize, bufsize)
        self.data_buffer_six = deque([0.0]*bufsize, bufsize)
        # Criando variável que armazena a quatidade de amostras a serem mostradas (Range do eixo X)
        self.x = np.linspace(-SAMPLE_WINDOW, 0.0, bufsize)
        # Criando variáveis que armazenarão os dados a serem plotados para cada variável

        self.my_plot_one.showGrid(x=True, y=True)
        self.my_plot_one.setLabel('left', 'Position', 'Cm')
        self.my_plot_one.setLabel('bottom', 'Samples', 'n')
        self.my_plot_one.setYRange(-22, 22)

        self.my_plot_two.showGrid(x=True, y=True)
        self.my_plot_two.setLabel('left', 'Position', 'Cm')
        self.my_plot_two.setLabel('bottom', 'Samples', 'n')
        self.my_plot_two.setYRange(-12, 12)

        self.my_plot_three.showGrid(x=True, y=True)
        self.my_plot_three.setLabel('left', 'Position', 'Cm')
        self.my_plot_three.setLabel('bottom', 'Samples', 'n')
        self.my_plot_three.setYRange(-12, 12)

        self.curve_one = self.my_plot_one.plot(self.x, self.data_buffer_one,   pen=pg.mkPen((255, 0, 0), width=2))
        self.curve_two = self.my_plot_one.plot(self.x, self.data_buffer_two,   pen=pg.mkPen((0, 0, 255), width=2))
        self.curve_three = self.my_plot_two.plot(self.x, self.data_buffer_three, pen=pg.mkPen((255, 0, 0), width=2))
        self.curve_four = self.my_plot_two.plot(self.x, self.data_buffer_four,  pen=pg.mkPen((0, 0, 255), width=2))
        self.curve_five = self.my_plot_three.plot(self.x, self.data_buffer_five,  pen=pg.mkPen((255, 0, 0), width=2))
        self.curve_six = self.my_plot_three.plot(self.x, self.data_buffer_six,   pen=pg.mkPen((0, 0, 255), width=2))

        # Adicionando as Legendas no Gráfico 1
        self.legend_one = pg.LegendItem((30, 10), offset=(70, 10))
        self.legend_one.setParentItem(self.my_plot_one.graphicsItem())
        self.legend_one.addItem(self.curve_one, 'X ')
        self.legend_one.addItem(self.curve_two, 'Y ')

        # Adicionando as Legendas no Gráfico 2
        self.legend_two = pg.LegendItem((30, 10), offset=(70, 30))
        self.legend_two.setParentItem(self.my_plot_two.graphicsItem())
        self.legend_two.addItem(self.curve_three, 'X SP')
        self.legend_two.addItem(self.curve_four, 'X CP')

        # Adicionando as Legendas no Gráfico 3
        self.legend_three = pg.LegendItem(size=(10, 10), offset=(70, 30))
        self.legend_three.setParentItem(self.my_plot_three.graphicsItem())
        self.legend_three.addItem(self.curve_five, 'Y SP')
        self.legend_three.addItem(self.curve_six, 'Y CP')

    def startApp(self):
        """
        This function start all threads and starts the Widget
        """
        # If the Start button is in the mode "Start"
        if self.start_button.text() == 'Start':

            # To prevent any not connected device error, start the app always with video feed from the embedded webcam
            self.vs = WebcamVideoStream(src=0).start()
            self.current_output = 0

            if self.start_arduino_connection.is_connected:
                self.start_signal.emit(True)

            # Iniciando o QTimer
            self.timer.timeout.connect(self.videoProcessing)
            self.timer.timeout.connect(self.updateWidgets)
            self.timer.start(self.TIME)

            self.start_button.setText("Pause")
            self.serial_connect_button.setEnabled(False)
            self.access_point_button.setEnabled(False)
            self.quit_button.setEnabled(False)

            # Iniciando o armazenamento do temporizador
            self.start_time = time.time()
            self.previous_time = self.start_time
            self.loop_time = 0
            self.update_widgets_time = 0
            self.video_processing_time = 0
            self.arduino_communication_time = 0

        # Executar quando apertar o botão Pause
        elif self.start_button.text() == 'Pause':
            self.timer.stop()
            self.start_button.setText("Resume")
            if self.start_arduino_connection.is_connected:
                self.start_signal.emit(False)
            self.serial_connect_button.setEnabled(True)
            if os.name != 'posix':
                self.access_point_button.setEnabled(True)
            self.quit_button.setEnabled(True)

        # Executar quando apertar o botão Start
        else:
            self.timer.start(self.TIME)
            self.start_button.setText("Pause")
            if self.start_arduino_connection.is_connected:
                self.start_signal.emit(True)
            self.serial_connect_button.setEnabled(False)
            self.access_point_button.setEnabled(False)
            self.quit_button.setEnabled(False)

    def connectSerial(self):
        """
        This function handles the arduino serial connection using the QThread method
        """
        if self.serial_connect_button.text() == 'Serial connect' and self.start_button.text() != 'Pause':
            # self.start_arduino_connection = ArduinoComunication()
            self.start_arduino_connection.start()
            self.start_arduino_connection.arduino_data.connect(self.get_data_from_arduino)
            self.serial_connect_button.setText("Serial disconnect")

        elif self.serial_connect_button.text() == 'Serial disconnect':
            self.start_arduino_connection.stop()
            # del self.start_arduino_connection
            self.serial_connect_button.setText("Serial connect")

    def toggleAccessPoint(self):

        if os.name == 'posix':
            print("This Access Point module works only on Linux, sorry!")
        else:
            if self.access_point_button.text() == "Start server":
                self.access_point_button.setText("Stop server")
                self.access_point_server.start()
            else:
                self.access_point_button.setText("Start server")
                self.access_point_server.stop()

    def changeThresh(self):
        """
        This function handles the selection of the threshold frame to be displayed
        """
        sliders = [self.slider_r_low, self.slider_g_low, self.slider_b_low,
                   self.slider_r_high, self.slider_g_high, self.slider_b_high]

        labels = [self.text_r_low_value_label, self.text_g_low_value_label, self.text_b_low_value_label,
                  self.text_r_high_value_label, self.text_g_high_value_label, self.text_b_high_value_label]

        if self.thresh_button.text() == 'Ball':
            self.thresh_button.setText("Plate")

            for index, (slider, label) in enumerate(zip(sliders, labels)):
                slider.setValue(self.threshold_plate[index])
                label.setText(str(self.threshold_plate[index]))

        else:
            self.thresh_button.setText("Ball")

            for index, (slider, label) in enumerate(zip(sliders, labels)):
                slider.setValue(self.threshold_ball[index])
                label.setText(str(self.threshold_ball[index]))

    def handleClose(self):
        if self.timer.isActive():
            print("Stopping Timer...")
            self.timer.stop()
            print("Done!")
        if self.access_point_button.text() == 'Stop server':
            print("Shutting down the WiFi Server")
            self.access_point_server.stop()
            print("Done!")
        if (self.start_button.text() != 'Start'):
            print("Stopping Video Stream Thread...")
            self.vs.stop()
            print("Done!")
        if (self.serial_connect_button.text() == 'Serial disconnect'):
            print("Stopping Serial Data Communication...")
            self.start_arduino_connection.stop()
            print("Done!")
        print("Exiting...")
        time.sleep(1)

    def closeEvent(self, event):
        """
        This function handles the close event (Pop up message to exit the application)
        """
        reply = QtWidgets.QMessageBox.question(self, 'Message', "Are you sure to quit?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                                               QtWidgets.QMessageBox.No)

        if reply == QtWidgets.QMessageBox.Yes:
            self.handleClose()
            event.accept()
        else:
            event.ignore()

    def videoChange(self, text):
        """
        This function handles the video input change from the combobox
        """
        if self.start_button.text() != 'Start':
            if text == 'Webcam' and self.current_output != 0:
                self.vs.stop()
                self.vs = WebcamVideoStream(src=0).start()
                self.current_output = 0
            elif text == 'USB Camera' and self.current_output != 1:
                self.vs.stop()
                self.vs = WebcamVideoStream(src=1).start()
                self.current_output = 1
            elif text == 'IP Camera' and self.current_output != 2:
                self.vs.stop()
                website = 'http://' + self.ip_value + ':8080/video'
                self.vs = WebcamVideoStream(src=website).start()
                self.current_output = 2
            else:
                print("This video is already selected")

    def setVideoIp(self):
        self.ip_value = self.camera_ip_textbox.text()

    def modeChange(self, text):
        """
        This function handles the mode change from the combobox
        """
        self.move_pattern = text

    def stepChange(self, text):
        """
        This function handles the change on step size
        """
        self.step = int(text)

    def radiusChange(self, text):
        """
        This function handles the change on radius size
        """
        if text == '2.5':
            self.circle_radius = 50
        elif text == '5.0':
            self.circle_radius = 100
        elif text == '7.5':
            self.circle_radius = 150

    def sliderValueChange(self, number=None, text_value_label=None, slider=None):
        """
        This function handles the value change of the sliders
        """
        if self.thresh_button.text() == 'Ball':
            self.threshold_ball[number] = slider.value()
            text_value_label.setText(str(self.threshold_ball[number]))
        else:
            self.threshold_plate[number] = slider.value()
            text_value_label.setText(str(self.threshold_plate[number]))

    def setSetpoint(self):
        """
        This function sets the correct setpoint variable according to the choosen mode
        """
        if self.move_pattern == 'Center':
            self.setpoint_pixels = (0, 0)
        elif self.move_pattern == 'Mouse':
            self.setpoint_pixels = self.setpoint_mouse
        elif self.move_pattern == 'Joystick':
            self.setpoint_pixels = self.setpoint_joystick
        elif self.move_pattern == 'Square':
            self.setpoint_pixels = self.setpoint_square[int(((time.time() - self.start_time)/4) % 4)]
        elif self.move_pattern == 'Circle':
            pointX = int(self.circle_radius * math.cos(self.step/3 * (time.time() - self.start_time) * math.pi))
            pointY = int(self.circle_radius * math.sin(self.step/3 * (time.time() - self.start_time) * math.pi))
            self.setpoint_pixels = (pointX, pointY)
        elif self.move_pattern == 'Lissajous':
            pointX = int(120 * math.cos(self.step/4 * (time.time() - self.start_time) * math.pi))
            pointY = int(80 * math.sin(2 * self.step/4 * (time.time() - self.start_time) * math.pi))
            self.setpoint_pixels = (pointX, pointY)

    def updateGraph(self, list):
        """
        This function updates all three graphs data
        """
        # Armazenando os dados recebidos pela função nos buffers
        self.data_buffer_one.append(list[0])
        self.data_buffer_two.append(list[1])
        self.data_buffer_three.append(list[2])
        self.data_buffer_four.append(list[3])
        self.data_buffer_five.append(list[4])
        self.data_buffer_six.append(list[5])
        # Atualizando as variáveis de curva x e y de cada gráfico
        self.curve_one.setData(self.x, self.data_buffer_one)
        self.curve_two.setData(self.x, self.data_buffer_two)
        self.curve_three.setData(self.x, self.data_buffer_three)
        self.curve_four.setData(self.x, self.data_buffer_four)
        self.curve_five.setData(self.x, self.data_buffer_five)
        self.curve_six.setData(self.x, self.data_buffer_six)

    def updateJoystick(self, joystick_x, joystick_y):
        """
        This function updates the points of the joystick setpoint variable
        """
        self.joystick_points.appendleft((joystick_x, joystick_y))
        xList, yList = zip(*self.joystick_points)
        self.setpoint_joystick = (int(np.mean(xList)), int(np.mean(yList)))

    def pixelToCentimeter(self, px_value):
        """
        This function converts the value from pixels to centimeters
        """
        return(round(0.05 * px_value[0], 2), round(0.05 * px_value[1], 2))

    def imageToQimage(self, image):
        """
        This function converts the processed frame to a QtGui.QImage, which is needed to be displayed on the widget
        """
        height, width, __ = image.shape
        bytes_per_line = 3 * width
        q_image = QtGui.QImage(image.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
        return(q_image)

    def setupKalmanFilter(self):
        """
        This function sets up the Kalman Filter parameters
        """
        self.kalman = cv2.KalmanFilter(4, 2)
        self.kalman.measurementMatrix = np.array([[1, 0, 0, 0],
                                                  [0, 1, 0, 0]], np.float32)

        self.kalman.transitionMatrix = np.array([[1, 0, 1, 0],
                                                 [0, 1, 0, 1],
                                                 [0, 0, 1, 0],
                                                 [0, 0, 0, 1]], np.float32)

        self.kalman.processNoiseCov = np.array([[1, 0, 0, 0],
                                                [0, 1, 0, 0],
                                                [0, 0, 1, 0],
                                                [0, 0, 0, 1]], np.float32) * 0.03

        self.prediction = np.zeros((2, 1), np.float32)

    def mousePressEvent(self, event):
        """
        This function handles the mouse press event, to setting the setpoint in mouse mode
        """
        if event.button() == QtCore.Qt.LeftButton:
            if (493 < event.x() < 893) and (121 < event.y() < 521) and (self.move_pattern == 'Mouse'):
                valueX = event.x() - 693
                valueY = -event.y() + 321
                self.setpoint_mouse = (valueX, valueY)

    def videoProcessing(self):
        """
        This function does all the video processing, wich includes:
        tracking the ball, tracking the corners of the moving plate, and apllying all the filters
        """
        tick_one = cv2.getTickCount()
        # Capture the Camera Frame
        frame = self.vs.read()
        frame = frame[15:465, 95:545]
        frame = imutils.rotate(frame, 90)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.image = frame.copy()
        blurred_rgb = cv2.medianBlur(frame, 5)

        # Create a Kernel
        kernel = np.ones((5, 5), np.uint8)
        # Create and process the mask, which will show a binary image
        mask_rgb = cv2.inRange(blurred_rgb, tuple(self.threshold_plate[0:3]), tuple(self.threshold_plate[3:6]))
        mask_rgb = cv2.morphologyEx(mask_rgb, cv2.MORPH_CLOSE, kernel)
        mask_rgb[0:450, 120:330] = [0]
        mask_rgb[120:330, 0:450] = [0]

        self.mask_3ch_rgb = cv2.cvtColor(mask_rgb, cv2.COLOR_GRAY2BGR)

        contours, _ = cv2.findContours(mask_rgb.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        self.pts_list = [[0, 0], [0, 0], [0, 0], [0, 0]]
        for contour in contours:
            M = cv2.moments(contour)
            if (M['m00'] > 200):
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])
                if (cx < 150):
                    if (cy < 120):
                        self.pts_list[0][0] = int(cx)
                        self.pts_list[0][1] = int(cy)
                    else:
                        self.pts_list[3][0] = int(cx)
                        self.pts_list[3][1] = int(cy)
                else:
                    if (cy < 150):
                        self.pts_list[1][0] = int(cx)
                        self.pts_list[1][1] = int(cy)
                    else:
                        self.pts_list[2][0] = int(cx)
                        self.pts_list[2][1] = int(cy)

        points_one = np.float32([[self.pts_list[0][0], self.pts_list[0][1]],
                                 [self.pts_list[1][0], self.pts_list[1][1]],
                                 [self.pts_list[2][0], self.pts_list[2][1]],
                                 [self.pts_list[3][0], self.pts_list[3][1]]])
        points_two = np.float32([[45, 45], [405, 45], [405, 405], [45, 405]])

        self.black = np.zeros((450, 450, 3), np.uint8)
        perspective = cv2.getPerspectiveTransform(points_one, points_two)
        self.warped = cv2.warpPerspective(frame, perspective, (450, 450))

        warped_scrot = self.warped[30:420, 30:420]

        blur = cv2.medianBlur(warped_scrot, 5)

        gray = cv2.cvtColor(blur, cv2.COLOR_BGR2GRAY)

        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 500, param1=60, param2=20, minRadius=15, maxRadius=40)

        if circles is not None:
            self.without_ball = 0
            x = int(circles[0][0][0]) + 30
            y = int(circles[0][0][1]) + 30
            radius = circles[0][0][2]
            self.center_pixels = np.array([np.float32(x - self.IMAGE_SIZE.width()/2),
                                           np.float32(self.IMAGE_SIZE.height()/2 - y)], np.float32)
            if 190 > self.center_pixels[0] > -190 and 190 > self.center_pixels[1] > -190:
                self.radius = radius
                self.kalman.correct(self.center_pixels)
                self.prediction = self.kalman.predict()

        else:
            # If lost tracking of the ball, use kalman prediction for a certain period of time
            if self.without_ball < 20:
                self.prediction = self.kalman.predict()
                self.without_ball += 1
            else:
                self.radius = 0
                self.prediction[0][0] = 0
                self.prediction[1][0] = 0

        # Updating the point array
        self.d_x = round(self.prediction[2][0], 2)
        self.d_y = round(self.prediction[3][0], 2)

        # Updating Set Point according to choosen mode
        self.setSetpoint()
        self.error_pixels = (self.setpoint_pixels[0] - self.prediction[0][0],
                             self.setpoint_pixels[1] - self.prediction[1][0])

        # Centimeters conversion
        self.error_centimeters = self.pixelToCentimeter(self.error_pixels)
        self.center_centimeters = self.pixelToCentimeter((self.prediction[0][0], self.prediction[1][0]))
        self.setpoint_centimeters = self.pixelToCentimeter(self.setpoint_pixels)

        self.coordinate_values = (self.error_centimeters, self.center_centimeters, self.setpoint_centimeters)

        self.centers_signal.emit(self.center_centimeters, self.setpoint_centimeters)

        tick_two = cv2.getTickCount()
        self.video_processing_time = (tick_two - tick_one)/cv2.getTickFrequency()

    def get_data_from_arduino(self, data):
        """
        This function handles the data sent from the arduino communication QThread
        """
        self.angle_x = data[0]
        self.angle_y = data[1]
        self.joystick_x = data[2]
        self.joystick_y = data[3]
        self.arduino_communication_time = data[4]

    def get_arduino_data(self, application_object):
        application_object.arduino_data.connect(self.get_data_from_arduino)

    def updateWidgets(self):
        initial_time = time.time()
        self.updateJoystick(self.joystick_x, self.joystick_y)

        self.updateGraph([self.error_centimeters[0], self.error_centimeters[1],
                         self.setpoint_centimeters[0], self.center_centimeters[0],
                         self.setpoint_centimeters[1], self.center_centimeters[1]])

        self.updateGui(self.warped, self.black, self.image)

        if self.thresh_button.text() == 'Ball':
            image_one = self.imageToQimage(self.image)
        else:
            image_one = self.imageToQimage(self.mask_3ch_rgb)

        image_two = self.imageToQimage(self.warped)
        image_three = self.imageToQimage(self.black)

        # Update the QtWidgets.QLabel Widget with all processed images
        self.image_label_one.setPixmap(QtGui.QPixmap.fromImage(image_one))
        self.image_label_two.setPixmap(QtGui.QPixmap.fromImage(image_two))
        self.image_label_three.setPixmap(QtGui.QPixmap.fromImage(image_three))

        final_time = time.time()
        self.update_widgets_time = final_time - initial_time