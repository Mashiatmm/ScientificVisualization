#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel, QPushButton, QTextEdit
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse



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
        self.slider_scale_factor = QSlider()
      
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
        self.gridlayout.addWidget(QLabel("Scale Factor resolution"), 4, 0, 1, 1)
        self.gridlayout.addWidget(self.slider_scale_factor, 4, 1, 1, 1)
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
    parser.add_argument('-e', help='Path to the elevation file.')
    parser.add_argument('-i', help='Path to the image file.')
    parser.add_argument('-r', '--resolution', type=int, metavar='int', nargs=2, help='Image resolution', default=[1024, 768])
    parser.add_argument('-o', '--output', type=str, metavar='filename', help='Base name for screenshots', default='frame_')
    parser.add_argument('-v', '--verbose', action='store_true', help='Toggle on verbose output')


    args = parser.parse_args()
    return args


# def main():
    

class PyQtDemo(QMainWindow):

    def __init__(self, args, parent = None):
        QMainWindow.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.scale_factor = 10
        self.args = args

        texture, topo_geometry = self.read_data()
        self.warped_data = self.warp_geometry(topo_geometry)
        self.mapper = self.to_mapper(self.warped_data)
        self.actor = self.to_actor(self.mapper)

        # # Apply the texture to the actor.
        self.actor.SetTexture(texture)
        # Create the rendering window, renderer, and interactive renderer.

        # Create the Renderer
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(self.actor)
        self.ui.vtkWidget.GetRenderWindow().AddRenderer(self.ren)
        self.iren = self.ui.vtkWidget.GetRenderWindow().GetInteractor()

        self.slider_setup(self.ui.slider_scale_factor, self.scale_factor, [1, 100], 2)

        


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
    

    def warp_geometry(self, geometry):

        # # Warp the data in a direction perpendicular to the image plane.
        warp = vtk.vtkWarpScalar()
        warp.SetInputConnection(geometry.GetOutputPort())
        warp.SetScaleFactor(self.scale_factor)
        return warp

    def to_mapper(self, warped_data):
        # Use vtkMergeFilter to combine the original image with the warped geometry.
        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputConnection(warped_data.GetOutputPort())
        # mapper.SetScalarRange(0, 255)
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

 

    def scale_factor_callback(self, val):
        self.scale_factor = val
        # self.edges.SetRadius(self.radius)
        self.warped_data.SetScaleFactor(self.scale_factor)
        self.ui.log.insertPlainText('Scale Factor set to {}\n'.format(self.scale_factor))
        self.ui.vtkWidget.GetRenderWindow().Render()

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
                             # the render inside Qt

    window.ui.slider_scale_factor.valueChanged.connect(window.scale_factor_callback)
    window.ui.push_screenshot.clicked.connect(window.screenshot_callback)
    window.ui.push_camera.clicked.connect(window.camera_callback)
    window.ui.push_quit.clicked.connect(window.quit_callback)
    sys.exit(app.exec_())