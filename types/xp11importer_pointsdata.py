import bpy
import mathutils
from mathutils import Vector

from typing import TypeVar, List, Any
from dataclasses import dataclass, field

@dataclass
class PointsData:
   # Triangle data
   verts: List[Vector] = field(default_factory=lambda: [])
   normals: List[Vector] = field(default_factory=lambda: [])
   uvs: List[tuple] = field(default_factory=lambda: [])
   
   # Line Primitives
   line_verts: List[Vector] = field(default_factory=lambda: [])
   line_colors: List[Vector] = field(default_factory=lambda: [])
   
   # Light (deprecated)
   light_verts: List[Vector] = field(default_factory=lambda: [])
   light_colors: List[Vector] = field(default_factory=lambda: [])

   # IDX tables
   index_table: List[int] = field(default_factory=lambda: [])

   def AddVTData(self, line):
      # VT triangle table data
      # VT <x> <y> <z> <nx> <ny> <nz> <uvx> <uvy>
      # Blender flips the z and -y vertices, adjusted accordingly
      # Xplane <x, y, z> => Blender <x, z, -y>
      vals = tuple(map(float, line[1:]))
      if(len(vals) != 8):
         print(f"error: invalid input detected for VT input, expected: [VT <x> <y> <z> <nx> <ny> <nz> <uvx> <uvy>], received: [{line}]")
      self.verts.append(
         Vector( (vals[0], (vals[2] * -1), vals[1]) )
      )
      self.normals.append(
         Vector( (vals[3], (vals[5] * -1), vals[4]) )
      )
      self.uvs.append(
         (vals[6], vals[7])
      )
   
   def AddVLINEData(self, line):
      # VLINE line table data
      # VLINE <x> <y> <z> <r> <g> <b>
      # Blender flips the z and -y vertices, adjusted accordingly
      # Xplane <x, y, z> => Blender <x, z, -y>
      vals = tuple(map(float, line[1:]))
      if(len(vals) != 6):
         print(f"error: invalid input detected, expected: [VLINE <x> <y> <z> <r> <g> <b>], received: [{line}]")
      self.line_verts.append(
         Vector( (vals[0], (vals[2] * -1), vals[1]) )
      )
      self.line_colors.append(
         Vector( (vals[3], (vals[5] * -1), vals[4]) )
      )

   def AddVLIGHTData(self, line): # [deprecated]
      # VLIGHT light table data
      # VLIGHT <x> <y> <z> <r> <g> <b>
      # Blender flips the z and -y vertices, adjusted accordingly
      # Xplane <x, y, z> => Blender <x, z, -y>
      vals = tuple(map(float, line[1:]))
      if(len(line) != 6):
         print(f"error: invalid input detected, expected: [VLIGHT <x> <y> <z> <r> <g> <b>], received: [{line}]")
      self.light_verts.append(
         Vector( (vals[0], (vals[2] * -1), vals[1]) )
      )
      self.light_colors.append(
         Vector( (vals[3], (vals[5] * -1), vals[4]) )
      )
   
   def AddIDXData(self, line):
      # IDX Index table data
      if(len(line) < 1 or len(line) > 11):
         print(f"error: invalid input detected for IDX?? input, expected: [IDX(10) <n> (<n>:9?)], received: [{line}]")
      self.index_table.extend(map(int, line[1:]))
      
   def GetTrisData(self, offset: int, count: int) -> tuple:
      faces = self.index_table[offset:offset+count]
      return tuple( zip(*[iter(faces)]*3) )

_classes = (
   PointsData,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
