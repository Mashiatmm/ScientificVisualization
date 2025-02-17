#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel, QPushButton, QTextEdit, QCheckBox
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse
import numpy as np
import json

import vtk_colors, vtk_colorbar
from vtk_colors import import_palette
from vtk_colorbar import colorbar_param, colorbar

frame_counter = 0
ctrl_pts = [2000, 14000, 20000, 35000]
opacities = [0.5, 0.6, 0.8, 1.0]
colors = [
        (206 / 255.0, 176 / 255.0, 165 / 255.0),  # Gray 206,176,165
        (1.0, 0.0, 0.0),  # Red
        (0.7, 0.7, 0.7),  # Light Gray
        (1.0, 1.0, 0.0),  # Yellow
    ]


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
    log.insertPlainText('Exported {}\n'.format(file_name))

def print_camera_settings(camera, text_window, log):
    # ---------------------------------------------------------------
    # Print out the current settings of the camera
    # ---------------------------------------------------------------
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
    
    # Convert tuples to lists for JSON serialization
    for key in camera_data:
        if isinstance(camera_data[key], tuple):
            camera_data[key] = list(camera_data[key])
    
    with open(filename, "w") as f:
        json.dump(camera_data, f, indent=4)
    log.insertPlainText('Saved camera info\n')


def load_camera_from_json(camera, filename):
    # Load JSON data
    with open(filename, "r") as f:
        camera_data = json.load(f)
    
    # Apply loaded parameters to the camera
    camera.SetPosition(camera_data["Position"])
    camera.SetFocalPoint(camera_data["FocalPoint"])
    camera.SetViewUp(camera_data["ViewUp"])
    camera.SetClippingRange(camera_data["ClippingRange"])
    camera.SetViewAngle(camera_data["ViewAngle"])
    camera.SetParallelScale(camera_data["ParallelScale"])


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
        # vtkWidget is a widget that encapsulates a vtkRenderWindow
        # and the associated vtkRenderWindowInteractor. We add
        # it to centralWidget.
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        self.slider_isovalue = QSlider()

        # Push buttons
        self.push_screenshot = QPushButton()
        self.push_screenshot.setText('Save screenshot')
        self.push_camera = QPushButton()
        self.push_camera.setText('Update camera info')
        self.push_quit = QPushButton()
        self.push_quit.setText('Quit')
        self.save_camera = QPushButton()
        self.save_camera.setText('Save camera info')
        # Text windows
        self.camera_info = QTextEdit()
        self.camera_info.setReadOnly(True)
        self.camera_info.setAcceptRichText(True)
        self.camera_info.setHtml("<div style='font-weight: bold'>Camera settings</div>")
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        # Add clipping controls
        self.clip_x_slider = QSlider()
        self.clip_y_slider = QSlider()
        self.clip_z_slider = QSlider()
        self.clip_x_check = QCheckBox("X Clip Dir")
        self.clip_y_check = QCheckBox("Y Clip Dir")
        self.clip_z_check = QCheckBox("Z Clip Dir")
        self.x_clip_label = QLabel("X Clip")
        self.y_clip_label = QLabel("Y Clip")
        self.z_clip_label = QLabel("Z Clip")

        # We are now going to position our widgets inside our
        # grid layout. The top left corner is (0,0)
        # Here we specify that our vtkWidget is anchored to the top
        # left corner and spans 3 rows and 4 columns.
        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 4, 4)
        # Add to grid layout
        self.gridlayout.addWidget(self.x_clip_label, 4, 0, 1, 1)
        self.gridlayout.addWidget(self.clip_x_slider, 4, 1, 1, 1)
        self.gridlayout.addWidget(self.clip_x_check, 4, 2, 1, 1)
        self.gridlayout.addWidget(self.y_clip_label, 5, 0, 1, 1)
        self.gridlayout.addWidget(self.clip_y_slider, 5, 1, 1, 1)
        self.gridlayout.addWidget(self.clip_y_check, 5, 2, 1, 1)
        self.gridlayout.addWidget(self.z_clip_label, 6, 0, 1, 1)
        self.gridlayout.addWidget(self.clip_z_slider, 6, 1, 1, 1)
        self.gridlayout.addWidget(self.clip_z_check, 6, 2, 1, 1)

        self.gridlayout.addWidget(self.push_screenshot, 0, 5, 1, 1)
        self.gridlayout.addWidget(self.push_camera, 1, 5, 1, 1)
        self.gridlayout.addWidget(self.camera_info, 2, 4, 1, 2)
        self.gridlayout.addWidget(self.log, 3, 4, 1, 2)
        self.gridlayout.addWidget(self.save_camera, 4, 5,  1, 1)
        self.gridlayout.addWidget(self.push_quit, 5, 5, 1, 1)
        MainWindow.setCentralWidget(self.centralWidget)


