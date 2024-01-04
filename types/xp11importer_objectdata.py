import bpy
#import mathutils
from mathutils import Vector

from dataclasses import dataclass, field
from enum import Enum
import logging
import sys
from typing import Any, List

from .types import Attribute
from .xp11importer_keyframe import KeyFrame

#if sys.version_info < (3,11):
#   from typing_extensions import Self
#else:
#   from typing import Self

logger = logging.getLogger(__name__)

class ObjectType(Enum):
   none = 0
   anim = 1
   mesh = 2
   group = 3

@dataclass
class ObjectData:
   attr: List[Attribute] = field(default_factory=list)
   faceData: tuple = None
   objectOrigin: Vector = Vector((0,0,0))
   
   # Reserved objects
   _bl_object: bpy.types.Object = None
   _name: str = ''
   _type: ObjectType = ObjectType.none
   
   # Animation data
   keyFrames: List[KeyFrame] = field(default_factory=list)

   # parenting data
   #parent: Any = None
   children: List[Any] = field(default_factory=list)

   # properties
   @property
   def bl_object(self):
      return self._bl_object

   @bl_object.setter
   def bl_object(self, value: bpy.types.Object):
      self._bl_object = value
      if self._bl_object:
         self._name = self._bl_object.name

   @bl_object.deleter
   def bl_object(self):
      del self._bl_object

   @property
   def name(self) -> str:
      return self._name
   
   @name.setter
   def name(self, value: str):
      self._name = value

   @name.deleter
   def name(self):
      del self._name

   @property
   def type(self):
      return self._type
   
   @type.setter
   def type(self, value: ObjectType):
      self._type = value

   @type.deleter
   def type(self):
      del self._type

   def deslectAllObjects(self):
      if bpy.context.active_object:
         bpy.context.active_object.select_set(False)
      for o in bpy.context.selected_objects:
         o.select_set(False)
         
   def New(self, name: str = '', type: ObjectType = ObjectType.none) -> Any:
      self.name = name
      self.type = type
      return self

      

   # setObjectName
   # attempts to locate a unique name based on the input criteria, if found and an attached
   # object is already associated with this data-structure, set it to the new value, otherwise
   # return the found name for external use
   # returns None if no valid name could be located
   def setObjectName(self,
                     name: str,
                     max_iterations: int = 1000,
                     start_index: int = 0) -> str:
      if self.bl_object and self.bl_object.name == name:
         # associated blender Object already has the requested name
         return name

      if bpy.context.scene.objects.get(name):
         logger.info(f"an object already exists with this name: {name}, iterating...")
         for i in list(range(start_index, (start_index + max_iterations), 1)):
            new_name = f"{name}.{i:003}"
            if bpy.context.scene.objects.get(new_name):
               logger.info(f"new_name: {new_name} exists, continuing search...")
            else:
               logger.info(f"found a unique name: {new_name}")
               if self.bl_object:
                  self.bl_object.name = new_name
                  self.name = new_name
                  return self.name
               else:
                  logger.warn(f"requested to update object name to {new_name} on an object not yet created")
                  return new_name
         logger.warn(f"failed to locate a unique name from the requested range")
         return None
      # no conflicts found, simply return the requested name un-altered
      return name
                  

   # createEmptyObject
   # Creates a new empty for the scene, typcially used for animation constructs
   def createEmptyObject(self,
                         collection: bpy.types.Collection,
                         prepend_collection_name: bool = True,
                         force_create: bool = False,
                         hide_in_viewport: bool = True,
                         display_size: float = 2.0,
                         display_type: str = 'PLAIN_AXES') -> bpy.types.Object:
      logger.info(f"createEmptyObject(collection={collection}, prepend_collection_name={prepend_collection_name}, force_create={force_create},hide_in_viewport={hide_in_viewport}, display_size={display_size}, display_type={display_type})")
      if self.bl_object and force_create:
         logger.warn(f"createEmptyObject(...), requested to replace current object with a new empty")
      elif self.bl_object and not force_create:
         logger.warn(f"existing blender object already associated, set 'force_create=True' to replace the object")
         return self.bl_object
      
      if collection and prepend_collection_name:
         new_name = f"{collection.name}.{self.name}"
      elif prepend_collection_name and not collection:
         raise ValueError("[prepend_collection_name] is set to 'True' and [collection] is not defined, unable to prepend name", collection, prepend_collection_name)
      
      # clear all current selections
      self.deslectAllObjects()

      new_name = self.setObjectName(new_name)
      if not new_name:
         raise ValueError('failed to generate a unique name for new empty object', self)
      obj = bpy.data.objects.new(name=new_name, object_data=None)
      if not obj:
         raise ValueError(f"failed to create a new empty object with name: {new_name}")
      else:
         logger.info(f"created new object: {obj}")
      
      if collection:
         try:
            collection.objects.link(obj)
         except Exception as e:
            logger.error(f"failed to link empty [{obj}] to collection [{collection}]", e)

      try:
         # set the object to the defined origin
         obj.location = self.objectOrigin
         # Adjust axis size, set style and hide the cursor in the viewport display
         obj.empty_display_size = display_size
         obj.empty_display_type = display_type
         if hide_in_viewport:
            obj.hide_set(True)
      except Exception as e:
         raise ValueError('failed to set attributres on new empty object', e)

      logger.info(f"setting self.bl_object => obj {self.bl_object} => {obj}")
      self.bl_object = obj
      return self.bl_object
         
