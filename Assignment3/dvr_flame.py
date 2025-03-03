#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse
import json
import vtk

import vtk_colorbar
from vtk_colorbar import colorbar_param, colorbar

def load_camera_from_json(camera, filename):
    with open(filename, "r") as f:
        camera_data = json.load(f)
    camera.SetPosition(camera_data["Position"])
    camera.SetFocalPoint(camera_data["FocalPoint"])
    camera.SetViewUp(camera_data["ViewUp"])
    camera.SetClippingRange(camera_data["ClippingRange"])

def create_color_bar(ctf):
        params = colorbar_param(
            title='Combustion Flame',
            title_col=[1, 1, 1],
            label_col=[1, 1, 1],
            pos=[0.85, 0.2],
            width=60,
            height=300,
            nlabels=5,
            font_size=14,
            title_font_size=16
        )
        return vtk_colorbar.colorbar(ctf, params)

def load_camera_from_json(camera, filename):
    with open(filename, "r") as f:
        camera_data = json.load(f)
    camera.SetPosition(camera_data["Position"])
    camera.SetFocalPoint(camera_data["FocalPoint"])
    camera.SetViewUp(camera_data["ViewUp"])
    camera.SetClippingRange(camera_data["ClippingRange"])

class DVRFlame(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.setup_ui()
        self.setup_pipeline()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)
        self.vtk_widget = QVTKRenderWindowInteractor()  # QWidget created AFTER QApplication exists
        self.layout.addWidget(self.vtk_widget)


    def setup_pipeline(self):
        # Read data
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(self.args.input)
        reader.Update()
        scalar_range = reader.GetOutput().GetScalarRange()

        # Transfer functions
        ctf = vtk.vtkColorTransferFunction()
        ctf.AddRGBPoint(400, 0, 0, 0)
        ctf.AddRGBPoint(500, 86 / 255, 109 / 255, 214 / 255 )
        ctf.AddRGBPoint(3000, 210 / 255, 105 / 255, 93 / 255 )
        # ctf.AddRGBPoint(2900, 61 / 255.0, 136 / 255.0, 255 / 255.0)   # Cool regions
        ctf.AddRGBPoint(9000, 1.0, 1.0, 1.0)
        ctf.AddRGBPoint(12000, 207 / 255.0, 53 / 255.0, 46 / 255.0)
        ctf.AddRGBPoint(15000, 215 / 255.0, 120 / 255.0, 111 / 255.0)
       
        otf = vtk.vtkPiecewiseFunction()

        otf.AddPoint(400, 0.0)
        otf.AddPoint(500, 0.2)
        otf.AddPoint(1000, 0.0)

        otf.AddPoint(2000, 0.0)
        otf.AddPoint(3000, 0.5)
        otf.AddPoint(4000, 0.0)

        otf.AddPoint(8500, 0.0)
        otf.AddPoint(9000, 0.4)
        otf.AddPoint(9500, 0.0)

        otf.AddPoint(10000, 0.0)
        otf.AddPoint(12000, 0.5)
        otf.AddPoint(14000, 0.0)

        otf.AddPoint(14500, 0.0)
        otf.AddPoint(15000, 0.1)
        otf.AddPoint(15700, 0)

        # otf.AddPoint(14000, 0.0)
        # otf.AddPoint(15000, 0.2)
        # otf.AddPoint(16000, 0.0)
      
        # Volume properties
        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(ctf)
        volume_property.SetScalarOpacity(otf)
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # Mapper
        mapper = vtk.vtkSmartVolumeMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        mapper.SetSampleDistance(0.05)
        mapper.SetBlendModeToComposite()

        # Volume
        volume = vtk.vtkVolume()
        volume.SetMapper(mapper)
        volume.SetProperty(volume_property)

        # Renderer
        self.ren = vtk.vtkRenderer()
        self.ren.AddVolume(volume)
        self.ren.SetBackground(81 / 255.0, 87 / 255.0, 112 / 255.0)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.ren)

        scalar_bar = create_color_bar(ctf)
        self.ren.AddActor2D(scalar_bar.get())

        # Camera
        if self.args.camera:
            load_camera_from_json(self.ren.GetActiveCamera(), self.args.camera)

        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.iren.Initialize()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Flame dataset (.vti)')
    parser.add_argument('--camera', help='Camera settings (.json)')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    app = QApplication(sys.argv)
    window = DVRFlame(args)
    window.setWindowTitle('Flame DVR')
    window.resize(1024, 768)
    window.show()
    sys.exit(app.exec_())