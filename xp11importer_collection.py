import bpy
import mathutils
from mathutils import Vector

import math
from collections import namedtuple
from dataclasses import dataclass, field
import logging
import pathlib
#from typing import TypeVar, List, Any
from typing import List

# Local imports
from .types.xp11importer_keyframe import *
from .types.xp11importer_objectdata import *
from .types.xp11importer_pointcounts import PointCounts
from .types.xp11importer_pointsdata import PointsData
from .utils import xp11importer_utils as xp11import_utils

logger = logging.getLogger(__name__)


@dataclass
class FinalCounts:
   objects: int = 0
   animated: int = 0
   groups: int = 0

@dataclass
class XplaneImportCollection:
   # required input params
   input_file: str
   shade_smooth: bool = False
   convert_to_quads: bool = False
   face_threshold: float = math.radians(40.0)
   shape_threshold: float = math.radians(40.0)
   
   # detected input file params
   lines: List[str] = field(default_factory=list)
   name: str = ''
   pointCounts: PointCounts = field(default_factory=PointCounts)
   pointsData: PointsData = field(default_factory=PointsData)

   # internal data structures
   _filePath: pathlib.Path = None
   _objectIndex: int = 0
   _finalCounts: FinalCounts = FinalCounts(0,0,0)
   _objectCount: int = 0
   _animatedEmpties: int = 0
   _grpCount: int = 0
   collection: bpy.types.Collection = None
   objects: List[ObjectData] = field(default_factory=list)
   material: bpy.types.Material = None
   material_diffuse_texture: pathlib.Path = None
   material_normal_texture: pathlib.Path = None
   material_lit_texture: pathlib.Path = None
   normal_metalness: bool = False
   blend_glass: bool = False


   def __post_init__(self):
      self._filePath = pathlib.Path(self.input_file)
      self.parseInputFile()
      self.objects = self.createBlenderObjects(self.objects)
      self.objects = self.configureKeyFrames(self.objects)


   def configureCollection(self, name: str = ''):
      if(self.name == ''):
         self.name = name if name else 'xp11importer'

      collName = name if name else self.name
      self.collection = bpy.data.collections.new(collName)
      self.collection.hide_render = True
      bpy.context.scene.collection.children.link(self.collection)
      try:
         self.collection.xplane.layer.name = collName
         self.collection.xplane.is_exportable_collection = True
      except:
         self.collection = None
         logger.exception("failed to detect xplane module, ensure that the XPlane2Blender add-on is enabled")


   def configureKeyFrames(self, objects: List[ObjectData]) -> List[ObjectData]:
      objs: List[ObjectData] = []
      for obj in objects:
         if(len(obj.keyFrames)):
            new_obj = self.createKeyFrames(obj)
            obj = new_obj if new_obj != None else obj
         obj.children = self.configureKeyFrames(obj.children)
         objs.append(obj)
      return objs

         
   def createKeyFrames(self, obj: ObjectData) -> ObjectData:
      curFrame = 1
      dataref = ''
      dataref_index = 0
      if(obj != None and obj.bl_object != None and len(obj.keyFrames)):
         obj.bl_object.select_set(True)
         bpy.context.view_layer.objects.active = obj.bl_object
         bpy.ops.object.mode_set(mode='OBJECT')
         for kf in obj.keyFrames:
            bpy.context.scene.frame_set(curFrame)
            match kf.type:
               case KeyframeType.translation:
                  if(kf.dataref == 'none'):
                     # don't create a keyframe for the 'none' dataref
                     continue
                  obj.bl_object.location = kf.loc
                  obj.bl_object.keyframe_insert(data_path='location', frame=curFrame)

                  curFrame += 2

                  # add the xplane dataref
                  dataref, dataref_index = kf.SetXplaneDataref(
                     obj=obj.bl_object,
                     dataref=dataref,
                     dataref_index=dataref_index,
                  )

               case KeyframeType.rotation:
                  try:
                     obj.bl_object.rotation_euler = mathutils.Euler(kf.GetEulerRotation(), 'XYZ')
                     obj.bl_object.keyframe_insert(data_path='rotation_euler', frame=curFrame)
                     
                     curFrame += 2

                     dataref, dataref_index = kf.SetXplaneDataref(
                        obj=obj.bl_object,
                        dataref=dataref,
                        dataref_index=dataref_index,
                     )

                  except Exception as e:
                     logger.error(f"failed to create rotation keyframe: {kf}", e)
               case KeyframeType.hide:
                  logger.warn(f"TODO: hide kf not supported: {kf}")
               case KeyframeType.show:
                  logger.warn(f"TODO: show kf not supported: {kf}")
               case KeyframeType.loop:
                  obj.bl_object.xplane.datarefs[dataref_index].loop = kf.param
               case _:
                  logger.warn(f"unsupported keyframe type, skipping {kf}")

      # Reset the scene back to the first frame
      xp11import_utils.deselectAllObjects()
      bpy.context.scene.frame_set(1)
      return obj


   
   def linkObjectToCollection(self, obj: bpy.types.Object):
      if(self.collection and obj):
         self.collection.objects.link(obj)

   def createBlenderObjects(self, objects: List[ObjectData]) -> List[ObjectData]:
      objs: List[ObjectData] = []
      for obj in objects:
         bl_obj = self.createBlenderObject(obj)
         if not bl_obj:
            raise ValueError('failed to create blender object', obj)
         if isinstance(bl_obj, ObjectData):
               logger.info(f"received an ObjectData instead of a blender object, {bl_obj}")
         elif isinstance(bl_obj, bpy.types.Object):
               logger.info(f"received a blender object with name {bl_obj.name}")
         else:
               logger.info(f"received an object of type: {type(bl_obj)}")

         obj.bl_object = bl_obj
         #obj.name = obj.bl_object.name
         logger.info(f"{obj.name} has {len(obj.children)} children")
         # Create all child objects
         if len(obj.children):
            logger.info(f"creating child objects for {obj.name}...")
            obj.children = self.createBlenderObjects(obj.children)
            for child in obj.children:
               try:
                  child.bl_object.parent = obj.bl_object
               except Exception as e:
                  logger.error(f"failed to parent {child.name}:{child.name} to {obj.name}:{obj.name}", e)

         objs.append(obj)
      return objs


   def createBlenderObject(self, obj: ObjectData) -> bpy.types.Object:
      if(obj == None):
         logger.error(f"invalid input, obj == None")
         return None
      else:
         match obj.type:
            case ObjectType.anim:
               obj.createEmptyObject(self.collection,display_size=0.5, force_create=True)
               self._finalCounts.animated += 1
               return obj.bl_object
            case ObjectType.group:
               obj.createEmptyObject(self.collection,display_size=0.5, force_create=True)
               self._finalCounts.groups += 1
               return obj.bl_object
            case ObjectType.mesh:
               if(obj.faceData != None):
                  label = obj.setObjectName(f"{self.name}.object.{obj.name}", start_index=self._objectIndex)
                  if not label:
                     raise ValueError("unable to find a unique name for the new mesh object: {obj.name}", obj)
                  logger.info(f"creating new object with label: {label}, expected label: {self.name}.{obj.name}")
                  bl_mesh = bpy.data.meshes.new(f"{label}.mesh")
                  bl_obj = bpy.data.objects.new(label, bl_mesh)
                  bl_obj.location = obj.objectOrigin
                  bl_obj.show_name = False
      
                  logger.info(f"linking {bl_obj} to {self.collection}")
                  self.linkObjectToCollection(bl_obj)
                  logger.info(f"{bl_obj} linked to {self.collection}")
                  self._objectIndex += 1

                  bl_obj.select_set(True)
                  bpy.context.view_layer.objects.active = bl_obj
                  logger.info(f"Creating object from mesh: {label}, faceData len: {len(obj.faceData)}")
                  bl_mesh.from_pydata(self.pointsData.verts, [], obj.faceData)
      
                  vIndex = 0
                  newNorms = []
                  for v in bl_mesh.vertices:
                     newNorms.append(self.pointsData.normals[vIndex])
                     vIndex += 1
                     
                  bl_mesh.normals_split_custom_set_from_vertices(newNorms)
                  bl_mesh.calc_normals_split()
                  bl_mesh.update(calc_edges=True)
      
                  bl_uvl = bl_mesh.uv_layers.new()
                  bl_mesh.uv_layers.active = bl_uvl
      
                  for face in bl_mesh.polygons:
                     for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                        bl_uvl.data[loop_idx].uv = self.pointsData.uvs[vert_idx]
      
                  if(self.material):
                     bl_obj.data.materials.append(self.material)
      
                  for attr in obj.attr:
                     try:
                        bpy.ops.object.add_xplane_object_attribute()
                        bl_obj.xplane.customAttributes[-1].name = attr[0]
                        bl_obj.xplane.customAttributes[-1].value = ' '.join(attr[1:])
                     except Exception as e:
                        logger.error("failed to set x-plane attribute", e)
      
                  try:
                     bpy.ops.object.select_pattern(pattern=bl_obj.name)
                     bpy.ops.object.mode_set(mode='EDIT')
                     bpy.ops.mesh.select_all(action='DESELECT')
                     bpy.ops.mesh.select_mode(type='VERT')
                     bpy.ops.mesh.select_loose()
                     bpy.ops.mesh.delete(type='VERT')
                     
                     bpy.ops.mesh.select_all(action='DESELECT')
                     bpy.ops.mesh.select_mode(type='EDGE')
                     bpy.ops.mesh.select_loose()
                     bpy.ops.mesh.delete(type='EDGE')
      
                     if(self.convert_to_quads):
                        bpy.ops.mesh.select_all(action='SELECT')
                        bpy.ops.mesh.tris_convert_to_quads(
                           face_threshold = self.face_threshold,
                           shape_threshold =self.shape_threshold,
                           uvs = True,
                           vcols = True,
                           seam = True,
                           sharp = True,
                           materials = True,
                        )
      
                     bpy.ops.object.mode_set(mode='OBJECT')

                     if(self.shade_smooth):
                        bpy.ops.object.shade_smooth()
                        logger.info(f"configured object [{bl_obj.name}] for shade-smooth")
                     
                     xp11import_utils.deselectAllObjects()
                  except Exception as e:
                     logger.error("error performing mesh cleanup", e)
      
                  obj.bl_object = bl_obj
                  #obj.name = bl_obj.name
                  self._finalCounts.objects += 1
                  return bl_obj
               else:
                  logger.warn("no faceData found for {obj.name}, skipping import")

         
   def loadImageTexture(self, filePath):
       fp = pathlib.Path(self._filePath.parent, filePath)
       logger.info(f"Attempting to load texture: {str(fp)}")
       try:
           tex = bpy.data.textures.new('Texture', type = 'IMAGE')
           tex.image = bpy.data.images.load(str(fp))
           return tex
       except:
           logger.warn(f"Unable to locate image {fp}, attempting to load a '.dds' version...")
           fp = pathlib.Path(f"{str(pathlib.Path(self._filePath.parent, filePath.stem))}.dds")
           try:
               tex.image = bpy.data.images.load(str(fp))
               return tex
           except:
               logger.warn(f"Unable to locate image file: {fp}")
               return False
   
   def createBaseMaterial(self, name='Material'):
       if(self.material == None):
           self.material = bpy.data.materials.new(name)
           self.material.use_nodes = True

   def createMaterial(self, diffuseTex, name):
       self.createBaseMaterial(name)

       bsdf = self.material.node_tree.nodes["Principled BSDF"]
       texImage = self.material.node_tree.nodes.new('ShaderNodeTexImage')
       texImage.name = f"Diffuse Texture"
       texImage.location = -350,350
       texImage.image = diffuseTex.image
       self.material.node_tree.links.new(bsdf.inputs['Base Color'], texImage.outputs['Color'])

   def createNormalMap(self, normalTex):
       self.createBaseMaterial()
           
       nrmImage = self.material.node_tree.nodes.new('ShaderNodeTexImage')
       nrmImage.location = -650, -50
       nrmImage.image = normalTex.image
       nrmImage.image.colorspace_settings.name = 'Non-Color'
       normalNode = self.material.node_tree.nodes.new('ShaderNodeNormalMap')
       normalNode.name = f"Normal Texture"
       if(self.normal_metalness):
           normalNode.inputs.get("Strength").default_value = 0.0
       normalNode.location = -300, -50
       normalNode.space = 'BLENDER_OBJECT'
           
       self.material.node_tree.links.new(normalNode.inputs['Color'], nrmImage.outputs['Color'])
       bsdf = self.material.node_tree.nodes["Principled BSDF"]
       self.material.node_tree.links.new(bsdf.inputs['Normal'], normalNode.outputs['Normal'])

   def createEmissionShader(self, litTexture):
       self.createBaseMaterial()
       litImage = self.material.node_tree.nodes.new('ShaderNodeTexImage')
       litImage.location = -650, -350
       litImage.image = litTexture.image
       EmissionNode = self.material.node_tree.nodes.new('ShaderNodeEmission')
       EmissionNode.name = f"Emission Texture"
       EmissionNode.location = -300, -350
       self.material.node_tree.links.new(EmissionNode.inputs['Color'], litImage.outputs['Color'])
       bsdf = self.material.node_tree.nodes["Principled BSDF"]
       mixShader = self.material.node_tree.nodes.new('ShaderNodeMixShader')
       mixShader.location = 300, -200
       mixShader.inputs[0].default_value = 0.0
       
       materialOutput = self.material.node_tree.nodes['Material Output']
       materialOutput.location = 500, 150
       self.material.node_tree.links.new(mixShader.inputs[2], EmissionNode.outputs['Emission'])
       self.material.node_tree.links.new(materialOutput.inputs['Surface'], mixShader.outputs['Shader'])
       self.material.node_tree.links.new(mixShader.inputs[1], bsdf.outputs['BSDF'])

   def setCollectionParameter(self, param, value):
       try:
          self.collection.xplane.layer[param] = value
          return True
       except:
           logger.warn(f"failed to set collection param [{param}] to value [{value}]")
           return False
         
   @xp11import_utils.defer
   def parseInputFile(self, defer):
      currentObject: ObjectData = None
      grpObject: ObjectData = None
      animStack = []
      label = ''
      if(self._filePath and self._filePath.is_file()):
         try:
            f = open(self._filePath,
                     mode='r',
                     encoding='utf-8',
                     errors='ignore')
            defer(lambda: f.close())
            self.lines = f.readlines()
            self.name = self._filePath.stem
         except Exception as e:
            raise ValueError('failed to read input file', e)
      else:
         raise ValueError('failed to read input file', self._filePath)
      
      logger.info(f"file_stem: {self._filePath.stem}, colName: {self.name}")
      self.configureCollection()

      for lineStr in self.lines:
         line = lineStr.split()
         if(len(line) == 0):
            continue
         match line[0]:
            case 'TEXTURE':
               self.material_diffuse_texture = pathlib.Path(line[1])
               textureFile = self.material_diffuse_texture
               texture = self.loadImageTexture(textureFile)
               if(texture):
                  self.createMaterial(texture, textureFile.stem)
                  self.setCollectionParameter('texture', textureFile.name)

            case 'TEXTURE_NORMAL':
               self.material_normal_texture = pathlib.Path(line[1])
               textureFile = self.material_normal_texture
               texture = self.loadImageTexture(textureFile)
               if(texture):
                  self.createNormalMap(texture)
                  self.setCollectionParameter('texture_normal', textureFile.name)

            case 'TEXTURE_LIT':
               self.material_lit_texture = pathlib.Path(line[1])
               textureFile = self.material_lit_texture
               texture = self.loadImageTexture(textureFile)
               if(texture):
                  self.createEmissionShader(texture)
                  self.setCollectionParameter('texture_lit', textureFile.name)

            case 'NORMAL_METALNESS':
               self.normal_metalness = True
               if(self.material != None and self.material_normal_texture != None):
                  nodes = self.material.node_tree.nodes
                  normalNode = nodes.get("Normal Texture")
                  if(normalNode):
                     normalNode.inputs.get("Strength").default_value = 0.0
               self.setCollectionParameter('normal_metalness', True)

            case 'BLEND_GLASS':
               self.blend_glass = True
               self.setCollectionParameter('blend_glass', True)

            case 'GLOBAL_specular':
               val = line[1]
               if(val != '1.0'):
                  logger.warn(f"NOTE: GLOBAL_specular detected [{val}], new versions of XPlane2Blender will override this to [1.0]")
            
            case 'POINT_COUNTS':
               self.pointCounts.fromLine(line)
            
            case '#':
               # capture object names
               label = line[1]
               logger.info(f"LABEL: {label}")

            case '####_group':
               # capture a group object
               if grpObject:
                  # a grouping has already been created, this line marks the beginning of a new group
                  # close the previous group, append to the objects collection and begin a new one
                  self.objects.append(grpObject)
                  logger.info(f"Closing previous group: [{grpObject.name}]")

               grpObject = ObjectData().New(name=f"group.{' '.join(line[1:])}", type=ObjectType.group)
               logger.info(f"New group created [group.{' '.join(line[1:])}]")

            case 'VT':
               self.pointsData.AddVTData(line)

            case 'VLINE':
               self.pointsData.AddVLINEData(line)

            case 'VLIGHT':
               self.pointsData.AddVLIGHTData(line)

            case str(x) if x.startswith('IDX'):
               self.pointsData.AddIDXData(line)

            case str(x) if x.startswith('ATTR_'):
               if(currentObject == None):
                  currentObject = ObjectData()
               currentObject.attr.append([line[0]])

            case 'TRIS': # Create a new mesh object
               if(currentObject == None):
                  currentObject = ObjectData()
               faceData = self.pointsData.GetTrisData(
                  offset=int(line[1]),
                  count=int(line[2])
               )
               match currentObject.type:
                  case ObjectType.none:
                     # create a standalone mesh object
                     currentObject.type = ObjectType.mesh
                     currentObject.name = f"object"
                     if label != '':
                        currentObject.name += f".{label}"
                     currentObject.faceData = faceData
                     if grpObject:
                        grpObject.children.append(currentObject)
                     else:
                        self.objects.append(currentObject)
                     currentObject = ObjectData()
                  case ObjectType.anim:
                     childObject = ObjectData()
                     childObject.type = ObjectType.mesh
                     childObject.name = f"object.{len(currentObject.children):003}"
                     if label != '':
                        childObject.name += f".{label}"
                     childObject.faceData = faceData
                     childObject.attr = currentObject.attr[:]
                     currentObject.children.append(childObject)
                  case _:
                     logger.warn(f"Unsupported type to the TRIS call: {currentObject.type}")
               
               # reset the label if it was defined
               logger.info(f"TRIS, Group: [{grpObject.name if grpObject else 'None'}], ObjectType: [{currentObject.type}], name: {currentObject.name}, label: {label}")
               label = ''
               
            case 'ANIM_begin':
               if(currentObject == None):
                  currentObject = ObjectData()
               match currentObject.type:
                  case ObjectType.none:
                     # repurpose the currentObject as an animation block
                     currentObject.type = ObjectType.anim
                     currentObject.name = f"anim"
                     if label != '':
                        currentObject.name += f".{label}"

                  case ObjectType.anim:
                     # currentObject is still a root level object, and alredy configured for
                     # an animation sequence, add a child animation object
                     # 1. push the currentObject onto the animStack
                     # 2. replace the currentObject with a new instance
                     # 3. configure it for animation
                     childObject = ObjectData()
                     childObject.attr = currentObject.attr[:]
                     animStack.append(currentObject)
                     currentObject = childObject
                     currentObject.name = f"anim.{len(animStack):003}"
                     if label != '':
                        currentObject.name += f".{label}"
                     currentObject.type = ObjectType.anim

                  case _:
                     # no action
                     logger.info(f"ANIM_begin UNDEFINED TYPE: currentObject: {currentObject}")
                     continue

               # reset the label if it was defined
               logger.info(f"ANIM_begin, ObjectType: [{currentObject.type}], name: {currentObject.name}, label: {label}")
               label = ''

            case 'ANIM_trans':
               vals = tuple(map(float,line[1:7]))
               loc1 = Vector((
                  vals[0],
                  (vals[2] * -1),
                  vals[1],
               ))
               loc2 = Vector((
                  vals[3],
                  (vals[5] * -1),
                  vals[4],
               ))
               match len(line):
                  case 7: # position only KF
                     kf = KeyFrame(loc=loc1)
                     currentObject.keyFrames.append(kf)
                  case 10: # has a dataref
                     params = tuple(map(float, line[7:9]))
                     dataref = line[9]
                     kf_1 = KeyFrame(type=KeyframeType.translation, loc=loc1, param=params[0], dataref=dataref)
                     kf_2 = KeyFrame(type=KeyframeType.translation, loc=loc2, param=params[1], dataref=dataref)
                     currentObject.keyFrames.extend([kf_1, kf_2])
            
            case 'ANIM_rotate':
               if(len(line) != 9):
                  logger.warn(f"invalid input detected for ANIM_rotate, expected 8 inputs, received {line}")
                  continue
               vals = tuple(map(float, line[1:8]))
               axis = Vector((
                  vals[0],
                  (vals[2] * -1),
                  vals[1],
               ))
               angle1 = vals[3]
               angle2 = vals[4]
               param1 = vals[5]
               param2 = vals[6]
               dataref = line[8]
               kf_1 = KeyFrame(type=KeyframeType.rotation, axis=axis, angle=angle1, param=param1, dataref=dataref)
               kf_2 = KeyFrame(type=KeyframeType.rotation, axis=axis, angle=angle2, param=param2, dataref=dataref)
               currentObject.keyFrames.extend([kf_1, kf_2])

            case 'ANIM_end':
               if(len(animStack) > 0):
                  # this is a child object
                  parentObject: ObjectData = animStack.pop(-1)
                  if(currentObject.type != ObjectType.none):
                     # object has data supplied, add this as a child to the parent
                     parentObject.children.append(currentObject)
                  logger.info(f"ANIM_end, Animated, Group: [{grpObject.name if grpObject else 'None'}] ObjectType: [{currentObject.type}], name: {currentObject.name}, label: {label}")
                  currentObject = parentObject
               else:
                  # This was a root level anim object, add it to the collection and create a new root object
                  if grpObject:
                     grpObject.children.append(currentObject)
                  else:
                     self.objects.append(currentObject)

                  logger.info(f"ANIM_end, Animated, Group: [{grpObject.name if grpObject else 'None'}] ObjectType: [{currentObject.type}], name: {currentObject.name}, label: {label}")
                  currentObject = ObjectData().New(type=ObjectType.none)

                  
            case _:
               # default case, unsupported operation, skip line and continue
               continue


_classes = (
   XplaneImportCollection,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
   