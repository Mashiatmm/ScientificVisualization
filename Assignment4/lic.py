import vtk
import argparse

def create_lic_plane(x_pos, wing_bounds, vector_source, y_res=500, z_res=500):
    image = vtk.vtkImageData()
    image.SetDimensions(1, y_res, z_res)
    
    vector_bounds = wing_bounds
    y_min, y_max = vector_bounds[2] , vector_bounds[3] 
    z_min, z_max = vector_bounds[4] - 0.2, vector_bounds[5] + 0.2
    
    spacing = (
        1.0,  
        (y_max - y_min)/(y_res-1),  
        (z_max - z_min)/(z_res-1)  
    )
    origin = (x_pos, y_min, z_min)
    image.SetSpacing(spacing)
    image.SetOrigin(origin)

    num_points = image.GetNumberOfPoints()
    pressure_array = vtk.vtkFloatArray()
    pressure_array.SetName("pressure")
    pressure_array.SetNumberOfComponents(3)
    pressure_array.SetNumberOfTuples(num_points)
    for i in range(num_points):
        pressure_array.SetTuple3(i, 0, 0, 0)
    image.GetPointData().SetVectors(pressure_array)



    probe = vtk.vtkProbeFilter()
    probe.SetInputData(image)
    probe.SetSourceConnection(vector_source.GetOutputPort())
    
    lic = vtk.vtkImageDataLIC2D()
    lic.SetInputConnection(probe.GetOutputPort())
    lic.SetSteps(100)                # Number of integration steps
    lic.SetStepSize(0.5)          # Step size as fraction of domain
    lic.Update()

    plane = vtk.vtkPlaneSource()
    plane.SetOrigin(image.GetOrigin())
    plane.SetPoint1(x_pos, y_max, z_min)
    plane.SetPoint2(x_pos, y_min, z_max)
    plane.SetResolution(1, 1)
  
    lut = vtk.vtkLookupTable()
    lut.SetNumberOfTableValues(256)
    lut.SetHueRange(0, 0)        
    lut.SetSaturationRange(0, 0) 
    lut.SetValueRange(0, 1)      
    lut.Build()

    map_to_gray = vtk.vtkImageMapToColors()
    map_to_gray.SetLookupTable(lut)
    map_to_gray.SetInputConnection(lic.GetOutputPort())
    map_to_gray.Update()

    texture = vtk.vtkTexture()
    texture.SetInputConnection(map_to_gray.GetOutputPort())
    texture.InterpolateOn()
    
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(plane.GetOutputPort())
    
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.SetTexture(texture)
    
    return actor

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, 
                      help="Path to vector field VTU file")
    parser.add_argument("-g", "--geometry", required=True,
                      help="Path to wing geometry VTP file")
    args = parser.parse_args()

    vfem_reader = vtk.vtkXMLUnstructuredGridReader()
    vfem_reader.SetFileName(args.input)
    vfem_reader.Update()
    wing_reader = vtk.vtkXMLPolyDataReader()
    wing_reader.SetFileName(args.geometry)
    wing_reader.Update()
    wing_bounds = wing_reader.GetOutput().GetBounds()

    wing_mapper = vtk.vtkPolyDataMapper()
    wing_mapper.SetInputConnection(wing_reader.GetOutputPort())
    wing_actor = vtk.vtkActor()
    wing_actor.SetMapper(wing_mapper)
    wing_actor.GetProperty().SetColor(0.3, 0.3, 0.3)

    plane_positions = [0.1, 0.3, 0.5]

    lic_actors = []
    for x in plane_positions:
        lic_actors.append( create_lic_plane(x, wing_bounds, vfem_reader) )
    
    renderer = vtk.vtkRenderer()
    renderer.AddActor(wing_actor)
    for actor in lic_actors:
        renderer.AddActor(actor)

    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    render_window.SetSize(1600, 900)
    renderer.SetBackground(0.1, 0.1, 0.1)

    render_window.Render()

    interactor = vtk.vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)
    interactor.Start()

if __name__ == "__main__":
    main()