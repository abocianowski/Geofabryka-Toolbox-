Geofabryka ToolBox is a set of tools supporting digitization, modification and creation of new polygon elements.
The plug-in consists of four tools:
- Cut elements,
- Add One Side Buffer,
- Fill the empty spaces,
- Attributes join by line

Each of the above tools requires the same coordinate system for the modified layers.
Each of the tools is described below:

### - Cut elements

The tool enables cutting out the common part from selected layers and saving it to the target layer. Topological points at the intersections will be added to each layer.


Source objects - layers 1 and 2:
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/1.jpg?raw=true" alt="1.jpg">


Specifying the common area to cut:
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/2.jpg?raw=true" alt="2.jpg">

The common part was cut from layers 1 and 2, then saved in the target layer (layer 3):
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/3.jpg?raw=true" alt="3.jpg">


### - Add One Side Buffer
The tool allows you to add a new polygon, which is a buffer from a selected object.


The first step after activating the tool is to select the source object - just click in the map window. The layer will be selected automatically based on the selected object in the map.
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/4.jpg?raw=true" alt="4.jpg">

The next two clicks specify the start and end point of the buffered line. Clicks do not have to be on the edge of the object.
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/5.jpg?raw=true" alt="5.jpg">

Next click determines the buffer width based on the line. The buffer follows the buffer - left or right edge of the object. The tolerance parameter, available in the settings, determines the buffer width jump, expressed in map unit.
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/6.jpg?raw=true" alt="6.jpg">

The fourth click completes the buffer edition. The buffer will be cut to existing objects. At this point you can choose the target layer from the context menu.
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/7.jpg?raw=true" alt="7.jpg">
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/8.jpg?raw=true" alt="8.jpg">


### - Fill the empty spaces
The tool enables filling empty spaces between polygon and line objects. You can set the configuration of the boundary layers in the settings. Depending on your choice, they can be polygons or lines, layers visible or not visible in the map window.
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/9.jpg?raw=true" alt="9.jpg">
<img src="https://github.com/abocianowski/Geofabryka-Toolbox-/blob/master/how_to/10.jpg?raw=true" alt="10.jpg">

### - Attributes join by line
AttributesJoinByLine allows you to copy attributes from the source layer to the target layer by using a line.

Points in both layers must be connected with lines. First, the algorithm searches for connected lines for the points of the source layer. If no touching lines were found at this stage, the algorithm will show an error message (along with the possibility of getting closer to the wrong object). Then, if you find a line, you search for objects from the source layer that are crossing on the line. Thanks to the fact, you can get a relationship of many points with data to one without data. If the target layer does not contain any field from the source layer, it will be automatically added. If more than one target has been found for one source point with completed data in the same column, it will be impossible to combine them (an error message will be displayed). The algorithm assumes that each of the three layers will be in the same coordinate system.
<img src="https://github.com/abocianowski/AttributesJoinByLine/blob/master/HowTo_gif/howto.gif?raw=true" alt="howto.gif">
