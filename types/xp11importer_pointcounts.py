import bpy

from typing import TypeVar, List, Any
from dataclasses import dataclass, field

@dataclass(order=True)
class PointCounts:
   tris: int = 0
   lines: int = 0
   lites: int = 0
   indices: int = 0

   def fromLine(self, line: List[str]):
      if(len(line) != 5):
         print(f"error: bad inputs detected for 'POINT_COUNTS', expected 'POINT_COUNTS <tris> <lines> <lites> <indices>', received [{line}]")
      # TODO: Figure out why this happens
      # convert line to tuple as int(line[x]) returns a tuple (val(x),) which screws things up down the road
      vals = tuple(map(int, line[1:]))
      self.tris=vals[0]
      self.lines=vals[1]
      self.lites=vals[2]
      self.indices=vals[3]

_classes = (
   PointCounts,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
 