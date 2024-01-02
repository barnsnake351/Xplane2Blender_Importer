#import bpy
#import mathutils
#
#from collections import namedtuple
#from dataclasses import dataclass
#
##Tris = namedtuple('Tris', 'offset count')
#Lines = namedtuple('Lines', 'offset count')
#Lights = namedtuple('Lights', 'offset count')
#LightNamed = namedtuple('LightNamed', 'name x y z')
#LightCustom = namedtuple('LightCustom', 'x y z r g b a s s1 t1 s2 t2 dataref')
#LightParam = namedtuple('LightParam', 'name x y z additional_params')
#LightSpillCustom = namedtuple('LightSpillCustom', 'x y z r g b a s dx dy dz semi dref')
#Magnet = namedtuple('Magnet', 'name type x y z psi the phi')
#Emitter = namedtuple('Emitter', 'name x y z psi index')
#
#@dataclass
#class GeometryPoints():
#    offset: int
#    count: int
#
#
#@dataclass
#class GeometryCommands():
#    Tris: GeometryPoints = None
#    Lights: GeometryPoints = None
#
#    # internal
#    _lines: GeometryPoints = None
#    
#    @property
#    def Lines(self):
#        return self._lines
#    
#    @Lines.setter
#    def Lines(self, offset: int, count: int):
#        if count % 2 != 0:
#            raise ValueError('invalid value for Lines, <count> must be a multiple of 2')
#        self._lines = GeometryPoints(offset=offset, count=count)
#
#    @Lines.deleter
#    def Lines(self):
#        del self._lines