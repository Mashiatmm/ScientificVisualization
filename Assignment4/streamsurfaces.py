import vtk
import argparse


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", type=str, help="path to vfem.vtu file")
    parser.add_argument("-g", type=str, help="path to wing.vtp file")
    return parser.parse_args()

def read_vfem_velocity(vfem_filename):
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(vfem_filename)
    reader.Update()
    velocity_range = reader.GetOutput().GetPointData().GetArray("velocity").GetRange()
    print(velocity_range)
    return reader, velocity_range


def build_source_around_vortices(n_seeds):
    seeds =vtk.vtkLineSource()
    seeds.SetResolution(n_seeds)

    trans_0 = vtk.vtkTransform()
    trans_0.Translate(0.05, 0.01, 0.01)
    trans_0.Scale(0.1, 1, 1)

    tpd_0 = vtk.vtkTransformPolyDataFilter()
    tpd_0.SetInputConnection(seeds.GetOutputPort())
    tpd_0.SetTransform(trans_0)

    trans_1 = vtk.vtkTransform()
    trans_1.Translate(0.05, -0.01, 0.01)
    trans_1.Scale(0.1, 1, 1)

    tpd_1 = vtk.vtkTransformPolyDataFilter()
    tpd_1.SetInputConnection(seeds.GetOutputPort())
    tpd_1.SetTransform(trans_1)

    append_filter = vtk.vtkAppendPolyData()
    append_filter.AddInputConnection(tpd_0.GetOutputPort())
    append_filter.AddInputConnection(tpd_1.GetOutputPort())

    return append_filter

def build_velocity_actor(output_port, velocity_range):
    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputConnection(output_port)
    mapper.GetLookupTable().SetVectorModeToMagnitude()
    mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray("velocity")
    mapper.SetScalarRange(velocity_range)
    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(mapper.GetLookupTable()) 
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    return actor, scalar_bar

   
def build_wing_actor(filename):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(filename)

    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputConnection(reader.GetOutputPort())

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    return actor

def main():
    args = parse_args()
    vfem_filename = args.i

    reader, velocity_range = read_vfem_velocity(vfem_filename)

    # seeds = vtk.vtkLineSource()
    # seeds.SetResolution(100)

    # trans = vtk.vtkTransform()
    # trans.RotateZ(90)
    # trans.Scale(0.1, 1, 1)
    # trans.Translate(0.1, 0, 0.0)

    # tpd_filter = vtk.vtkTransformPolyDataFilter()
    # tpd_filter.SetInputConnection(seeds.GetOutputPort())
    # tpd_filter.SetTransform(trans)
    source = build_source_around_vortices(400)

    stream_surface = vtk.vtkStreamSurface()
    stream_surface.SetSourceConnection(source.GetOutputPort())
    stream_surface.SetInputConnection(reader.GetOutputPort())
    stream_surface.SetMaximumPropagation(1.5)

    stream_actor, scalar_bar = build_velocity_actor(stream_surface.GetOutputPort(), velocity_range)

    wing_actor = build_wing_actor(args.g)
    wing_actor.GetProperty().SetColor(0.4, 0.4, 0.4)

    renderer = vtk.vtkRenderer()
    renderer.AddActor(stream_actor)
    renderer.AddActor(wing_actor)
    renderer.AddActor(scalar_bar)
    colors = vtk.vtkNamedColors()
    renderer.SetBackground(colors.GetColor3d("Black"))

    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(640, 480)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    interactor.Start()



if __name__ == "__main__":
    main()