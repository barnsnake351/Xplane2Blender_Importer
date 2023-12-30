# Standalone functional helpers

import bpy
import pathlib
from typing import TypeVar, List

from ..types.xp11importer_objectdata import ObjectData

# Implement go-like defer - full credit and source: https://towerbabbel.com/go-defer-in-python/
from functools import wraps
def defer(func):
   @wraps(func)
   def func_wrapper(*args, **kwargs):
      deferred = []
      defer = lambda f: deferred.append(f)
      try:
         return func(*args, defer=defer, **kwargs)
      finally:
         deferred.reverse()
         for f in deferred:
            f()
   return func_wrapper

def stub_filePath(file_name="objects/T38_cockpit.obj"):
   base_dir = pathlib.Path(pathlib.Path.home(),'OneDrive','Blender','Projects','X-Plane','Aircraft','Northrop T-38')
   return pathlib.Path(base_dir, file_name)

# This doesn't work, tweak or remove
T = TypeVar('T')
def listToVertex(itemType: T, input: List[str]) -> tuple:
   # Blender swaps the y,z params in the traditional input and inverts y
   # this function will input a standard coordinate and return a blender compatible version
   # ['x','y','z'] => (T(x), T(z), T(-y))
   vals = tuple(map(T,input[1:]))
   if(len(vals) != 3):
      print(f"error: invalid input detected to 'listToVertex', expected ['x','y','z'], received [{input}]")
   return (vals[0], (vals[2] * -1), vals[1])
# end testing

def read_all_lines(fp: pathlib.Path):
   lines = []
   if(fp and fp.is_file()):
      try:
         f = open(fp, 'r')
         lines = f.readlines()
      finally:
         f.close()
   return lines      

def printObject(obj: ObjectData, padding: int = 0):
   pad = ' ' * padding
   print(f"{pad}OB: label: {obj.label}, attr: {obj.attr}, type: {obj.objectType}, faces: {len(obj.faceData) if obj.faceData != None else 'None'}, children: {len(obj.children) if len(obj.children) > 0 else 'None'}")
   for x in obj.keyFrames:
      print(f"{pad}  KF: {x}")
   if(len(obj.children) > -1):
      for child in obj.children:
         printObject(child, padding=padding+3)

def deselectAllObjects():
   bpy.context.active_object.select_set(False)
   for o in bpy.context.selected_objects:
      o.select_set(False)
   

def hideObjectFromView(obj: bpy.types.Object):
   if(obj != None):
      # deselect all other objects
      deselectAllObjects()
      obj.select_set(True)

      # hide the provided object
      bpy.context.active_object.hide_set(True)
      bpy.context.active_object.select_set(False)

      # deselct this object
      deselectAllObjects()
