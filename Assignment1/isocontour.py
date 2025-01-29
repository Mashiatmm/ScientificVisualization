#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel, QPushButton, QTextEdit
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse
import numpy as np

import vtk_colors, vtk_colorbar
from vtk_colors import import_palette
from vtk_colorbar import colorbar_param, colorbar

frame_counter = 0

def make_colormap(scheme_name, ctrl_pts):
    colors = vtk.vtkColorSeries()
    # colors = newcolors
    m = colors.GetNumberOfColorSchemes()
    # print(f'There are {m} color schemes')
    g = colors.SetColorSchemeByName(scheme_name)
    if g == m:
        # print('Requested color scheme was not found in VTK list')
        try:
            colors = import_palette( scheme_name, len(ctrl_pts) )
        except:
            print('unable to find requested color map: {}'.format(scheme_name))
            raise
    else:
        print(f'Requested color scheme {scheme_name} has index {g}')
    n = colors.GetNumberOfColors()
    # print(f'{n} colors')
    if len(ctrl_pts) == 2:
        f = interpolate.interp1d(x=[0, n-1], y=ctrl_pts)
        ctrl_pts = f(range(n))
    elif len(ctrl_pts) != n:
        raise ValueError('Numbers of colors and control points don\'t match')
    cmap = vtk.vtkColorTransferFunction()
    for i in range(n):
        c = colors.GetColor(i)
        d=[0,0,0]
        for j in range(3):
            # print(c[j])
            d[j] = float(c[j])/255.
        cmap.AddRGBPoint(ctrl_pts[i], d[0], d[1], d[2])
        # print(f'{i}: {ctrl_pts[i]} . {c} / {d}')
    return cmap

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
        # vtkWidget is a widget that encapsulates a vtkRenderWindow
        # and the associated vtkRenderWindowInteractor. We add
        # it to centralWidget.
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
     
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
        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 4, 4)
        self.gridlayout.addWidget(self.push_screenshot, 0, 5, 1, 1)
        self.gridlayout.addWidget(self.push_camera, 1, 5, 1, 1)
        self.gridlayout.addWidget(self.camera_info, 2, 4, 1, 2)
        self.gridlayout.addWidget(self.log, 3, 4, 1, 2)
        self.gridlayout.addWidget(self.push_quit, 5, 5, 1, 1)
        MainWindow.setCentralWidget(self.centralWidget)



def get_program_parameters():
    description = 'Isocontour.'
    epilogue = '''
    Isocontour with Utah Salt Lake

   '''
    parser = argparse.ArgumentParser(description=description, epilog=epilogue,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-e', help='Path to the elevation file.')
    parser.add_argument('-i', help='Path to the image file.')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')
    parser.add_argument('-n', '--numContours', type=int, metavar='int', help='Number of contours', default=9)

    args = parser.parse_args()
    return args


    

class PyQtDemo(QMainWindow):

    def __init__(self, args, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.numContours = args.numContours
        self.min_value = 4200
        self.max_value = 10200
        self.args = args

        texture, topoGeometry = self.read_data()
       
        self.baseMapper = self.to_mapper(topoGeometry)
        self.baseActor = self.to_actor(self.baseMapper)
        self.baseActor.SetTexture(texture)

        self.contours = self.apply_contour_filter(topoGeometry, self.numContours, self.min_value, self.max_value)
        self.contourMapper = self.to_mapper(self.contours)
        # Create color map for contours
        self.colormap, self.contourMapper = self.create_color_map( mapper = self.contourMapper, min_value = self.min_value, max_value = self.max_value, numContours = self.numContours)
        self.color_bar = self.create_color_bar( colormap = self.colormap )
        self.contourActor = self.to_actor(self.contourMapper)
        self.contourActor.GetProperty().SetLineWidth(2)

       

        # Create the Renderer
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(self.baseActor)
        self.ren.AddActor(self.contourActor)
        self.ren.AddActor(self.color_bar.get())  # Add the color bar
        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()


    def read_data(self):
        elevation_file_path = self.args.e
        satellite_file_path = self.args.i

        topo_reader = vtk.vtkXMLImageDataReader()
        topo_reader.SetFileName(elevation_file_path)
        geometry = vtk.vtkImageDataGeometryFilter()
        geometry.SetInputConnection(topo_reader.GetOutputPort())

        texture_reader = vtk.vtkJPEGReader()  # Use appropriate reader for the image format.
        texture_reader.SetFileName(satellite_file_path)
        texture_reader.Update()
        texture = vtk.vtkTexture()
        texture.SetInputConnection(texture_reader.GetOutputPort())
        texture.InterpolateOn()

        return texture, geometry
    

    def apply_contour_filter(self, geometry, numContours, min_value, max_value):
        surface = vtk.vtkContourFilter()
        surface.SetInputConnection(geometry.GetOutputPort())
        surface.GenerateValues(numContours, min_value, max_value)
        return surface

    def create_color_map(self, mapper, min_value, max_value, numContours):
        ctrl_pts = np.linspace(min_value, max_value, numContours)
        colormap = make_colormap("YlOrRd", ctrl_pts)
        mapper.SetLookupTable(colormap)
        mapper.ScalarVisibilityOn()
        mapper.SetScalarRange(self.min_value, self.max_value)
        return colormap, mapper

    def create_color_bar(self, colormap):
        #  Create color bar
        colorbar_params = colorbar_param(
            title='Elevation',
            title_col=[1, 1, 1],  # Black text
            label_col=[1, 1, 1],  # Black text
            pos=[0.85, 0.2],      # Position on the right side
            width=60,             # Width of the color bar
            height=300,           # Height of the color bar
            nlabels=6,            # Number of labels
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
   
    # Setting up widgets
    def slider_setup(self, slider, val, bounds, interv):
        slider.setOrientation(QtCore.Qt.Horizontal)
        slider.setValue(int(val))
        slider.setTracking(False)
        slider.setTickInterval(interv)
        slider.setTickPosition(QSlider.TicksAbove)
        slider.setRange(bounds[0], bounds[1])

    def screenshot_callback(self):
        save_frame(self.ui.vtkWidget.GetRenderWindow(), self.ui.log)

    def camera_callback(self):
        print_camera_settings(self.ren.GetActiveCamera(), self.ui.camera_info, self.ui.log)

    def quit_callback(self):
        sys.exit()





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
    window.ui.push_quit.clicked.connect(window.quit_callback)
    sys.exit(app.exec_())