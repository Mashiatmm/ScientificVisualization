import vtk
import argparse
from SuperquadricTensorGlyph import SuperquadricTensorGlyph

def read_dti_volume(input_file):
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(input_file)
    reader.Update()
    return reader.GetOutput()

def determine_slice_positions(volume, args):
    print(volume.GetBounds())
    centerX, centerY, centerZ = volume.GetCenter()
    sliceX = args.X if args.X is not None else centerX
    sliceY = args.Y if args.Y is not None else centerY
    sliceZ = args.Z if args.Z is not None else centerZ
    return sliceX, sliceY, sliceZ

def create_plane_source(slice_position, orientation, bounds, dims):
    plane = vtk.vtkPlaneSource()
    if orientation == 'X':
        plane.SetOrigin(slice_position, bounds[2], bounds[4])
        plane.SetPoint1(slice_position, bounds[3], bounds[4])
        plane.SetPoint2(slice_position, bounds[2], bounds[5])
        plane.SetXResolution(dims[1] - 1)
        plane.SetYResolution(dims[2] - 1)
    elif orientation == 'Y':
        plane.SetOrigin(bounds[0], slice_position, bounds[4])
        plane.SetPoint1(bounds[1], slice_position, bounds[4])
        plane.SetPoint2(bounds[0], slice_position, bounds[5])
        plane.SetXResolution(dims[0] - 1)
        plane.SetYResolution(dims[2] - 1)
    elif orientation == 'Z':
        plane.SetOrigin(bounds[0], bounds[2], slice_position)
        plane.SetPoint1(bounds[1], bounds[2], slice_position)
        plane.SetPoint2(bounds[0], bounds[3], slice_position)
        plane.SetXResolution(dims[0] - 1)
        plane.SetYResolution(dims[1] - 1)
    plane.Update()
    return plane

def probe_volume_with_plane(volume, plane_source):
    probe = vtk.vtkProbeFilter()
    probe.SetInputConnection(plane_source.GetOutputPort())
    probe.SetSourceData(volume)
    probe.Update()
    return probe.GetOutput()

def create_tensor_glyphs(probed_slice, scale=1000, maxsize=10, gamma=5, resolution=20):
    glyph = SuperquadricTensorGlyph()
    glyph.SetInputData(probed_slice)
    glyph.SetGamma(gamma)
    glyph.SetMaxSize(maxsize)
    glyph.SetResolution(resolution)
    glyph.SetScale(scale)
    glyph.Update()
    return glyph.GetOutput()

def create_glyph_actor(glyph_data, color):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(glyph_data)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    return actor

def setup_renderer_and_window(actors):
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0, 0, 0)
    for actor in actors:
        renderer.AddActor(actor)
    renderer.ResetCamera()

    renWin = vtk.vtkRenderWindow()
    renWin.SetSize(800, 600)
    renWin.AddRenderer(renderer)
    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)
    return renderer, iren

def main():
    parser = argparse.ArgumentParser(description="Visualize DTI volume with superquadric tensor glyphs on orthogonal slices")
    parser.add_argument("-i", "--input", dest="i", required=True, help="Path to input DTI .vti file")
    parser.add_argument("-X", type=float, dest="X", help="X slice position (world coordinate)")
    parser.add_argument("-Y", type=float, dest="Y", help="Y slice position (world coordinate)")
    parser.add_argument("-Z", type=float, dest="Z", help="Z slice position (world coordinate)")
    args = parser.parse_args()

    # Read the DTI volume
    volume = read_dti_volume(args.i)

    # Determine slice positions
    sliceX, sliceY, sliceZ = determine_slice_positions(volume, args)

    # Prepare plane sources
    bounds = volume.GetBounds()
    dims = volume.GetDimensions()
    planeX = create_plane_source(sliceX, 'X', bounds, dims)
    planeY = create_plane_source(sliceY, 'Y', bounds, dims)
    planeZ = create_plane_source(sliceZ, 'Z', bounds, dims)

    # Probe the volume with each plane
    probedSliceX = probe_volume_with_plane(volume, planeX)
    probedSliceY = probe_volume_with_plane(volume, planeY)
    probedSliceZ = probe_volume_with_plane(volume, planeZ)

    # Create tensor glyphs for each slice
    glyphsX = create_tensor_glyphs(probedSliceX)
    glyphsY = create_tensor_glyphs(probedSliceY)
    glyphsZ = create_tensor_glyphs(probedSliceZ)

    # Create actors for the glyphs with distinct colors
    actorX = create_glyph_actor(glyphsX, (1.0, 0.0, 0.0))  # red for X slice
    actorY = create_glyph_actor(glyphsY, (0.0, 1.0, 0.0))  # green for Y slice
    actorZ = create_glyph_actor(glyphsZ, (0.0, 0.0, 1.0))  # blue for Z slice

    # Set up renderer and rendering window
    renderer, interactor = setup_renderer_and_window([actorX, actorY, actorZ])

    # Render and start interaction
    renderer.ResetCamera()
    interactor.Start()

if __name__ == "__main__":
    main()