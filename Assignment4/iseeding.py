#!/usr/bin/env python

from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow, QSlider, QGridLayout, QLabel, QPushButton, QTextEdit
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import Qt
import vtk
from vtk.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import sys
import argparse
import numpy as np
import json

class InteractiveSeedingUI(QMainWindow):
    def __init__(self, args, parent=None):
        QMainWindow.__init__(self, parent)
        self.args = args
        self.setup_ui()
        self.setup_vtk_pipeline()
        self.setup_sliders()
        self.setup_connections()
        self.setup_sphere_widget()

    def setup_ui(self):
        self.centralWidget = QWidget()
        self.gridlayout = QGridLayout(self.centralWidget)
        
        # VTK Widget
        self.vtkWidget = QVTKRenderWindowInteractor(self.centralWidget)
        
        # Slider
        self.count_slider = QSlider(Qt.Horizontal)
        self.count_label = QLabel("Seed Count:")
        
        # Layout
        self.gridlayout.addWidget(self.vtkWidget, 0, 0, 4, 4)
        self.gridlayout.addWidget(self.count_label, 4, 0)
        self.gridlayout.addWidget(self.count_slider, 4, 1)
        
        self.setCentralWidget(self.centralWidget)
        self.setWindowTitle("Interactive Streamline Seeding")

    def setup_vtk_pipeline(self):
        # Read input data
        self.reader = vtk.vtkXMLUnstructuredGridReader()
        self.reader.SetFileName(self.args.i)
        self.reader.Update()
        
        # Wing geometry
        wing_reader = vtk.vtkXMLPolyDataReader()
        wing_reader.SetFileName(self.args.g)
        wing_mapper = vtk.vtkDataSetMapper()
        wing_mapper.SetInputConnection(wing_reader.GetOutputPort())
        self.wing_actor = vtk.vtkActor()
        self.wing_actor.SetMapper(wing_mapper)
        self.wing_actor.GetProperty().SetColor(0.5, 0.5, 0.5)

        # Streamline setup
        self.point_source = vtk.vtkPointSource()
        self.point_source.SetNumberOfPoints(100)
        self.point_source.SetRadius(0.02)
        self.point_source.SetCenter(0.05, 0.0, 0.01)

        self.stream_tracer = vtk.vtkStreamTracer()
        self.stream_tracer.SetInputConnection(self.reader.GetOutputPort())
        self.stream_tracer.SetSourceConnection(self.point_source.GetOutputPort())
        self.stream_tracer.SetIntegratorTypeToRungeKutta45()
        self.stream_tracer.SetMaximumPropagation(1.0) 

        # Streamline mapper
        stream_mapper = vtk.vtkDataSetMapper()
        stream_mapper.SetInputConnection(self.stream_tracer.GetOutputPort())
        stream_mapper.SetScalarModeToUsePointFieldData()
        stream_mapper.SelectColorArray("velocity")
        stream_mapper.SetScalarRange(
            self.reader.GetOutput().GetPointData().GetArray("velocity").GetRange()
        )

        self.stream_actor = vtk.vtkActor()
        self.stream_actor.SetMapper(stream_mapper)

        # Pressure isosurface
        pressure_range = self.reader.GetOutput().GetPointData().GetArray("pressure").GetRange()
        contour = vtk.vtkContourFilter()
        contour.SetInputConnection(self.reader.GetOutputPort())
        contour.GenerateValues(8, pressure_range)
        
        contour_mapper = vtk.vtkDataSetMapper()
        contour_mapper.SetInputConnection(contour.GetOutputPort())
        contour_mapper.SetScalarRange( pressure_range )
        
        self.contour_actor = vtk.vtkActor()
        self.contour_actor.SetMapper(contour_mapper)
        self.contour_actor.GetProperty().SetOpacity(0.3)

        # Renderer setup
        self.ren = vtk.vtkRenderer()
        self.ren.AddActor(self.wing_actor)
        self.ren.AddActor(self.stream_actor)
        self.ren.AddActor(self.contour_actor)
        self.ren.SetBackground(0.1, 0.1, 0.1)
        self.vtkWidget.GetRenderWindow().AddRenderer(self.ren)

    def setup_sphere_widget(self): 
        # Create sphere widget
        self.sphere_widget = vtk.vtkSphereWidget()
        
        # Get VTK interactor from render window
        vtk_interactor = self.vtkWidget.GetRenderWindow().GetInteractor()
        
        self.sphere_widget.SetInteractor(vtk_interactor)
        self.sphere_widget.SetRepresentationToSurface()
        self.sphere_widget.GetSphereProperty().SetColor(1, 0, 0)  # Red color
        
        # Set initial position and size
        self.sphere_widget.SetCenter(self.point_source.GetCenter())
        self.sphere_widget.SetRadius(self.point_source.GetRadius())
        
        # Add observer for interaction events
        self.sphere_widget.AddObserver("InteractionEvent", self.update_seed_source)
        self.sphere_widget.On()

    def setup_sliders(self):
        # Seed count slider
        self.count_slider.setRange(10, 500)
        self.count_slider.setValue(100)

    def setup_connections(self):
        self.count_slider.valueChanged.connect(self.update_seed_count)

    def update_seed_source(self, obj, event):
        # Update point source from sphere widget
        self.point_source.SetCenter(self.sphere_widget.GetCenter())
        self.point_source.SetRadius(self.sphere_widget.GetRadius())
        self.update_streamlines()

    def update_seed_count(self, value):
        self.point_source.SetNumberOfPoints(value)
        self.update_streamlines()

    def update_streamlines(self):
        self.vtkWidget.GetRenderWindow().Render()

def get_program_parameters():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", type=str, help="path to vfem.vtu file")
    parser.add_argument("-g", type=str, help="path to wing.vtp file")
    return parser.parse_args()

if __name__ == "__main__":
    args = get_program_parameters()
    app = QApplication(sys.argv)
    window = InteractiveSeedingUI(args)
    window.resize(1024, 768)
    window.show()
    window.iren = window.vtkWidget.GetRenderWindow().GetInteractor()
    window.iren.Initialize()
    sys.exit(app.exec_())