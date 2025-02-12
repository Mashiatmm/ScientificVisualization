#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel, QPushButton, QTextEdit
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt, QTimer
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse
import pandas as pd


frame_counter = 0

def save_frame(window, log):
    global frame_counter
    global args
    # ---------------------------------------------------------------
    # Save current contents of render window to PNG file
    # ---------------------------------------------------------------
    file_name = args.output + str(frame_counter).zfill(5) + ".png"
    image = vtk.vtkWindowToImageFilter()
    image.SetInput(window)
    png_writer = vtk.vtkPNGWriter()
    png_writer.SetInputConnection(image.GetOutputPort())
    png_writer.SetFileName(file_name)
    window.Render()
    png_writer.Write()
    frame_counter += 1
    if args.verbose:
        print(file_name + " has been successfully exported")
    log.insertPlainText('Exported {}\n'.format(file_name))

def print_camera_settings(camera, text_window, log):
    # ---------------------------------------------------------------
    # Print out the current settings of the camera
    # ---------------------------------------------------------------
    text_window.setHtml("<div style='font-weight:bold'>Camera settings:</div><p><ul><li><div style='font-weight:bold'>Position:</div> {0}</li><li><div style='font-weight:bold'>Focal point:</div> {1}</li><li><div style='font-weight:bold'>Up vector:</div> {2}</li><li><div style='font-weight:bold'>Clipping range:</div> {3}</li></ul>".format(camera.GetPosition(), camera.GetFocalPoint(),camera.GetViewUp(),camera.GetClippingRange()))
    log.insertPlainText('Updated camera info\n')

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName('The Main Window')
        MainWindow.setWindowTitle('Simple VTK + PyQt5 Example')
        # in Qt, windows are made of widgets.
        # centralWidget will contains all the other widgets
        self.centralWidget = QWidget(MainWindow)
        # we will organize the contents of our centralWidget
        # in a grid / table layout
        # Here is a screenshot of the layout:
        # https://www.cs.purdue.edu/~cs530/projects/img/PyQtGridLayout.png
        self.gridlayout = QGridLayout(self.centralWidget)
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        # Sliders
        self.slider_time = QSlider()
        self.water_level_label = QLabel("Water Level: ")
        self.date_label = QLabel("Date: ")
        
      
        # Push buttons
        self.push_screenshot = QPushButton()
        self.push_screenshot.setText('Save screenshot')
        self.push_camera = QPushButton()
        self.push_camera.setText('Update camera info')
        self.push_quit = QPushButton()
        self.push_quit.setText('Quit')
        # Text windows
        self.camera_info = QTextEdit()
        self.camera_info.setReadOnly(True)
        self.camera_info.setAcceptRichText(True)
        self.camera_info.setHtml("<div style='font-weight: bold'>Camera settings</div>")
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        # We are now going to position our widgets inside our
        # grid layout. The top left corner is (0,0)
        # Here we specify that our vtkWidget is anchored to the top
        # left corner and spans 3 rows and 4 columns.

        # ... [Previous UI setup code] ...
        # Add new UI elements
        self.water_level_label = QLabel("Water Level: ")
        self.date_label = QLabel("Date: ")
        self.slider_time = QSlider(Qt.Horizontal)
        self.btn_play = QPushButton("Play")
        
        # Add to layout
        self.gridlayout.addWidget(self.btn_play, 6, 5, 1, 1)
        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 4, 4)
        self.gridlayout.addWidget(self.slider_time, 4, 0, 1, 4)
        self.gridlayout.addWidget(self.water_level_label, 5, 0, 1, 2)
        self.gridlayout.addWidget(self.date_label, 5, 2, 1, 2)
        self.gridlayout.addWidget(self.push_screenshot, 0, 5, 1, 1)
        self.gridlayout.addWidget(self.push_camera, 1, 5, 1, 1)
        self.gridlayout.addWidget(self.camera_info, 2, 4, 1, 2)
        self.gridlayout.addWidget(self.log, 3, 4, 1, 2)
        self.gridlayout.addWidget(self.push_quit, 5, 5, 1, 1)
        MainWindow.setCentralWidget(self.centralWidget)

        

