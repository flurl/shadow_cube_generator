import os
import sys
import Mesh
import Part
import MeshPart
from BOPTools import BOPFeatures
from PySide2 import QtWidgets

def intersect_stl_files(mesh_files, output_step_file, tolerance=0.1):
    """
    Import multiple mesh files, convert them to solids, and create their intersection
    using BOPTools
    Args:
      mesh_files: List of paths to mesh files
      tolerance: Tolerance for the surface creation (default=0.1)
    Returns:
      The intersection solid object
    """
    solid_objects = []  # Store document objects instead of just shapes

    # Import and convert each mesh
    for i, mesh_file in enumerate(mesh_files):
        # Get base name without extension
        base_name = os.path.splitext(os.path.basename(mesh_file))[0]
        
        # Import mesh
        Mesh.insert(mesh_file, "Document")
        
        # Convert to shape
        mesh_obj = FreeCAD.ActiveDocument.getObject(base_name)
        if not mesh_obj:
            raise ValueError(f"Failed to import mesh: {mesh_file}")
        
        shape = Part.Shape()
        shape.makeShapeFromMesh(mesh_obj.Mesh.Topology, tolerance)
        
        # Create shell and solid
        shells = shape.Shells
        if not shells:
            raise ValueError(f"No valid shells created from mesh: {mesh_file}")
        
        shell = shells[0]
        if shell.Orientation == "Reverse":
            shell.reverse()
            
        try:
            solid = Part.makeSolid(shell)
            
            # Create intermediate solid object for visualization
            solid_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", f"{base_name}_solid")
            solid_obj.Shape = solid
            solid_objects.append(solid_obj)  # Store the document object
            
        except Exception as e:
            raise ValueError(f"Could not create valid solid from: {mesh_file}. Error: {str(e)}")

    # Calculate intersection of all solids
    if len(solid_objects) < 2:
        raise ValueError("Need at least 2 solids for intersection")

    try:
        # Create intersection object using Part Common
        result = solid_objects[0].Shape
        for obj in solid_objects[1:]:
            result = result.common(obj.Shape)
            
        # Create final intersection object
        intersection_obj = FreeCAD.ActiveDocument.addObject("Part::Feature", "Intersection")
        intersection_obj.Shape = result
        
        # Recompute document
        FreeCAD.ActiveDocument.recompute()
        
        # Export the intersection as STEP file
        result.exportStep(output_step_file)
        
        # Return success message
        return f"Intersection saved successfully to {output_step_file}"
        
    except Exception as e:
        raise ValueError(f"Failed to create intersection: {str(e)}")



output_step_file = sys.argv[2]
mesh_files = sys.argv[3:]

intersect_stl_files(mesh_files, output_step_file)

#QtWidgets.QApplication.instance().quit()
