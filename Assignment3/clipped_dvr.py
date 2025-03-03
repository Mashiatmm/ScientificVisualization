#!/usr/bin/env python

import sys
import argparse
import json
import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout, QSlider, QLabel
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

def load_transfer_functions(filename):
    with open(filename, 'r') as f:
        tf_data = json.load(f)
    
    ctf = vtk.vtkColorTransferFunction()
    for point in tf_data['color']:
        ctf.AddRGBPoint(*point)
    
    otf = vtk.vtkPiecewiseFunction()
    for point in tf_data['opacity']:
        otf.AddPoint(*point)
    
    return ctf, otf

def load_camera_from_json(camera, filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    camera.SetPosition(data['Position'])
    camera.SetFocalPoint(data['FocalPoint'])
    camera.SetViewUp(data['ViewUp'])
    camera.SetClippingRange(data['ClippingRange'])

class ClippedDVR(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.setup_ui()
        self.setup_pipeline()
        self.setup_sliders()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)
        self.vtk_widget = QVTKRenderWindowInteractor()
        self.layout.addWidget(self.vtk_widget, 0, 0, 1, 4)
        
        # Slider labels
        self.x_label = QLabel("X Clip: 0.0")
        self.y_label = QLabel("Y Clip: 0.0")
        self.z_label = QLabel("Z Clip: 0.0")
        self.layout.addWidget(self.x_label, 1, 0)
        self.layout.addWidget(self.y_label, 1, 1)
        self.layout.addWidget(self.z_label, 1, 2)

    def setup_pipeline(self):
        # Read data
        self.reader = vtk.vtkXMLImageDataReader()
        self.reader.SetFileName(self.args.input)
        self.reader.Update()
        self.data = self.reader.GetOutput()
        self.bounds = self.data.GetBounds()

        # Load transfer functions
        self.ctf, self.otf = load_transfer_functions(self.args.tf)

        # Volume properties
        self.volume_property = vtk.vtkVolumeProperty()
        self.volume_property.SetColor(self.ctf)
        self.volume_property.SetScalarOpacity(self.otf)
        self.volume_property.ShadeOn()
        self.volume_property.SetInterpolationTypeToLinear()

        # Volume mapper with cropping
        self.mapper = vtk.vtkSmartVolumeMapper()
        self.mapper.SetInputData(self.data)
        self.mapper.SetBlendModeToComposite()
        self.mapper.SetSampleDistance(0.1)
        self.mapper.SetCropping(True)
        self.mapper.SetCroppingRegionPlanes(*self.bounds)

        # Volume actor
        self.volume = vtk.vtkVolume()
        self.volume.SetMapper(self.mapper)
        self.volume.SetProperty(self.volume_property)

        # Renderer
        self.renderer = vtk.vtkRenderer()
        self.renderer.AddVolume(self.volume)
        self.renderer.SetBackground(0.1, 0.1, 0.2)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)

        # Load camera if provided
        if self.args.camera:
            load_camera_from_json(self.renderer.GetActiveCamera(), self.args.camera)

        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.iren.Initialize()

    def setup_sliders(self):
        self.x_slider = QSlider(QtCore.Qt.Horizontal)
        self.x_slider.setRange(0, 1000)
        self.x_slider.valueChanged.connect(lambda v: self.update_clipping(v, 'x'))
        self.layout.addWidget(self.x_slider, 2, 0)

        self.y_slider = QSlider(QtCore.Qt.Horizontal)
        self.y_slider.setRange(0, 1000)
        self.y_slider.valueChanged.connect(lambda v: self.update_clipping(v, 'y'))
        self.layout.addWidget(self.y_slider, 2, 1)

        self.z_slider = QSlider(QtCore.Qt.Horizontal)
        self.z_slider.setRange(0, 1000)
        self.z_slider.valueChanged.connect(lambda v: self.update_clipping(v, 'z'))
        self.layout.addWidget(self.z_slider, 2, 2)

    def update_clipping(self, value, axis):
        normalized = (value / 1000.0)
        idx = {'x':0, 'y':2, 'z':4}[axis]
        planes = list(self.mapper.GetCroppingRegionPlanes())
        
        # Update min plane and keep max at bounds
        planes[idx] = self.bounds[idx] + normalized * (self.bounds[idx+1] - self.bounds[idx])
        planes[idx+1] = self.bounds[idx+1]  # Keep max fixed
        
        self.mapper.SetCroppingRegionPlanes(planes)
        getattr(self, f"{axis}_label").setText(f"{axis.upper()} Clip: {planes[idx]:.1f}")
        self.vtk_widget.GetRenderWindow().Render()

def parse_args():
    parser = argparse.ArgumentParser(description='Clipped Direct Volume Rendering')
    parser.add_argument('-i', '--input', required=True, help='Input dataset (.vti)')
    parser.add_argument('--tf', required=True, help='Transfer function config (.json)')
    parser.add_argument('--camera', help='Camera settings file (.json)')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    app = QApplication(sys.argv)
    window = ClippedDVR(args)
    window.setWindowTitle('Clipped DVR')
    window.resize(1024, 768)
    window.show()
    sys.exit(app.exec_())