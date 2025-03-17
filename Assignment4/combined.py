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
    pressure_range = reader.GetOutput().GetPointData().GetArray("pressure").GetRange()
    # pressure_range = [43000, 45000]
    print(velocity_range)
    return reader, velocity_range, pressure_range

def build_source_around_vortices(n_seeds):
    seeds =vtk.vtkPointSource()
    seeds.SetRadius(0.01)
    seeds.SetNumberOfPoints(n_seeds)

    trans_0 = vtk.vtkTransform()
    trans_0.Translate(0.05, 0.01, 0.01)

    tpd_0 = vtk.vtkTransformPolyDataFilter()
    tpd_0.SetInputConnection(seeds.GetOutputPort())
    tpd_0.SetTransform(trans_0)

    trans_1 = vtk.vtkTransform()
    trans_1.Translate(0.05, -0.01, 0.01)

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

def build_window(actors, depth_peeling = False):
    renderer = vtk.vtkRenderer()
    for actor in actors:
        renderer.AddActor(actor)
   
    colors = vtk.vtkNamedColors()
    renderer.SetBackground(colors.GetColor3d("Gray"))

    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(640, 480)

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    if depth_peeling:
        render_window.SetAlphaBitPlanes(True)
        render_window.SetMultiSamples(0)
        renderer.SetUseDepthPeeling(True)
        renderer.SetMaximumNumberOfPeels(100)
        renderer.SetOcclusionRatio(0.0)

    return interactor


def main():
    args = parse_args()

    wing_filename = args.g
    vfem_filename = args.i

    seeds = vtk.vtkPlaneSource()
    seeds.SetResolution(15, 15)
    seeds.SetNormal(1, 0, 0)

    reader, velocity_range, pressure_range = read_vfem_velocity(vfem_filename)

    source = build_source_around_vortices(n_seeds=50)

    streamline = vtk.vtkStreamTracer()
    streamline.SetSourceConnection(source.GetOutputPort())
    streamline.SetInputConnection(reader.GetOutputPort())

    streamline_actor, _ = build_velocity_actor(streamline.GetOutputPort(), velocity_range)


    contour = vtk.vtkContourFilter()
    contour.SetInputConnection(reader.GetOutputPort())
    contour.GenerateValues(8, pressure_range)

    contour_mapper = vtk.vtkDataSetMapper()
    contour_mapper.SetInputConnection(contour.GetOutputPort())
    contour_mapper.SetScalarRange(pressure_range)

    contour_actor = vtk.vtkActor()
    contour_actor.SetMapper(contour_mapper)
    contour_actor.GetProperty().SetOpacity(0.25)

    build_window(
        [build_wing_actor(wing_filename), streamline_actor, contour_actor],
        depth_peeling=True,
    ).Start()


if __name__ == "__main__":
    main()