#### import the simple module from the paraview
from paraview.simple import *
import numpy as np
import os
#### disable automatic camera reset on 'Show'
paraview.simple._DisableFirstRenderCameraReset()

# create a new 'XML Image Data Reader'
#PathName = 'X:\\data\\caoyue\\20240304_NSLS_ISR\\woods\\analysis_runtime'
PathName = 'Z:\\Data\\ChoiMinju\\202404_NSLSII\\analysis_runtime'
# this is the sample name, typically SPEC filename without the suffix
SampleName = 'Continuous_Pd_film_on_STO_001'
# scan numbers exactly as they are in the .vti file name.
scans = ['27-28']
# Is the grid based on "hkl" or "qxyz"?
grid_type = "hkl"

# Setup some variables to use for plot slices and tile them along one main axis direction.
# this is the center of the RSM volume and where the slice would go through
slice_Origin = [0, 0, 1.9]
# normal direction of the slice
slice_normals = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
# clipping the RSM3D volume so that we have better control of the tiling. This is the 'box' size here
clip_size = [0.4, 0.4, 0.6]

# view from this direction in reciprocal space
view_direction= slice_normals[0]
# color scale low and high limits
color_scale_low = 1.2
color_scale_high = 5.2

# Check the existence of the .vti files first; skip those that nonexist
FileNames = []
for ScanN in scans:
    # build vti file name here for each RSM volume
    FileName = SampleName + f'_{ScanN}_{grid_type}.vti'
    thisFileName = os.path.join(PathName, SampleName, FileName)
    if os.path.isfile(thisFileName):
        FileNames.append(FileName)
    else:
        print(f"Make sure the filename {thisFileName} is valid. ")

_ind0 = 1
for _ind1, FileName in enumerate(FileNames):
    # build vti file name here for each RSM volume
    thisFileName = os.path.join(PathName, SampleName, FileName)
    vti_data = XMLImageDataReader(FileName=thisFileName)

    # get active source.
    xMLImageDataReader = GetActiveSource()

    # rename source object
    RenameSource(FileName, xMLImageDataReader)

    # get active view
    renderView1 = GetActiveViewOrCreate('RenderView')
    # uncomment following to set a specific view size
    # renderView1.ViewSize = [1217, 918]

    # show data in view
    vti_dataDisplay = Show(vti_data, renderView1)
    # trace defaults for the display properties.
    vti_dataDisplay.Representation = 'Outline'

    # reset view to fit data
    renderView1.ResetCamera()

    # update the view to ensure updated data information
    renderView1.Update()

    # create a new 'Calculator'
    calculator1 = Calculator(Input=vti_data)
    # Properties modified on calculator1
    calculator1.Function = 'log10(Scalars_)'
    # show data in view
    calculator1Display = Show(calculator1, renderView1)
    # trace defaults for the display properties.
    calculator1Display.Representation = 'Outline'
    # hide data in view
    Hide(vti_data, renderView1)
    # hide data in view
    Hide(calculator1, renderView1)

    # update the view to ensure updated data information
    renderView1.Update()

    # create a new 'Clip'
    clip1 = Clip(registrationName=f'Clip{_ind1+1}', Input=calculator1)
    # Properties modified on clip1
    clip1.ClipType = 'Box'
    # Properties modified on clip1.ClipType
    clip1.ClipType.Position = list(np.array(slice_Origin) - np.array(clip_size)/2) 
    clip1.ClipType.Length = clip_size
    # get active view
    renderView1 = GetActiveViewOrCreate('RenderView')
    # show data in view
    clip1Display = Show(clip1, renderView1, 'UnstructuredGridRepresentation')
    # get color transfer function/color map for 'Result'
    resultLUT = GetColorTransferFunction('Result')

    # hide data in view
    Hide(clip1, renderView1)

    # create a new 'Slice'
    for slice_normal in slice_normals:
        slice1 = Slice(registrationName=f'Slice{_ind0}', Input=clip1)
        slice1.SliceType = 'Plane'
        slice1.HyperTreeGridSlicer = 'Plane'
        slice1.SliceOffsetValues = [0.0]

        # Properties modified on slice1.SliceType
        slice1.SliceType.Origin = slice_Origin
        slice1.SliceType.Normal = slice_normal

        # show data in view
        slice1Display = Show(slice1, renderView1)
        # trace defaults for the display properties.
        slice1Display.Representation = 'Surface'

        # show color bar/color legend
        slice1Display.SetScalarBarVisibility(renderView1, True)

        # update the view to ensure updated data information
        renderView1.Update()
        _ind0 += 1 

        # init the 'GridAxesRepresentation' selected for 'DataAxesGrid'
        slice1Display.DataAxesGrid.GridColor = [0.0, 0.6666666666666666, 1.0]
        slice1Display.DataAxesGrid.ShowTicks = 0
        slice1Display.DataAxesGrid.AxesToLabel = 0
        slice1Display.DataAxesGrid.ShowEdges = 0
        # settings for font and size for labels and titles
        slice1Display.DataAxesGrid.XTitle = 'H (rlu)'
        slice1Display.DataAxesGrid.YTitle = 'K (rlu)'
        slice1Display.DataAxesGrid.ZTitle = 'L (rlu)'
        slice1Display.DataAxesGrid.XTitleColor = [0.0, 0.0, 0.0]
        slice1Display.DataAxesGrid.XTitleFontFamily = 'Times'
        slice1Display.DataAxesGrid.XTitleFontSize = 28
        slice1Display.DataAxesGrid.XLabelColor = [0.0, 0.0, 0.0]
        slice1Display.DataAxesGrid.XLabelFontFamily = 'Times'
        slice1Display.DataAxesGrid.XLabelFontSize = 20
        slice1Display.DataAxesGrid.XAxisPrecision = 0
        slice1Display.DataAxesGrid.YTitleColor = [0.0, 0.0, 0.0]
        slice1Display.DataAxesGrid.YTitleFontFamily = 'Times'
        slice1Display.DataAxesGrid.YTitleFontSize = 28
        slice1Display.DataAxesGrid.YLabelColor = [0.0, 0.0, 0.0]
        slice1Display.DataAxesGrid.YLabelFontFamily = 'Times'
        slice1Display.DataAxesGrid.YLabelFontSize = 20
        slice1Display.DataAxesGrid.YAxisPrecision = 0
        slice1Display.DataAxesGrid.ZTitleColor = [0.0, 0.0, 0.0]
        slice1Display.DataAxesGrid.ZTitleFontFamily = 'Times'
        slice1Display.DataAxesGrid.ZTitleFontSize = 28
        slice1Display.DataAxesGrid.ZLabelColor = [0.0, 0.0, 0.0]
        slice1Display.DataAxesGrid.ZLabelFontFamily = 'Times'
        slice1Display.DataAxesGrid.ZLabelFontSize = 20
        slice1Display.DataAxesGrid.ZAxisPrecision = 0

        _labelFlag = np.array([1, 2, 4])
        
        # figure out what the label values would be on each axis
        _tmp1 = slice_Origin[2]
        _tmp2 = clip_size[2]/2
        slice1Display.DataAxesGrid.ZAxisLabels = [_tmp1-_tmp2, _tmp1, _tmp1+_tmp2]
        _tmp1 = slice_Origin[0]
        _tmp2 = clip_size[0]/2
        slice1Display.DataAxesGrid.XAxisLabels = [_tmp1-_tmp2, _tmp1, _tmp1+_tmp2]
        _tmp1 = slice_Origin[1]
        _tmp2 = clip_size[1]/2
        slice1Display.DataAxesGrid.YAxisLabels = [_tmp1-_tmp2, _tmp1, _tmp1+_tmp2]
        # display all 3 lower axis side labels/titles
        slice1Display.DataAxesGrid.AxesToLabel = 7
        # show axis labels
        slice1Display.DataAxesGrid.GridAxesVisibility = 1
        
        # show color bar/color legend
        slice1Display.SetScalarBarVisibility(renderView1, True)

        # toggle 3D widget visibility (only when running from the GUI)
        Hide3DWidgets(proxy=slice1.SliceType)

