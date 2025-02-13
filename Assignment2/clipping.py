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
ctrl_pts = [2000, 14000, 17000, 40000]
opacities = [0.4, 0.5, 0.8, 1.0]
colors = [
        (0.5, 0.5, 0.5),  # Gray
        (1.0, 0.0, 0.0),  # Red
        (0.7, 0.7, 0.7),  # Light Gray
        (1.0, 1.0, 0.0),  # Yellow
    ]

def make_colormap(min_value, max_value, ctrl_pts):
    num_colors = len(ctrl_pts)# Number of discrete intervals
    # Define colors for each interval
    colors = [
        (0.5, 0.5, 0.5),  # Gray
        (1.0, 0.0, 0.0),  # Red
        (0.7, 0.7, 0.7),  # Light Gray
        (1.0, 1.0, 0.0),  # Yellow
    ]
    
    ## Create color transfer function
    ctf = vtk.vtkColorTransferFunction()
    
    # Add color segments
    for i in range(len(ctrl_pts)):
        # Current control point pair
        if i == 0:
            start = min_value
        else:
            start = ctrl_pts[i - 1] + 1
        end = ctrl_pts[i]
        r, g, b = colors[i]
        
        # Add color at both ends of the interval
        ctf.AddRGBPoint(start, r, g, b)
        ctf.AddRGBPoint(end, r, g, b)
    
    return ctf


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
       
        scalar_volume = self.read_data()  
        self.volume = scalar_volume 
        self.interval = 100 # min( [ctrl_pts[i+1] - ctrl_pts[i] for i in range(len(ctrl_pts) - 1)] )
        self.numValues = len(ctrl_pts) 

        self.ren = vtk.vtkRenderer()
        self.ren.SetUseDepthPeeling(1)
        self.ren.SetMaximumNumberOfPeels(100)
        self.ren.SetOcclusionRatio(0.1)

        # Setup clipping box
        self.clip_box = vtk.vtkBox()
        
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

        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        camera = self.ren.GetActiveCamera()
        load_camera_from_json(camera, args.c)

        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()
        self.init_clipping_controls(scalar_volume)


    def read_data(self):
        scalar_data_path = self.args.i
        scalar_volume = vtk.vtkXMLImageDataReader()
        scalar_volume.SetFileName(scalar_data_path)
        scalar_volume.Update()
        return scalar_volume
    

    def apply_contour_filter(self, geometry, isovalue):
        surface = vtk.vtkContourFilter()
        surface.SetInputConnection(geometry.GetOutputPort())
        surface.SetValue(0, isovalue)
        return surface

    def create_color_map(self, mapper, min_value, max_value, numLabels):
        colormap = make_colormap(min_value, max_value, ctrl_pts)
        mapper.SetLookupTable(colormap)
        mapper.ScalarVisibilityOff()
        mapper.SetScalarRange(self.min_value, self.max_value)
        return colormap, mapper

    def create_color_bar(self, colormap):
        #  Create color bar
        colorbar_params = colorbar_param(
            title='HUMAN ANATOMY',
            title_col=[1, 1, 1],  # Black text
            label_col=[1, 1, 1],  # Black text
            pos=[0.85, 0.2],      # Position on the right side
            width=60,             # Width of the color bar
            height=300,           # Height of the color bar
            nlabels= len(ctrl_pts),            # Number of labels
            font_size=14,         # Label font size
            title_font_size=16    # Title font size
        )
        scalar_bar = colorbar(colormap, colorbar_params, is_float=False)
        return scalar_bar



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
        self.update_clipping()

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
        self.ui.x_clip_label.setText(f"X Clip : {x_val}")
        self.ui.y_clip_label.setText(f"Y Clip : {y_val}")
        self.ui.z_clip_label.setText(f"Z Clip : {z_val}")
        self.ui.vtkWidget.GetRenderWindow().Render()

      
   
    # Setting up widgets
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
    parser.add_argument('-i', help='Path to the 3D Scalar Dataset', default = 'data/ct_full_small.vti')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    # parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')
    parser.add_argument('-v', '--isovalue', type=int, metavar='int', help='Initial isovalue', default= ctrl_pts[0])
    parser.add_argument('-c',  help='Initial Camera Value', default='camera.json')
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
    window.init_clipping_controls(window.volume)
    sys.exit(app.exec_())