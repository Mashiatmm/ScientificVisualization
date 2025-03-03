#!/usr/bin/env python

import sys
import argparse
import json
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
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
            title='Human Head',
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

class DVRHead(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.setup_ui()
        self.setup_pipeline()

    def setup_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QGridLayout(self.central_widget)
        self.vtk_widget = QVTKRenderWindowInteractor()
        self.layout.addWidget(self.vtk_widget)

    def setup_pipeline(self):
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(self.args.input)
        reader.Update()

        ctf = vtk.vtkColorTransferFunction()
        ctf.AddRGBPoint(350, 0, 0, 0)
        ctf.AddRGBPoint(450, 0.8, 0.7, 0.6)
        ctf.AddRGBPoint(850, 0.8, 0.4, 0.4)
        ctf.AddRGBPoint(1100, 1.0, 1.0, 0.9)
        ctf.AddRGBPoint(2900, 1.0, 1.0, 1.0)
        ctf.AddRGBPoint(4300, 0, 0, 0)

        otf = vtk.vtkPiecewiseFunction()
        # Skin
        otf.AddPoint(350, 0.0)
        otf.AddPoint(450, 0.5)
        otf.AddPoint(550, 0.0)

        # Muscle
        otf.AddPoint(700, 0.0)
        otf.AddPoint(850, 0.6)
        otf.AddPoint(1000, 0.0)

        # Bone
        otf.AddPoint(1050, 0.0)
        otf.AddPoint(1100, 0.7)
        otf.AddPoint(1150, 0.0)

        # Teeth
        otf.AddPoint(2800, 0.0)
        otf.AddPoint(2900, 0.9)
        otf.AddPoint(3000, 0.0)

        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(ctf)
        volume_property.SetScalarOpacity(otf)
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        mapper = vtk.vtkSmartVolumeMapper()
        mapper.SetInputConnection(reader.GetOutputPort())
        mapper.SetSampleDistance(0.1)

        volume = vtk.vtkVolume()
        volume.SetMapper(mapper)
        volume.SetProperty(volume_property)

        self.ren = vtk.vtkRenderer()
        self.ren.AddVolume(volume)
        self.ren.SetBackground(0.1, 0.1, 0.2)
        self.vtk_widget.GetRenderWindow().AddRenderer(self.ren)

        scalar_bar = create_color_bar(ctf)
        self.ren.AddActor2D(scalar_bar.get())

        if self.args.camera:
            load_camera_from_json(self.ren.GetActiveCamera(), self.args.camera)

        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.iren.Initialize()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True, help='Head dataset (.vti)')
    parser.add_argument('--camera', help='Camera settings (.json)')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    app = QApplication(sys.argv)
    window = DVRHead(args)
    window.setWindowTitle('Head DVR')
    window.resize(1024, 768)
    window.show()
    sys.exit(app.exec_())