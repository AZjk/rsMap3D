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
SampleName_list = ['Continuous_Pd_film_on_STO_001', 
                    ]
# scan numbers exactly as they are in the .vti file name.
#scans = ['104-106', '117-119', '129-131', '141-143', '153-155', '165-167', '177-179', '189-191', '201-203', '213-215', '331-333']
scans_list = [['27-28', '34-35', '44-45', '49-50', '55-56', '59-60']]
# Is the grid based on "hkl" or "qxyz"?
grid_type = "hkl"

# Setup some variables to use for plot slices and tile them along one main axis direction.
# this is the center of the RSM volume and where the slice would go through
slice_Origin = [0, 0, 1.93]
# normal direction of the slice
slice_normal = [0, 0, 1]
# tiling multiple images along this direction; and default viewing direction would be another in-plane one
slice_offSet_direction = [1, 0, 0]
# clipping the RSM3D volume so that we have better control of the tiling. This is the 'box' size here
clip_size = [0.4, 0.4, 0.6]
# use the 'box' dimension in this direction as the tiling offset
offset_unit = clip_size[slice_offSet_direction.index(1)]

# view from this direction in reciprocal space
view_direction= slice_normal
# color scale low and high limits
color_scale_low = 1.2
color_scale_high = 5.2

# Check the existence of the .vti files first
FileNames = []
LabelNames = []
for (scans, SampleName) in zip(scans_list, SampleName_list):
    for ScanN in scans:
        # build vti file name here for each RSM volume
        FileName = SampleName + f'_{ScanN}_{grid_type}.vti'
        thisFileName = os.path.join(PathName, SampleName, FileName)
        if os.path.isfile(thisFileName):
            LabelNames.append(FileName)
            FileNames.append(thisFileName)
        else:
            print(f"Make sure the filename {thisFileName} is valid. ")

# How many slices
num_plot = len(FileNames)
# the largest offset value
offset_max = offset_unit*int(num_plot/2)

