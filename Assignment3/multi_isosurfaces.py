#!/usr/bin/env python

import sys
import argparse
import json
import vtk
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QGridLayout
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

import vtk_colorbar
from vtk_colorbar import colorbar_param, colorbar

def load_camera_from_json(camera, filename):
    with open(filename, 'r') as f:
        data = json.load(f)
    camera.SetPosition(data['Position'])
    camera.SetFocalPoint(data['FocalPoint'])
    camera.SetViewUp(data['ViewUp'])
    camera.SetClippingRange(data['ClippingRange'])

def create_color_bar(ctf):
        params = colorbar_param(
            title='Isovalues',
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

class MultiIsoWindow(QMainWindow):
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
        # Read input data
        reader = vtk.vtkXMLImageDataReader()
        reader.SetFileName(self.args.input)
        reader.Update()

        # Setup renderer with depth peeling
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetUseDepthPeeling(1)
        self.renderer.SetMaximumNumberOfPeels(100)
        self.renderer.SetOcclusionRatio(0.1)

        # Create color transfer function for the color bar
        ctf = vtk.vtkColorTransferFunction()
        sorted_isos = sorted(self.args.iso, key=lambda x: x[0])

        # Create each isosurface
        for i, iso in enumerate(sorted_isos):
            value, alpha, r, g, b = iso

            # Contour filter
            contour = vtk.vtkContourFilter()
            contour.SetInputConnection(reader.GetOutputPort())
            contour.SetValue(0, value)

            # Mapper
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(contour.GetOutputPort())
            mapper.ScalarVisibilityOff()

            # Actor
            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(r, g, b)
            actor.GetProperty().SetOpacity(alpha)
            self.renderer.AddActor(actor)

            # Add to color transfer function
            ctf.AddRGBPoint(value, r, g, b)

        # Create scalar bar
        scalar_bar = create_color_bar(ctf)
        self.renderer.AddActor2D(scalar_bar.get())
        self.renderer.SetBackground(81 / 255.0, 87 / 255.0, 112 / 255.0)

        # Load camera settings if provided
        if self.args.camera:
            load_camera_from_json(self.renderer.GetActiveCamera(), self.args.camera)

        # Add renderer to VTK widget
        self.vtk_widget.GetRenderWindow().AddRenderer(self.renderer)
        self.iren = self.vtk_widget.GetRenderWindow().GetInteractor()
        self.iren.Initialize()

def parse_args():
    parser = argparse.ArgumentParser(description='Visualize multiple isosurfaces with custom colors and opacities.')
    parser.add_argument('-i', '--input', required=True, help='Input dataset (.vti)')
    parser.add_argument('--iso', action='append', nargs=5, type=float, required=True,
                        metavar=('VALUE', 'ALPHA', 'R', 'G', 'B'),
                        help='Add an isosurface: value, opacity, red, green, blue')
    parser.add_argument('--camera', help='JSON file with camera settings')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()
    app = QApplication(sys.argv)
    window = MultiIsoWindow(args)
    window.setWindowTitle('Multi Isosurfaces')
    window.resize(1024, 768)
    window.show()
    sys.exit(app.exec_())