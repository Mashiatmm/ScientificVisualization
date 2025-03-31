import vtk
import argparse
import random
from TensorLines import TensorLines

from tensor_glyphs import (
    read_dti_volume,
    determine_slice_positions,
    create_plane_source,
)

def sample_plane_points(polydata, num_samples):
    
    num_points = polydata.GetNumberOfPoints()
    if num_samples >= num_points:
        return polydata  # No need to sample if we want more or equal points

    indices = random.sample(range(num_points), num_samples)
    sampled_points = vtk.vtkPoints()
    for index in indices:
        x, y, z = polydata.GetPoint(index)
        sampled_points.InsertNextPoint(x, y, z)

    sampled_polydata = vtk.vtkPolyData()
    sampled_polydata.SetPoints(sampled_points)
    return sampled_polydata

def combine_sampled_plane_points(polydatas, num_total_samples=5000):
    active_planes = [pd for pd in polydatas if pd is not None and pd.GetNumberOfPoints() > 0]
    num_active = len(active_planes)
    if num_active == 0:
        seed_poly_data = vtk.vtkPolyData()
        seed_poly_data.SetPoints(vtk.vtkPoints())
        return seed_poly_data

    samples_per_plane = num_total_samples // num_active
    remaining_samples = num_total_samples % num_active

    all_points = vtk.vtkPoints()
    for i, pd in enumerate(active_planes):
        n_samples = samples_per_plane + (1 if i < remaining_samples else 0)
        sampled_pd = sample_plane_points(pd, n_samples)
        num_pts = sampled_pd.GetNumberOfPoints()
        for j in range(num_pts):
            x, y, z = sampled_pd.GetPoint(j)
            all_points.InsertNextPoint(x, y, z)

    seed_poly_data = vtk.vtkPolyData()
    seed_poly_data.SetPoints(all_points)
    return seed_poly_data

def main():
    parser = argparse.ArgumentParser(
        description="Hyperstreamlines seeded from sampled points on planes used for Task 1 glyphs."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input DTI .vti file")
    parser.add_argument("-X", type=float, default = 76, dest="X", help="X slice position (world coordinate)")
    parser.add_argument("-Y", type=float, default = 70, dest="Y", help="Y slice position (world coordinate)")
    parser.add_argument("-Z", type=float, default = 90, dest="Z", help="Z slice position (world coordinate)")
    args = parser.parse_args()

    volume = read_dti_volume(args.input)

    sliceX, sliceY, sliceZ = determine_slice_positions(volume, args)

    bounds = volume.GetBounds()
    dims = volume.GetDimensions()

    planeX_source = create_plane_source(sliceX, 'X', bounds, dims)
    planeY_source = create_plane_source(sliceY, 'Y', bounds, dims)
    planeZ_source = create_plane_source(sliceZ, 'Z', bounds, dims)

    planeX_source.Update()
    planeY_source.Update()
    planeZ_source.Update()

    polyX = planeX_source.GetOutput() if args.X is not None or (args.X is None and args.Y is None and args.Z is None) else None
    polyY = planeY_source.GetOutput() if args.Y is not None or (args.X is None and args.Y is None and args.Z is None) else None
    polyZ = planeZ_source.GetOutput() if args.Z is not None or (args.X is None and args.Y is None and args.Z is None) else None

    active_polys = []
    if args.X is not None or (args.X is None and args.Y is None and args.Z is None):
        active_polys.append(polyX)
    if args.Y is not None or (args.X is None and args.Y is None and args.Z is None):
        active_polys.append(polyY)
    if args.Z is not None or (args.X is None and args.Y is None and args.Z is None):
        active_polys.append(polyZ)

    seeds = combine_sampled_plane_points([p for p in active_polys if p is not None])

    tlines = TensorLines()
    tlines.SetMinFA(0.3)          
    tlines.SetMaxLength(150)      
    tlines.SetMaxNumberOfSteps(1000)
    tlines.SetStepSize(1.0)

    tlines.SetInputDataObject(volume)
    tlines.SetSource(seeds)
    tlines.Update()

    # 6) Get the resulting fiber tracts
    fibers = tlines.GetOutput()

    # 7) Visualize
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(fibers)

    actor = vtk.vtkActor()
    actor.SetMapper(mapper)

    renderer = vtk.vtkRenderer()
    renderer.SetBackground(0, 0, 0)
    renderer.AddActor(actor)

    renWin = vtk.vtkRenderWindow()
    renWin.AddRenderer(renderer)
    renWin.SetSize(800, 600)

    iren = vtk.vtkRenderWindowInteractor()
    iren.SetRenderWindow(renWin)

    renderer.ResetCamera()
    renWin.Render()
    iren.Start()

if __name__ == "__main__":
    main()