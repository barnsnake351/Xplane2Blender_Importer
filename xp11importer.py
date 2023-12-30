# Blender imports
import bpy
#import bmesh
#import mathutils
#from mathutils import Vector, Euler

#import copy
import math
#import itertools
#import os

# Local imports
from .xp11importer_collection import XplaneImportCollection
from .types import *


class pluginDefaults():
   # shadeSmooth
   shadeSmooth: bool = True
   
   # TRIS -> Quads
   trisToQuads: bool = False
   faceThreshold: float = math.radians(40)
   shapeThreshold: float = math.radians(40)


class XPlane11Importer(bpy.types.Operator):
   bl_label = "Import X-Plane (.obj)"    
   bl_idname = "import.xplane_obj"

   importCollection: XplaneImportCollection = None

   filepath: bpy.props.StringProperty(subtype="FILE_PATH")

   shadeSmooth: bpy.props.BoolProperty(
      name = "Shade Smooth",
      default = pluginDefaults.shadeSmooth
   )

   convertTrisToQuads: bpy.props.BoolProperty(
      name = "TRIS -> Quads",
      default = pluginDefaults.trisToQuads
   )

   faceThreshold: bpy.props.FloatProperty(
      name = "Face Threshold",
      default = pluginDefaults.faceThreshold,
      description = "Max Face Angle to use for the TRIS -> Quad conversion",
      min = 0.0,
      max = math.pi,
      subtype = 'ANGLE'
   )

   shapeThreshold: bpy.props.FloatProperty(
      name = "Shape Threshold",
      default = pluginDefaults.shapeThreshold,
      description = "Max Shape Angle to use for the TRIS -> Quad conversion",
      min = 0.0,
      max = math.pi,
      subtype = 'ANGLE'

   )

   def execute(self, context):
      print(f"execute x-plane (.obj) import for: {self.filepath}")
      print(f"convert-to-quads: {self.convertTrisToQuads}, faceThreshold: {self.faceThreshold}, shapeThreshold: {self.shapeThreshold}")
      try:
         self.importCollection = XplaneImportCollection(
            input_file=self.filepath,
            shade_smooth=self.shadeSmooth,
            convert_to_quads=self.convertTrisToQuads,
            face_threshold=self.faceThreshold,
            shape_threshold=self.shapeThreshold)
      except Exception as e:
         print(f"[error] Failed to import collection from [{self.filepath}]: {e}")
         return {"CANCELLED"}

      if(self.importCollection != None and len(self.importCollection.objects) > 0):
         print(f"Imported {self.importCollection._finalCounts}")
      else:
         print(f"Unhandled error occured, no objects imported")
         return {"CANCELLED"}

      return {"FINISHED"}

   def invoke(self, context, event):
      context.window_manager.fileselect_add(self)
      return {"RUNNING_MODAL"}

_classes = (
   XPlane11Importer,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