# update the view to ensure updated data information
renderView1.Update()

# Apply a preset using its name. Note this may not work as expected when presets have duplicate names.
resultLUT.ApplyPreset('Jet', True)

#paraview.simple._DisableFirstRenderCameraReset()
#
# get active view
renderView1 = GetActiveViewOrCreate('RenderView')
# uncomment following to set a specific view size
# renderView1.ViewSize = [1217, 918]

# reset view to fit data
renderView1.ResetCamera()

# get color transfer function/color map for 'Result'
resultLUT = GetColorTransferFunction('Result')

# Rescale transfer function
resultLUT.RescaleTransferFunction(color_scale_low, color_scale_high)

# get opacity transfer function/opacity map for 'Result'
resultPWF = GetOpacityTransferFunction('Result')

# Rescale transfer function
resultPWF.RescaleTransferFunction(color_scale_low, color_scale_high)

# Properties modified on renderView1
renderView1.UseColorPaletteForBackground = 0
# Properties modified on renderView1
renderView1.Background = [1.0, 1.0, 1.0]

#### saving camera placements for all active views

# current camera placement for renderView1
renderView1.CameraPosition = list(np.array(slice_Origin) + slice_normals[0])
renderView1.CameraFocalPoint = slice_Origin
#renderView1.CameraPosition = [0.0249742791056633, -1.6546449800997225, 3.9885722398757935]
#renderView1.CameraFocalPoint = [0.0249742791056633, 0.00796423852443695, 3.9885722398757935]
renderView1.CameraViewUp = [0.0, 0.0, 1.0]
renderView1.CameraParallelScale = 0.5





#### uncomment the following to render all views
# RenderAllViews()
# alternatively, if you want to write images, you can use SaveScreenshot(...).