for _ind1, (FileName, LabelName) in enumerate(zip(FileNames, LabelNames)):
    # build vti file name here for each RSM volume
    #thisFileName = os.path.join(PathName, SampleName, FileName)
    vti_data = XMLImageDataReader(FileName=FileName)

    # offset value for this slice
    _this_offset = -offset_max + offset_unit * _ind1
    # get active source.
    xMLImageDataReader = GetActiveSource()

    # rename source object
    RenameSource(LabelName, xMLImageDataReader)

    # get active view
    renderView1 = GetActiveViewOrCreate('RenderView')

    # create a new 'Calculator'
    calculator1 = Calculator(Input=vti_data)

    # Properties modified on calculator1
    calculator1.Function = 'log10(Scalars_)'
    
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

    # update the view to ensure updated data information
    renderView1.Update()

    # reset view to fit data
    renderView1.ResetCamera(False)

    # create a new 'Slice'
    slice1 = Slice(registrationName=f'Slice{_ind1+1}', Input=clip1)
    slice1.SliceType = 'Plane'
    slice1.HyperTreeGridSlicer = 'Plane'
    slice1.SliceOffsetValues = [0.0]

    # init the 'Plane' selected for 'SliceType'
    slice1.SliceType.Origin = slice_Origin
    slice1.SliceType.Normal = slice_normal
    
    # init the 'Plane' selected for 'HyperTreeGridSlicer'
    slice1.HyperTreeGridSlicer.Origin = slice_Origin

    # show data in view
    slice1Display = Show(slice1, renderView1, 'GeometryRepresentation')

    # trace defaults for the display properties.
    slice1Display.Representation = 'Surface'
    slice1Display.ColorArrayName = ['POINTS', 'Result']
    slice1Display.LookupTable = resultLUT
    slice1Display.SelectTCoordArray = 'None'
    slice1Display.SelectNormalArray = 'None'
    slice1Display.SelectTangentArray = 'None'
    slice1Display.OSPRayScaleArray = 'Result'
    slice1Display.OSPRayScaleFunction = 'PiecewiseFunction'
    slice1Display.SelectOrientationVectors = 'None'
    slice1Display.ScaleFactor = 0.02399998903274536
    slice1Display.SelectScaleArray = 'Result'
    slice1Display.GlyphType = 'Arrow'
    slice1Display.GlyphTableIndexArray = 'Result'
    slice1Display.GaussianRadius = 0.0011999994516372682
    slice1Display.SetScaleArray = ['POINTS', 'Result']
    slice1Display.ScaleTransferFunction = 'PiecewiseFunction'
    slice1Display.OpacityArray = ['POINTS', 'Result']
    slice1Display.OpacityTransferFunction = 'PiecewiseFunction'
    slice1Display.DataAxesGrid = 'GridAxesRepresentation'
    slice1Display.PolarAxes = 'PolarAxesRepresentation'

    # init the 'PiecewiseFunction' selected for 'ScaleTransferFunction'
    slice1Display.ScaleTransferFunction.Points = [0.0, 0.0, 0.5, 0.0, 8.617164190771732, 1.0, 0.5, 0.0]

    # init the 'PiecewiseFunction' selected for 'OpacityTransferFunction'
    slice1Display.OpacityTransferFunction.Points = [0.0, 0.0, 0.5, 0.0, 8.617164190771732, 1.0, 0.5, 0.0]

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

    #  OK, this below might not be correct, i don't quite understand 
    #   how it works.  Maybe it is not fixed?  
    # which axis label to display: 1 - z_min;  2 - y_min;  4 - x_min; 
    #                              8 - z_max; 16 - y_max; 32 - x_max
    #_labelFlag = np.array([4, 2, 1])
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
    # try to figure out which axes to label, probably not working well
    if _ind1 == 0:
        # label the axis-min on the lowest side of offset direction
        _tmp1 = np.array(slice_offSet_direction)!=0
        _axesToLable = sum( np.multiply(_tmp1, _labelFlag) )
        slice1Display.DataAxesGrid.AxesToLabel = _axesToLable
    elif _this_offset==0:
        # lable the axis-min orthorgonal to both offset and slice normal direction.
        _tmp1 = ( np.array(slice_offSet_direction) + np.array(slice_normal) ) == 0
        _axesToLable = sum( np.multiply(_tmp1, _labelFlag) )
        slice1Display.DataAxesGrid.AxesToLabel = _axesToLable
                
    # show axis labels
    slice1Display.DataAxesGrid.GridAxesVisibility = 1
    
    # show color bar/color legend
    slice1Display.SetScalarBarVisibility(renderView1, True)

    # update the view to ensure updated data information
    renderView1.Update()

    # toggle 3D widget visibility (only when running from the GUI)
    Hide3DWidgets(proxy=slice1.SliceType)

    # set active source
    SetActiveSource(slice1)

    # show data in view
    slice1Display = Show(slice1, renderView1, 'GeometryRepresentation')

    # show color bar/color legend
    slice1Display.SetScalarBarVisibility(renderView1, True)

    # Calculate how much offset this slice needs
    this_slice_offset = list( np.array(slice_offSet_direction) * (_this_offset) )

    # Properties modified on slice1Display
    slice1Display.Position = this_slice_offset

    # Properties modified on slice1Display.DataAxesGrid
    slice1Display.DataAxesGrid.Position = this_slice_offset

    # Properties modified on slice1Display.PolarAxes
    slice1Display.PolarAxes.Translation = this_slice_offset

    # reset view to fit data
    renderView1.ResetCamera(False)

    # update the view to ensure updated data information
    renderView1.Update()


# Apply a preset using its name. Note this may not work as expected when presets have duplicate names.
resultLUT.ApplyPreset('Jet', True)

# reset view to fit data
renderView1.ResetCamera()

# get color transfer function/color map for 'Result'
resultLUT = GetColorTransferFunction('Result')

# Rescale transfer function
resultLUT.RescaleTransferFunction(color_scale_low, color_scale_high)

# Properties modified on renderView1
renderView1.UseColorPaletteForBackground = 0

# Properties modified on renderView1
renderView1.Background = [1.0, 1.0, 1.0]

""" 
# get opacity transfer function/opacity map for 'Result'
resultPWF = GetOpacityTransferFunction('Result')

# Rescale transfer function
resultPWF.RescaleTransferFunction(color_scale_low, color_scale_high)
"""
#### saving camera placements for all active views

# current camera placement for renderView1
renderView1.CameraPosition = list(np.array(slice_Origin) + view_direction)
renderView1.CameraFocalPoint = slice_Origin
#renderView1.CameraPosition = [0.0249742791056633, -1.6546449800997225, 3.9885722398757935]
#renderView1.CameraFocalPoint = [0.0249742791056633, 0.00796423852443695, 3.9885722398757935]
renderView1.CameraViewUp = [0.0, 0.0, 1.0]
renderView1.CameraParallelScale = 0.25





#### uncomment the following to render all views
# RenderAllViews()
# alternatively, if you want to write images, you can use SaveScreenshot(...).
