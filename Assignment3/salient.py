#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel, QPushButton, QTextEdit
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse
import json

import vtk_colorbar
from vtk_colorbar import colorbar_param, colorbar

frame_counter = 0

def save_frame(window, log):
    global frame_counter
    global args
    file_name = args.output + str(frame_counter).zfill(5) + ".png"
    image = vtk.vtkWindowToImageFilter()
    image.SetInput(window)
    png_writer = vtk.vtkPNGWriter()
    png_writer.SetInputConnection(image.GetOutputPort())
    png_writer.SetFileName(file_name)
    window.Render()
    png_writer.Write()
    frame_counter += 1
    log.insertPlainText('Exported {}\n'.format(file_name))

def print_camera_settings(camera, text_window, log):
    text_window.setHtml("<div style='font-weight:bold'>Camera settings:</div><p><ul><li><div style='font-weight:bold'>Position:</div> {0}</li><li><div style='font-weight:bold'>Focal point:</div> {1}</li><li><div style='font-weight:bold'>Up vector:</div> {2}</li><li><div style='font-weight:bold'>Clipping range:</div> {3}</li></ul>".format(camera.GetPosition(), camera.GetFocalPoint(),camera.GetViewUp(),camera.GetClippingRange()))
    log.insertPlainText('Updated camera info\n')

def save_camera_to_json(camera, log, filename="camera.json"):
    camera_data = {
        "Position": camera.GetPosition(),
        "FocalPoint": camera.GetFocalPoint(),
        "ViewUp": camera.GetViewUp(),
        "ClippingRange": camera.GetClippingRange(),
        "ViewAngle": camera.GetViewAngle(),
        "ParallelScale": camera.GetParallelScale()
    }
    for key in camera_data:
        if isinstance(camera_data[key], tuple):
            camera_data[key] = list(camera_data[key])
    with open(filename, "w") as f:
        json.dump(camera_data, f, indent=4)
    log.insertPlainText('Saved camera info\n')

def load_camera_from_json(camera, filename):
    with open(filename, "r") as f:
        camera_data = json.load(f)
    camera.SetPosition(camera_data["Position"])
    camera.SetFocalPoint(camera_data["FocalPoint"])
    camera.SetViewUp(camera_data["ViewUp"])
    camera.SetClippingRange(camera_data["ClippingRange"])
    camera.SetViewAngle(camera_data["ViewAngle"])
    camera.SetParallelScale(camera_data["ParallelScale"])

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName('The Main Window')
        MainWindow.setWindowTitle('Salient Isovalues')
        self.centralWidget = QWidget(MainWindow)
        self.gridlayout = QGridLayout(self.centralWidget)
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        self.slider_isovalue = QSlider()
        self.push_screenshot = QPushButton()
        self.push_screenshot.setText('Save screenshot')
        self.push_camera = QPushButton()
        self.push_camera.setText('Update camera info')
        self.push_quit = QPushButton()
        self.push_quit.setText('Quit')
        self.save_camera = QPushButton()
        self.save_camera.setText('Save camera info')
        self.camera_info = QTextEdit()
        self.camera_info.setReadOnly(True)
        self.camera_info.setAcceptRichText(True)
        self.camera_info.setHtml("<div style='font-weight: bold'>Camera settings</div>")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.isovalue_label = QLabel("Isovalue")
        self.x_clip_label = QLabel("X Clip")
        self.x_clip_slider = QSlider()
        self.y_clip_label = QLabel("Y Clip")
        self.y_clip_slider = QSlider()
        self.z_clip_label = QLabel("Z Clip")
        self.z_clip_slider = QSlider()

        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 5, 5)
        self.gridlayout.addWidget(self.isovalue_label, 5, 0, 1, 1)
        self.gridlayout.addWidget(self.slider_isovalue, 5, 1, 1, 4)
        self.gridlayout.addWidget(self.x_clip_label, 6, 0, 1, 1)
        self.gridlayout.addWidget(self.x_clip_slider, 6, 1, 1, 4)
        self.gridlayout.addWidget(self.y_clip_label, 7, 0, 1, 1)
        self.gridlayout.addWidget(self.y_clip_slider, 7, 1, 1, 4)
        self.gridlayout.addWidget(self.z_clip_label, 8, 0, 1, 1)
        self.gridlayout.addWidget(self.z_clip_slider, 8, 1, 1, 4)
        self.gridlayout.addWidget(self.push_screenshot, 0, 5, 1, 2)
        self.gridlayout.addWidget(self.push_camera, 1, 5, 1, 2)
        self.gridlayout.addWidget(self.camera_info, 2, 5, 2, 2)
        self.gridlayout.addWidget(self.log, 4, 5, 4, 2)
        self.gridlayout.addWidget(self.save_camera, 3, 5, 1, 2)
        self.gridlayout.addWidget(self.push_quit, 8, 5, 1, 2)
        MainWindow.setCentralWidget(self.centralWidget)

