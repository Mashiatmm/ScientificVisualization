import vtk
import argparse

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", type=str, help="path to vfem.vtu file")
    parser.add_argument("-g", type=str, help="path to wing.vtp file")

    return parser.parse_args()

def read_input(args):
    vfem_reader =vtk.vtkXMLUnstructuredGridReader()
    vfem_reader.SetFileName(args.i)
    wing_reader = vtk.vtkXMLPolyDataReader()
    wing_reader.SetFileName(args.g)
    wing_reader.Update()
    return wing_reader, vfem_reader


def build_actor(reader, lut = None, prange = None):
    mapper = vtk.vtkDataSetMapper()
    mapper.SetInputConnection(reader.GetOutputPort())
    if lut != None:
        mapper.SetLookupTable(lut)
        mapper.SetScalarRange(prange)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    return actor


def build_arrow_plane_actor(reader_output_port, x, wing_bounds, lut):
    vector_bounds = wing_bounds
    y_min, y_max = vector_bounds[2] , vector_bounds[3] 
    z_min, z_max = vector_bounds[4] - 0.2, vector_bounds[5] + 0.2
   
    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(x, y_min, z_min)
    plane.SetPoint1(x, y_max, z_min)
    plane.SetPoint2(x, y_min, z_max)
    plane.SetResolution(50, 50)
  
    # trans = vtk.vtkTransform()
    # trans.Translate(x, 0, 0)
    # trans.RotateY(90)

    # tpd_filter = vtk.vtkTransformPolyDataFilter()
    # tpd_filter.SetInputConnection(plane.GetOutputPort())
    # tpd_filter.SetTransform(trans)

    probe_filter = vtk.vtkProbeFilter()
    probe_filter.SetInputConnection(plane.GetOutputPort())
    probe_filter.SetSourceConnection(reader_output_port)

    arrow_source = vtk.vtkArrowSource()
    arrow_source.SetShaftResolution(20)
    arrow_source.SetTipResolution(20)
    arrow_source.SetShaftRadius(0.02)
    arrow_source.SetTipRadius(0.1)

    arrow_glyph_filter = vtk.vtkGlyph3D()
    arrow_glyph_filter.SetScaleFactor(0.000001)
    arrow_glyph_filter.SetInputConnection(probe_filter.GetOutputPort())
    arrow_glyph_filter.SetSourceConnection(arrow_source.GetOutputPort())
    return arrow_glyph_filter


def inspect_vtu(file_path):
    reader = vtk.vtkXMLUnstructuredGridReader()
    reader.SetFileName(file_path)
    reader.Update()  

    data = reader.GetOutput()

    print(f"Number of Points: {data.GetNumberOfPoints()}")
    print(f"Number of Cells: {data.GetNumberOfCells()}")
    
    point_data = data.GetPointData()
    print("\nPoint Data Arrays:")
    for i in range(point_data.GetNumberOfArrays()):
        array_name = point_data.GetArrayName(i)
        array = point_data.GetArray(i)
        print(f"  {i}. {array_name} - {array.GetNumberOfComponents()} components")

    cell_data = data.GetCellData()
    print("\nCell Data Arrays:")
    for i in range(cell_data.GetNumberOfArrays()):
        array_name = cell_data.GetArrayName(i)
        array = cell_data.GetArray(i)
        print(f"  {i}. {array_name} - {array.GetNumberOfComponents()} components")

    print("\nBounds of the dataset:", data.GetBounds())


def main():
    args = parse_args()
    wing_reader, vfem_reader = read_input(args)

    vfem_reader.Update()
    # pressure_data = vfem_reader.GetOutput().GetPointData().GetArray('pressure')
    # prange = pressure_data.GetRange()
    prange = [43000, 45000]

    lut = vtk.vtkColorTransferFunction()
    lut.AddRGBPoint(prange[0], 0, 0, 1) 
    lut.AddRGBPoint(prange[1], 1, 1, 0) 
    
    scalar_bar = vtk.vtkScalarBarActor()
    scalar_bar.SetLookupTable(lut)
    scalar_bar.SetTitle("Pressure")
    scalar_bar.SetNumberOfLabels(5)
    scalar_bar.SetPosition(0.9, 0.1)
    scalar_bar.SetWidth(0.08)
    scalar_bar.SetHeight(0.4)


    wingBounds = wing_reader.GetOutput().GetBounds()
    plane_x_coords = [0.1, 0.3, 0.5]
    arrow_actors = []
    for x in plane_x_coords:
        arrow_glyph_filter = build_arrow_plane_actor(vfem_reader.GetOutputPort(), x, wingBounds, lut)
        arrow_actor = build_actor(arrow_glyph_filter, lut, prange)
        arrow_actors.append(arrow_actor)


    wing_actor = build_actor(wing_reader)
    wing_actor.GetProperty().SetColor(0.4, 0.4, 0.4)
    renderer = vtk.vtkRenderer()

    renderer.AddActor(scalar_bar)
    renderer.AddActor(wing_actor)
    for actor in arrow_actors:
        renderer.AddActor(actor)

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
