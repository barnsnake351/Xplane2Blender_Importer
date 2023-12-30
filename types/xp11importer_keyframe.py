import bpy
import mathutils
from mathutils import Vector

from dataclasses import dataclass
from enum import Enum
import math

class KeyframeType(Enum):
   none = 0
   translation = 1
   rotation = 2
   hide = 3
   show = 4
   loop = 5

@dataclass
class KeyFrame:
   loc: Vector = Vector((0,0,0))
   axis: Vector = Vector((0,0,0))
   angle: float = 0.0
   param: float = 0.0
   dataref: str = 'none'
   type: KeyframeType = KeyframeType.none

   def GetEulerRotation(self):
      rad = math.radians(self.angle)
      return Vector((
         (self.axis[0] * rad),
         (self.axis[1] * rad),
         (self.axis[2] * rad),
      ))

   def SetXplaneDataref(self, obj: bpy.types.Object, dataref: str, dataref_index: int) -> (str, int):
      # add the xplane dataref
      if(obj):
         try:
            if(dataref != self.dataref):
               dataref = self.dataref
               # add only once as long as the dataref doesn't change
               obj.xplane.datarefs.add()
               dataref_index = len(obj.xplane.datarefs) -1
               obj.xplane.datarefs[dataref_index].path = dataref
   
            # set the dataref value
            obj.xplane.datarefs[dataref_index].value = self.param
            # add the xplane dataref keyframe
            bpy.ops.object.add_xplane_dataref_keyframe(index=dataref_index)
         except Exception as e:
            print(f"failed to set the xplane dataref for kf: {self}", e)

      return dataref, dataref_index
         

_classes = (
   KeyFrame,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
