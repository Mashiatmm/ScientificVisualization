import vtk
import argparse
import numpy as np
import random

from TensorLines import TensorLines

def read_volume(filename):
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()

def read_dti_volume(filename):
    reader = vtk.vtkXMLImageDataReader()
    reader.SetFileName(filename)
    reader.Update()
    return reader.GetOutput()

def create_fa_volume_actor(fa_image):
    ctf = vtk.vtkColorTransferFunction()
    otf = vtk.vtkPiecewiseFunction()

    fa_range = fa_image.GetPointData().GetScalars().GetRange()  # (minFA, maxFA)
    minFA, maxFA = fa_range[0], fa_range[1]

    ctf.AddRGBPoint(minFA, 0, 0, 0)
    ctf.AddRGBPoint(maxFA, 1.0, 1.0, 1.0)

    otf.AddPoint(minFA, 0.0)
    otf.AddPoint(0.2 * maxFA, 0.0)
    otf.AddPoint(0.4 * maxFA, 0.2)
    otf.AddPoint(0.5 * maxFA, 0.0)
    otf.AddPoint(0.6 * maxFA, 0.5)
    otf.AddPoint(0.75 * maxFA, 0.0)
    otf.AddPoint(0.9 * maxFA, 0.7)
    otf.AddPoint(maxFA, 0.0)

    volume_property = vtk.vtkVolumeProperty()
    volume_property.SetColor(ctf)
    volume_property.SetScalarOpacity(otf)
    volume_property.SetInterpolationTypeToLinear()
    volume_property.ShadeOff()       
    volume_property.SetAmbient(0.1)  
    volume_property.SetDiffuse(0.9)
    volume_property.SetSpecular(0.0)

    volume_mapper = vtk.vtkGPUVolumeRayCastMapper()
    volume_mapper.SetInputData(fa_image)

    volume_actor = vtk.vtkVolume()
    volume_actor.SetMapper(volume_mapper)
    volume_actor.SetProperty(volume_property)

    return volume_actor

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

def create_seed_points(clipping_planes, num_total_samples=5000):
    return combine_sampled_plane_points(clipping_planes, num_total_samples)


def main():
    parser = argparse.ArgumentParser(
        description="Visualize FA volume (in white) with volume rendering + DTI fiber tracts."
    )
    parser.add_argument("-i", "--input", required=True, help="Path to input DTI .vti file (with tensors)")
    parser.add_argument("--fa", required=True, help="Path to FA .vti file (scalar volume)")
    args = parser.parse_args()

    dti_volume = read_dti_volume(args.input)
    fa_volume = read_volume(args.fa)

    fa_volume_actor = create_fa_volume_actor(fa_volume)
   
    tlines = TensorLines()
    tlines.SetMinFA(0.3)
    tlines.SetMaxLength(150)
    tlines.SetMaxNumberOfSteps(1000)
    tlines.SetStepSize(1.0)

    tlines.SetInputDataObject(dti_volume)

    sliceX, sliceY, sliceZ = [76, 70, 90]

    bounds = dti_volume.GetBounds()
    dims = dti_volume.GetDimensions()

    planeX_source = create_plane_source(sliceX, 'X', bounds, dims)
    planeY_source = create_plane_source(sliceY, 'Y', bounds, dims)
    planeZ_source = create_plane_source(sliceZ, 'Z', bounds, dims)

    planeX_source.Update()
    planeY_source.Update()
    planeZ_source.Update()

    polyX = planeX_source.GetOutput() 
    polyY = planeY_source.GetOutput() 
    polyZ = planeZ_source.GetOutput() 


    clipping_planes = [polyX, polyY, polyZ]  
    seeds = create_seed_points(clipping_planes, num_total_samples=5000)
    tlines.SetSource(seeds)
    tlines.Update()

    fiber_polydata = tlines.GetOutput()

    fiber_mapper = vtk.vtkPolyDataMapper()
    fiber_mapper.SetInputData(fiber_polydata)

    fiber_actor = vtk.vtkActor()
    fiber_actor.SetMapper(fiber_mapper)
    fiber_actor.GetProperty().SetLineWidth(2.0)

    renderer = vtk.vtkRenderer()
    renderer.AddVolume(fa_volume_actor)
    renderer.AddActor(fiber_actor)
    renderer.SetBackground(0, 0, 0)

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
