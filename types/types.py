##import bpy
##import mathutils
##from mathutils import Vector
#
##import math
#
##from enum import Enum
from dataclasses import dataclass
#from collections import namedtuple
from typing import Any
#
#HeaderFormat = namedtuple('HeaderFormat', 'line_endings version type')
#
## OBJ Format
#@dataclass
#class ObjectFile():
#    _header: HeaderFormat = HeaderFormat()
#    version: int
#
#
# Attribute format
@dataclass
class Attribute():
    
    command: str = ''
    params: (Any) = ()
    