class PyQtDemo(QMainWindow):
    def __init__(self, args, parent=None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.args = args
        self.scalar_volume = self.read_data()
        self.init_isovalue()
        self.init_clipping()
        self.contour = self.apply_contour_filter(self.scalar_volume, self.isovalue)
        self.setup_clipping_filters()
        self.contourMapper = self.to_mapper(self.clip_z)
        self.colormap = self.create_colormap()
        self.contourMapper.SetLookupTable(self.colormap)
        self.contourMapper.SetScalarRange(self.min_iso, self.max_iso)
        self.contourActor = self.to_actor(self.contourMapper)
        self.color_bar = self.create_color_bar()
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(self.contourActor)
        self.ren.AddActor(self.color_bar.get())
        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        if args.camera:
            load_camera_from_json(self.ren.GetActiveCamera(), args.camera)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()
        self.setup_sliders()
        self.connect_callbacks()

    def read_data(self):
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(self.args.input)
        reader.Update()
        return reader

    def init_isovalue(self):
        r = self.scalar_volume.GetOutput().GetScalarRange()
        if self.args.range:
            self.min_iso = self.args.range[0]
            self.max_iso = self.args.range[1]
        else:
            self.min_iso, self.max_iso = r
        self.isovalue = self.args.val if self.args.val is not None else (self.min_iso + self.max_iso) / 2
        self.isovalue = max(self.min_iso, min(self.max_iso, self.isovalue))

    def init_clipping(self):
        bounds = self.scalar_volume.GetOutput().GetBounds()
        self.x_min, self.x_max = bounds[0], bounds[1]
        self.y_min, self.y_max = bounds[2], bounds[3]
        self.z_min, self.z_max = bounds[4], bounds[5]
        if self.args.clip:
            self.x_clip = max(self.x_min, min(self.x_max, self.args.clip[0]))
            self.y_clip = max(self.y_min, min(self.y_max, self.args.clip[1]))
            self.z_clip = max(self.z_min, min(self.z_max, self.args.clip[2]))
        else:
            self.x_clip = self.x_min
            self.y_clip = self.y_min
            self.z_clip = self.z_min

    def setup_clipping_filters(self):
        self.clip_x_plane = vtk.vtkPlane()
        self.clip_x_plane.SetNormal(1, 0, 0)
        self.clip_x_plane.SetOrigin(self.x_clip, 0, 0)
        self.clip_x = vtk.vtkClipPolyData()
        self.clip_x.SetClipFunction(self.clip_x_plane)
        self.clip_x.SetInputConnection(self.contour.GetOutputPort())

        self.clip_y_plane = vtk.vtkPlane()
        self.clip_y_plane.SetNormal(0, 1, 0)
        self.clip_y_plane.SetOrigin(0, self.y_clip, 0)
        self.clip_y = vtk.vtkClipPolyData()
        self.clip_y.SetClipFunction(self.clip_y_plane)
        self.clip_y.SetInputConnection(self.clip_x.GetOutputPort())

        self.clip_z_plane = vtk.vtkPlane()
        self.clip_z_plane.SetNormal(0, 0, 1)
        self.clip_z_plane.SetOrigin(0, 0, self.z_clip)
        self.clip_z = vtk.vtkClipPolyData()
        self.clip_z.SetClipFunction(self.clip_z_plane)
        self.clip_z.SetInputConnection(self.clip_y.GetOutputPort())

    def apply_contour_filter(self, geometry, isovalue):
        surface = vtk.vtkContourFilter()
        surface.SetInputConnection(geometry.GetOutputPort())
        surface.SetValue(0, isovalue)
        return surface

    def create_colormap(self):
        lut = vtk.vtkLookupTable()
        lut.SetHueRange(0.6667, 0.0)
        lut.SetSaturationRange(1.0, 1.0)
        lut.SetValueRange(1.0, 1.0)
        lut.SetRange(self.min_iso, self.max_iso)
        lut.Build()
        return lut

    def create_color_bar(self):
        params = colorbar_param(
            title='Scalar Value',
            title_col=[1, 1, 1],
            label_col=[1, 1, 1],
            pos=[0.85, 0.2],
            width=60,
            height=300,
            nlabels=5,
            font_size=14,
            title_font_size=16
        )
        return vtk_colorbar.colorbar(self.colormap, params)

    def to_mapper(self, source):
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(source.GetOutputPort())
        mapper.ScalarVisibilityOn()
        return mapper

    def to_actor(self, mapper):
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        return actor

    def setup_sliders(self):
        self.ui.slider_isovalue.setOrientation(QtCore.Qt.Horizontal)
        self.ui.slider_isovalue.setMinimum(0)
        self.ui.slider_isovalue.setMaximum(1000)
        iso_val = int(((self.isovalue - self.min_iso) / (self.max_iso - self.min_iso)) * 1000 if (self.max_iso > self.min_iso) else 0)
        self.ui.slider_isovalue.setValue(iso_val)
        self.ui.isovalue_label.setText(f"Isovalue: {self.isovalue:.2f}")

        self.setup_clip_slider(self.ui.x_clip_slider, self.x_clip, self.x_min, self.x_max, self.ui.x_clip_label, "X Clip: {:.2f}")
        self.setup_clip_slider(self.ui.y_clip_slider, self.y_clip, self.y_min, self.y_max, self.ui.y_clip_label, "Y Clip: {:.2f}")
        self.setup_clip_slider(self.ui.z_clip_slider, self.z_clip, self.z_min, self.z_max, self.ui.z_clip_label, "Z Clip: {:.2f}")

    def setup_clip_slider(self, slider, clip_val, data_min, data_max, label, label_text):
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setMinimum(0)
        slider.setMaximum(1000)
        if data_max > data_min:
            slider_val = int(((clip_val - data_min) / (data_max - data_min)) * 1000)
            slider.setValue(slider_val)
        label.setText(label_text.format(clip_val))

    def connect_callbacks(self):
        self.ui.slider_isovalue.valueChanged.connect(self.isovalue_callback)
        self.ui.x_clip_slider.valueChanged.connect(lambda v: self.clip_callback(v, 'x'))
        self.ui.y_clip_slider.valueChanged.connect(lambda v: self.clip_callback(v, 'y'))
        self.ui.z_clip_slider.valueChanged.connect(lambda v: self.clip_callback(v, 'z'))
        self.ui.push_screenshot.clicked.connect(self.screenshot_callback)
        self.ui.push_camera.clicked.connect(self.camera_callback)
        self.ui.save_camera.clicked.connect(self.save_camera_callback)
        self.ui.push_quit.clicked.connect(self.quit_callback)

    def isovalue_callback(self, val):
        self.isovalue = self.min_iso + (val / 1000.0) * (self.max_iso - self.min_iso)
        self.contour.SetValue(0, self.isovalue)
        self.ui.isovalue_label.setText(f"Isovalue: {self.isovalue:.2f}")
        self.ui.vtkWidget.GetRenderWindow().Render()

    def clip_callback(self, val, axis):
        if axis == 'x':
            clip_val = self.x_min + (val / 1000.0) * (self.x_max - self.x_min)
            self.clip_x_plane.SetOrigin(clip_val, 0, 0)
            self.ui.x_clip_label.setText(f"X Clip: {clip_val:.2f}")
        elif axis == 'y':
            clip_val = self.y_min + (val / 1000.0) * (self.y_max - self.y_min)
            self.clip_y_plane.SetOrigin(0, clip_val, 0)
            self.ui.y_clip_label.setText(f"Y Clip: {clip_val:.2f}")
        elif axis == 'z':
            clip_val = self.z_min + (val / 1000.0) * (self.z_max - self.z_min)
            self.clip_z_plane.SetOrigin(0, 0, clip_val)
            self.ui.z_clip_label.setText(f"Z Clip: {clip_val:.2f}")
        self.ui.vtkWidget.GetRenderWindow().Render()

    def screenshot_callback(self):
        save_frame(self.ui.vtkWidget.GetRenderWindow(), self.ui.log)

    def camera_callback(self):
        print_camera_settings(self.ren.GetActiveCamera(), self.ui.camera_info, self.ui.log)

    def save_camera_callback(self):
        save_camera_to_json(self.ren.GetActiveCamera(), self.ui.log)

    def quit_callback(self):
        sys.exit()

def get_program_parameters():
    parser = argparse.ArgumentParser(description='Interactive isosurface visualization with clipping planes.')
    parser.add_argument('-i', '--input', required=True, help='Path to the 3D scalar dataset (.vti)')
    parser.add_argument('--val', type=float, help='Initial isovalue')
    parser.add_argument('--clip', nargs=3, type=float, help='Initial positions of the X, Y, Z clipping planes')
    parser.add_argument('--range', nargs=2, type=float, help='Range for isovalue slider [min max]')
    parser.add_argument('--camera', help='JSON file containing initial camera settings')
    parser.add_argument('-o', '--output', default='frame_', help='Base filename for screenshots')
    parser.add_argument('-r', '--resolution', nargs=2, type=int, default=[1024, 768], help='Render window resolution')
    return parser.parse_args()

if __name__ == '__main__':
    args = get_program_parameters()
    app = QApplication(sys.argv)
    window = PyQtDemo(args)
    window.ui.vtkWidget.GetRenderWindow().SetSize(args.resolution[0], args.resolution[1])
    window.show()
    window.iren.Initialize()
    sys.exit(app.exec_())