def get_program_parameters():
    description = 'ImageWarp.'
    epilogue = '''
    This example shows how to combine data from both the imaging
    and graphics pipelines. The vtkMergeData filter is used to
    merge the data from each together.

   '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-e', help='Path to the elevation file.', default = "gsl_basin_topography.vti")
    parser.add_argument('-i', help='Path to the image file.', default = "gsl_dry.jpg")
    parser.add_argument('-w', help='Path to the water level file.', default = "gsl_all_water_levels.csv")
    parser.add_argument('-m', help='Path to the mask file.', default = "lake_mask.vti")
    parser.add_argument('-s', help='Scale Factor', type=int, metavar='int', default = 1)

    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')

    args = parser.parse_args()
    return args
    

class PyQtDemo(QMainWindow):

    def __init__(self, args, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.timer = QTimer()
        self.animation_running = False
        
        self.args = args
        self.scale_factor = self.args.s

        texture, topo_geometry, self.water_level, mask_geometry = self.read_data()
        self.min_date = 0
        self.max_date = len(self.water_level) - 1
        self.warped_data = self.warp_geometry(topo_geometry, self.scale_factor)
        self.mapper = self.to_mapper(self.warped_data)
        self.actor = self.to_actor(self.mapper)
        self.actor.SetTexture(texture)

        record = self.water_level.iloc[0]
        water_elevation = record['325949_62614_00003'] * self.scale_factor
        self.warp_water = self.warp_geometry(mask_geometry, water_elevation)
        self.warp_mapper = self.to_mapper(self.warp_water)
        self.warp_actor = self.to_actor(self.warp_mapper)
        self.warp_actor.GetProperty().SetColor(28 / 255.0, 60 / 255.0, 76 / 255.0)  # Water color

        # Create the Renderer
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(self.actor)
        self.ren.AddActor(self.warp_actor)
        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()
        self.slider_setup(self.ui.slider_time, 0, [self.min_date, self.max_date], 100) 

    def read_data(self):
        elevation_file_path = self.args.e
        satellite_file_path = self.args.i
        water_level_file_path = self.args.w
        mask_file_path = self.args.m
     
        topo_reader = vtk.vtkXMLImageDataReader()
        topo_reader.SetFileName(elevation_file_path)
        topo_geometry = vtk.vtkImageDataGeometryFilter()
        topo_geometry.SetInputConnection(topo_reader.GetOutputPort())

        texture_reader = vtk.vtkJPEGReader()  # Use appropriate reader for the image format.
        texture_reader.SetFileName(satellite_file_path)
        texture_reader.Update()
        texture = vtk.vtkTexture()
        texture.SetInputConnection(texture_reader.GetOutputPort())
        texture.InterpolateOn()

        water_level = pd.read_csv(water_level_file_path)

        lake_mask = vtk.vtkXMLImageDataReader()
        lake_mask.SetFileName(mask_file_path)
        mask_geometry = vtk.vtkImageDataGeometryFilter()
        mask_geometry.SetInputConnection(lake_mask.GetOutputPort())

        return texture, topo_geometry, water_level, mask_geometry
    

    def warp_geometry(self, geometry, scale_factor):
        warp = vtk.vtkWarpScalar()
        warp.SetInputConnection(geometry.GetOutputPort())
        warp.SetScaleFactor(scale_factor)
        return warp

    def to_mapper(self, warped_data):
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputConnection(warped_data.GetOutputPort())
        mapper.ScalarVisibilityOff()
        return mapper

    def to_actor(self, mapper):
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        return actor
   
    # Setting up widgets
    def slider_setup(self, slider, val, bounds, interv):
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setValue(int(val))
        slider.setTracking(False)
        slider.setTickInterval(interv)
        slider.setTickPosition(QSlider.TicksAbove)
        slider.setRange(bounds[0], bounds[1])

 
    def update_water_level(self, idx):
        record = self.water_level.iloc[idx]
        water_elevation = record['325949_62614_00003'] * self.scale_factor
        self.warp_water.SetScaleFactor(water_elevation)
        self.warp_water.Update()
        self.ui.water_level_label.setText(f"Water Level: {record['325949_62614_00003']:.2f} ft")
        self.ui.date_label.setText(f"Date: {record['datetime']}")
        self.ui.vtkWidget.GetRenderWindow().Render()

    def toggle_animation(self):
        if self.animation_running:
            self.timer.stop()
            self.ui.btn_play.setText("Play Animation")
        else:
            self.timer.start(10) 
            self.ui.btn_play.setText("Stop Animation")
        self.animation_running = not self.animation_running

    def animation_step(self):
        current_idx = self.ui.slider_time.value()
        if current_idx < self.max_date:
            self.ui.slider_time.setValue(current_idx + 30)
        else:
            self.timer.stop()
            self.ui.btn_play.setText("Play Animation")
            self.animation_running = False

    def screenshot_callback(self):
        save_frame(self.ui.vtkWidget.GetRenderWindow(), self.ui.log)

    def camera_callback(self):
        print_camera_settings(self.ren.GetActiveCamera(), self.ui.camera_info, self.ui.log)

    def quit_callback(self):
        sys.exit()


if __name__ == '__main__':
    global args
    args = get_program_parameters()

    app = QApplication(sys.argv)
    window = PyQtDemo(args)
    window.ui.vtkWidget.GetRenderWindow().SetSize(args.resolution[0], args.resolution[1])
    window.ui.log.insertPlainText('Set render window resolution to {}\n'.format(args.resolution))
    window.show()
    window.setWindowState(Qt.WindowMaximized)  # Maximize the window

    window.iren.Initialize() # Need this line to actually show
                             # the render inside Qt
    window.ui.slider_time.setRange(window.min_date, window.max_date)
    window.ui.slider_time.valueChanged.connect(window.update_water_level)
    window.ui.btn_play.clicked.connect(window.toggle_animation)
    window.timer.timeout.connect(window.animation_step)
    window.ui.push_screenshot.clicked.connect(window.screenshot_callback)
    window.ui.push_camera.clicked.connect(window.camera_callback)
    window.ui.push_quit.clicked.connect(window.quit_callback)
    window.update_water_level(0)  # 0 represents the first row in your CSV

    sys.exit(app.exec_())