class PyQtDemo(QMainWindow):

    def __init__(self, args, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.args = args
       
        scalar_volume , self.photo_volume = self.read_data()  
        self.volume = scalar_volume 
        self.interval = 100 # min( [ctrl_pts[i+1] - ctrl_pts[i] for i in range(len(ctrl_pts) - 1)] )
        self.numValues = len(ctrl_pts) 

        self.ren = vtk.vtkRenderer()
        self.ren.SetUseDepthPeeling(1)
        self.ren.SetMaximumNumberOfPeels(100)
        self.ren.SetOcclusionRatio(0.1)

        # Setup clipping box
        self.clip_box = vtk.vtkBox()
        self.actors = []
        # Modify the contour creation loop
        for i, (val, color, opacity) in enumerate(zip(ctrl_pts, colors, opacities)):
            contour = self.apply_contour_filter(scalar_volume, val)
            
            # Create individual clip filter for each contour
            clip_filter = vtk.vtkClipPolyData()
            clip_filter.SetClipFunction(self.clip_box)
            clip_filter.SetInputConnection(contour.GetOutputPort())
            
            mapper = self.to_mapper(clip_filter)  # Connect mapper to clip filter
            actor = self.to_actor(mapper)
            actor.GetProperty().SetColor(color)
            actor.GetProperty().SetOpacity(opacity)    
            self.ren.AddActor(actor)
            self.actors.append(actor)

        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        camera = self.ren.GetActiveCamera()
        load_camera_from_json(camera, args.camera)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()
        self.init_clipping_controls(scalar_volume)

    def read_data(self):
        scalar_data_path = self.args.input[0]
        scalar_volume = vtk.vtkXMLImageDataReader()
        scalar_volume.SetFileName(scalar_data_path)
        scalar_volume.Update()

        photo_volume_path = self.args.input[1]
        photo_volume = vtk.vtkXMLImageDataReader()
        photo_volume.SetFileName(photo_volume_path)
        photo_volume.Update()

        return scalar_volume, photo_volume.GetOutput()
    

    def apply_contour_filter(self, geometry, isovalue):
        surface = vtk.vtkContourFilter()
        surface.SetInputConnection(geometry.GetOutputPort())
        surface.SetValue(0, isovalue)
        return surface


    def to_mapper(self, image):
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputConnection(image.GetOutputPort())
        mapper.ScalarVisibilityOff()
        return mapper

    def to_actor(self, mapper):
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        return actor

    def init_clipping_controls(self, volume):
        bounds = volume.GetOutput().GetBounds()
        self.data_bounds = bounds 
        default_clip = [self.data_bounds[1], self.data_bounds[3], self.data_bounds[5]]  # Define these based on your data
        initial_clip_values = args.clip if args.clip else default_clip
       
        self.ui.x_clip_label.setText(f"X Clip : {initial_clip_values[0]}")
        self.ui.y_clip_label.setText(f"Y Clip : {initial_clip_values[1]}")
        self.ui.z_clip_label.setText(f"Z Clip : {initial_clip_values[2]}")
        self.slider_setup(self.ui.clip_x_slider, initial_clip_values[0], 
                         [self.data_bounds[0], self.data_bounds[1]], 100)
        self.slider_setup(self.ui.clip_y_slider, initial_clip_values[1],
                         [self.data_bounds[2], self.data_bounds[3]], 100)
        self.slider_setup(self.ui.clip_z_slider, initial_clip_values[2],
                         [self.data_bounds[4], self.data_bounds[5]], 100)
        self.init_probe_planes()

    def update_clipping(self):
        x_val = self.ui.clip_x_slider.value()
        y_val = self.ui.clip_y_slider.value()
        z_val = self.ui.clip_z_slider.value()
        
        x_dir = self.ui.clip_x_check.isChecked()
        y_dir = self.ui.clip_y_check.isChecked()
        z_dir = self.ui.clip_z_check.isChecked()

        # Calculate new bounds
        new_bounds = [
            self.data_bounds[0] if x_dir else x_val,
            x_val if x_dir else self.data_bounds[1],
            self.data_bounds[2] if y_dir else y_val,
            y_val if y_dir else self.data_bounds[3],
            self.data_bounds[4] if z_dir else z_val,
            z_val if z_dir else self.data_bounds[5]
        ]
        self.clip_box.SetBounds(new_bounds)
        self.clip_box.Modified() 
        self.ui.x_clip_label.setText(f"X Clip : {x_val}")
        self.ui.y_clip_label.setText(f"Y Clip : {y_val}")
        self.ui.z_clip_label.setText(f"Z Clip : {z_val}")
        self.update_probe_planes()
        self.ui.vtkWidget.GetRenderWindow().Render()
    
    def init_probe_planes(self):
        """Create and add probe plane actors once."""
        self.offset = 15.0 # Offset for visualization
        self.probe_planes = {}
        self.planes_initialized = False

        plane_configs = {
            'yz': {'normal': [1, 0, 0]},  # X-normal plane
            'xz': {'normal': [0, 1, 0]},  # Y-normal plane
            'xy': {'normal': [0, 0, 1]}   # Z-normal plane
        }

        for plane, config in plane_configs.items():
            # Create plane source with higher resolution
            plane_source = vtk.vtkPlaneSource()
            plane_source.SetResolution(100, 100)
            
            # Set up probe filter
            probe_filter = vtk.vtkProbeFilter()
            probe_filter.SetSourceData(self.photo_volume)
            probe_filter.SetInputConnection(plane_source.GetOutputPort())
            probe_filter.PassPointArraysOn()

            # Add clipping
            clipper = vtk.vtkClipPolyData()
            clipper.SetClipFunction(self.clip_box)
            clipper.GenerateClippedOutputOn()
            clipper.SetInputConnection(probe_filter.GetOutputPort())
                        
            # Set up mapper
            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputConnection(clipper.GetOutputPort())  # Connect to clipper instead of probe
            mapper.SetScalarRange(0, 255)
            mapper.SetColorModeToDirectScalars()
            
            # Set up actor
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetOpacity(1.0)
            actor.GetProperty().SetAmbient(1.0)
            actor.GetProperty().SetDiffuse(0.0)
            actor.VisibilityOff()

            self.ren.AddActor(actor)
            
            self.probe_planes[plane] = {
                'source': plane_source,
                'probe': probe_filter,
                'clipper': clipper,  # Store the clipper
                'mapper': mapper,
                'actor': actor,
                'normal': config['normal']
            }
   
    def update_probe_planes(self):
        x_val = self.ui.clip_x_slider.value()
        y_val = self.ui.clip_y_slider.value()
        z_val = self.ui.clip_z_slider.value()
        bounds = self.data_bounds

        x_dir = self.ui.clip_x_check.isChecked()
        y_dir = self.ui.clip_y_check.isChecked()
        z_dir = self.ui.clip_z_check.isChecked()

        plane_x = x_val  
        if self.ui.clip_x_check.isChecked():
            plane_x = x_val + self.offset  # Move plane away from clipped region
        else:
            plane_x = x_val - self.offset  # Move plane toward clipped region
        yz_source = self.probe_planes['yz']['source']
        yz_source.SetOrigin(plane_x, bounds[2], bounds[4])
        yz_source.SetPoint1(plane_x, bounds[3], bounds[4])
        yz_source.SetPoint2(plane_x, bounds[2], bounds[5])
        
        plane_y = y_val
        if self.ui.clip_y_check.isChecked():
            plane_y = y_val + self.offset
        else:
            plane_y = y_val - self.offset       
        xz_source = self.probe_planes['xz']['source']
        xz_source.SetOrigin(bounds[0], plane_y, bounds[4])
        xz_source.SetPoint1(bounds[1], plane_y, bounds[4])
        xz_source.SetPoint2(bounds[0], plane_y, bounds[5])

        # Update XY plane (Z direction)
        plane_z = z_val  
        if self.ui.clip_z_check.isChecked():
            plane_z = z_val + self.offset
        else:
            plane_z = z_val - self.offset
        xy_source = self.probe_planes['xy']['source']
        xy_source.SetOrigin(bounds[0], bounds[2], plane_z)
        xy_source.SetPoint1(bounds[1], bounds[2], plane_z)
        xy_source.SetPoint2(bounds[0], bounds[3], plane_z)

        if not self.planes_initialized:
            for plane in self.probe_planes.values():
                plane['actor'].VisibilityOn()
            self.planes_initialized = True
        for plane in self.probe_planes.values():
            plane['source'].Modified()
            plane['probe'].Modified()
        
        self.ui.vtkWidget.GetRenderWindow().Render()


    def slider_setup(self, slider, val, bounds, interv):
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setValue( int(val) )
        slider.setTracking(False)
        slider.setTickInterval(interv)
        slider.setTickPosition(QSlider.TicksAbove)
        slider.setRange(int(bounds[0]), int(bounds[1]))

   
    def screenshot_callback(self):
        save_frame(self.ui.vtkWidget.GetRenderWindow(), self.ui.log)

    def camera_callback(self):
        print_camera_settings(self.ren.GetActiveCamera(), self.ui.camera_info, self.ui.log)

    def save_camera_callback(self):
        save_camera_to_json(self.ren.GetActiveCamera(), self.ui.log)

    def quit_callback(self):
        sys.exit()


def get_program_parameters():
    description = 'Isosurfaces'
    epilogue = '''
    Isosurfaces of Human Anatomy
   '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-i', '--input', nargs=2, help='Path to the 3D Scalar Dataset', default = ['data/ct_head_small.vti', 'data/rgb_thorax_small.vti'])
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    # parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')
    parser.add_argument('-v', '--val', type=int, metavar='int', help='Initial isovalue', default= ctrl_pts[0])
    parser.add_argument('--camera',  help='Initial Camera Value', default='camera.json')
    parser.add_argument("--clip", nargs=3, type=float, help="Initial positions of the three clipping planes (X, Y, Z)")
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    # main()
    global args

    args = get_program_parameters()

    app = QApplication(sys.argv)
    window = PyQtDemo(args)
    window.ui.vtkWidget.GetRenderWindow().SetSize(args.resolution[0], args.resolution[1])
    window.ui.log.insertPlainText('Set render window resolution to {}\n'.format(args.resolution))
    window.show()
    window.setWindowState(Qt.WindowMaximized)  # Maximize the window
    window.iren.Initialize() # Need this line to actually show

    window.ui.push_screenshot.clicked.connect(window.screenshot_callback)
    window.ui.push_camera.clicked.connect(window.camera_callback)
    window.ui.save_camera.clicked.connect(window.save_camera_callback)
    window.ui.push_quit.clicked.connect(window.quit_callback)
    window.ui.clip_x_slider.valueChanged.connect(window.update_clipping)
    window.ui.clip_y_slider.valueChanged.connect(window.update_clipping)
    window.ui.clip_z_slider.valueChanged.connect(window.update_clipping)
    window.ui.clip_x_check.stateChanged.connect(window.update_clipping)
    window.ui.clip_y_check.stateChanged.connect(window.update_clipping)
    window.ui.clip_z_check.stateChanged.connect(window.update_clipping)
    # window.init_clipping_controls(window.volume)
    sys.exit(app.exec_())