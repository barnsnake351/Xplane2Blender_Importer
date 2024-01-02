import bpy
import mathutils
from mathutils import Vector

from collections import namedtuple
import copy
from dataclasses import dataclass, field
import logging
import math
import pathlib
from typing import List

# Local imports
from .types.types import Attribute
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
   _global_ATTR_LOD = None
   _firstCommand: bool = True
   _package_name: str = 'xp11importer'
   
   # View Layers
   _viewLayer: bpy.types.ViewLayer = None
   _packageViewLayer: bpy.types.ViewLayer = None

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


   def configureGroupCollection(self, name: str = '') -> bpy.types.Collection:
      coll: bpy.types.Collection = None
      if bpy.data.collections.get(name):
         # existing collection with this name already found, iterate the name to find a unique value
         for i in range(0,100):
            name = f"{name}.{i:003}"
            if bpy.data.collections.get(name):
               continue
            else:
               coll = bpy.data.collections.new(name)
      else:
         coll = bpy.data.collections.new(name)

      if not name:
         raise ValueError('failed to create sub-group collection', name)
      self.collection.children.link(coll)
      self.update_view_layer_visibility()
      return coll

   def configureCollection(self, name: str = ''):
      if(self.name == ''):
         self.name = name if name else self._package_name

      collName = name if name else self.name
      self.collection = bpy.data.collections.new(collName)
      self.collection.hide_render = True
      bpy.context.scene.collection.children.link(self.collection)
      self.update_view_layer_visibility()
      try:
         self.collection.xplane.layer.name = collName
         self.collection.xplane.is_exportable_collection = True
      except:
         self.collection = None
         logger.exception("failed to detect xplane module, ensure that the XPlane2Blender add-on is enabled")


   # create_view_layers
   # Create a new layer for the object collection imported
   # Create an additional top-level ViewLayer to capture all new objects, name this after the package
   # and all the end-user to change later
   # TODO: add a preference option to override this behavior (use-view-layers, collection name)
   # in the add-on configuration settings
   def create_view_layers(self):
      # Create the shared view layer that all imported objects from this library will use, default
      # this to the package name for simplicity
      if not self._viewLayer:
         # set the local viewLayer to the starting point of this import, retain this throughout
         self._viewLayer = bpy.context.view_layer
      if not bpy.context.scene.view_layers.get(self._package_name):
         try:
            vl = bpy.context.scene.view_layers.new(self._package_name)
            if not vl:
               raise ValueError('failed to create new view layer, received an empty object')
         except Exception as e:
            raise ValueError('failed to create combined view layer', e)
         
      if not bpy.context.scene.view_layers.get(self.name):
         try:
            vl = bpy.context.scene.view_layers.new(self.name)
            if not vl:
               raise ValueError('failed to create object view layer, received an empty object')
         except Exception as e:
            raise ValueError('failed to create object view layer', e)

      # reset the view_layer back to the starting point
      bpy.context.window.view_layer = self._viewLayer

    
   # update_view_layer_visibility
   # pulls the list of associated collections with this object and then
   # sets the collection visibility for the active_layer, xpl1importer, and the
   # discovered collection name the imported collections will be excluded from
   # all remaining view_layers
   # TODO: future update to expose this feature as a boolean operation in the
   # addon preferences
   def update_view_layer_visibility(self):
      if not self._viewLayer:
         self.create_view_layers()

      active_layer = bpy.context.view_layer
      collection_layers = [active_layer.name, self.name, self._package_name]
      collection_names = list(map(lambda c: c.name, bpy.data.collections[self.collection.name].children[:]))
      collection_names.extend([self.collection.name, self._package_name, active_layer.name])
      for layer in bpy.context.scene.view_layers:
         if layer.name in collection_layers:
            for coll in layer.layer_collection.children:
               if layer.name in [active_layer.name,self._package_name]:
                  coll.exclude = False
               elif coll.name in collection_names:
                  coll.exclude = False
               else:
                  coll.exclude = True
         else:
            for coll in layer.layer_collection.children:
               if coll.name in collection_names:
                  coll.exclude = True
               

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


   
   def linkObjectToCollection(self, obj: bpy.types.Object, collection: bpy.types.Collection = None):
      if not collection:
         collection = self.collection
      if collection and obj:
         collection.objects.link(obj)

   def createBlenderObjects(self, objects: List[ObjectData], collection: bpy.types.Collection = None) -> List[ObjectData]:
      objs: List[ObjectData] = []
      if not collection:
         collection = self.collection
      for obj in objects:
         bl_obj = self.createBlenderObject(obj, collection)
         if not bl_obj:
            raise ValueError('failed to create blender object', obj)
         if isinstance(bl_obj, ObjectData):
               logger.info(f"received an ObjectData instead of a blender object, {bl_obj}")
         elif isinstance(bl_obj, bpy.types.Object):
               logger.info(f"received a blender object with name {bl_obj.name}")
         else:
               logger.info(f"received an object of type: {type(bl_obj)}")

         if isinstance(bl_obj, bpy.types.Collection):
            collection = bl_obj
         elif isinstance(bl_obj, bpy.types.Object):
            obj.bl_object = bl_obj
         else:
            logger.warn(f"unsupported return type to createBlenderObject: {type(bl_obj)}")

         # Create all child objects
         if len(obj.children):
            logger.info(f"{obj.name} has {len(obj.children)} children")
            logger.info(f"creating child objects for {obj.name}...")
            obj.children = self.createBlenderObjects(obj.children, collection)
            for child in obj.children:
               try:
                  if obj.type != ObjectType.group:
                     child.bl_object.parent = obj.bl_object
               except Exception as e:
                  logger.error(f"failed to parent {child.name}:{child.name} to {obj.name}:{obj.name}", e)

         objs.append(obj)
      return objs


   def createBlenderObject(self, obj: ObjectData, coll: bpy.types.Collection = None) -> Any:
      if not coll:
         coll = self.collection
      if(obj == None):
         logger.error(f"invalid input, obj == None")
         return None
      else:
         match obj.type:
            case ObjectType.anim:
               obj.createEmptyObject(coll,display_size=0.5, force_create=True)
               self._finalCounts.animated += 1
               return obj.bl_object
            case ObjectType.group:
               self._finalCounts.groups += 1
               return self.configureGroupCollection(obj.name)
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
      
                  logger.info(f"linking {bl_obj} to {coll}")
                  self.linkObjectToCollection(bl_obj, coll)
                  logger.info(f"{bl_obj} linked to {coll}")
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
                        bl_obj.xplane.customAttributes[-1].name = attr.command
                        bl_obj.xplane.customAttributes[-1].value = ' '.join(attr.params)
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

         
   def loadImageTexture(self, filePath) -> bpy.types.Image:
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
               return None
   
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
      
      self.configureCollection()

      for lineStr in self.lines:
         line = lineStr.split()
         if(len(line) == 0):
            continue
         match line[0]:
            case str(x) if x.startswith('TEXTURE'):
               texFile = pathlib.Path(line[1])
               texture = self.loadImageTexture(texFile)
               if not texture:
                  logger.warn(f"failed to load texture image, make sure it is available, skipping import", line[1])
                  continue
               match line[0]:
                  case 'TEXTURE':
                     self.createMaterial(texture, texFile.stem)
                     self.setCollectionParameter('texture', texFile.name)
                     pass
                  case 'TEXTURE_NORMAL':
                     self.createNormalMap(texture)
                     self.setCollectionParameter('texture_normal', texFile.name)
                     self.material_normal_texture = texFile
                     pass
                  case 'TEXTURE_LIT':
                     self.createEmissionShader(texture)
                     self.setCollectionParameter('texture_lit', texFile.name)
                     pass
                  case _:
                     logger.warn(f"unsupported texture argument", line)

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

               grpObject = ObjectData().New(name=f"{self.name}.{' '.join(line[1:])}", type=ObjectType.group)
               logger.info(f"New group created [{self.name}.{' '.join(line[1:])}]")

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
               match line[0]:
                  case 'ATTR_LOD':
                     # ATTR_LOD <near:int> <far:int>
                     # If and ATTR_LOD is the first command record (after data-tables), it must be the only
                     # definition in the file
                     if len(line) != 3:
                        logger.error(f"{line[0]} ignored, invalid element found, expected: {line[0]} <near> <far>, received: {line}")
                        continue
                     if line[1] == line[2]:
                        logger.error(f"{line[0]} ignored, invalid format for LOD, <near> and <far> must be different:", line)
                        continue
                     if self._firstCommand:
                        if int(line[1]) != 0:
                           raise ValueError('the near value of the first/only LOD must be 0', line)
                        try:
                           if self.collection.xplane.layer.lods == '0':
                              self.collection.xplane.layer.lod.add()
                              self.collection.xplane.layer.lod[0].near = int(line[1])
                              self.collection.xplane.layer.lod[0].far = int(line[2])
                              self.collection.xplane.layer.lods = '1'

                        except Exception as e:
                           raise ValueError('failed to set global LOD:', e)
                     elif not self._firstCommand and self._global_ATTR_LOD != None:
                        # Invalid definition, if global ATTR_LOD is defined, then there can be no
                        # other references, the import will work, however Xplane will not be able
                        # load the object definition as XPlane2Blender will augment without checking
                        logger.error(f"{line[0]} ignored, {line[0]} was defined as the global (first command sequence), additional entries will cause errors")
                        continue
                     else:
                        currentObject.attr.append(Attribute(line[0], (line[1],line[2])))
                  case 'ATTR_shiny_rat':
                     if len(line) != 2:
                        logger.error(f"{line[0]} ignore, invalid element found, expected: {line[0]} <ratio>, received: {line}")
                        continue
                     currentObject.attr.append(Attribute(line[0], (line[1],)))
                  case 'ATTR_reset':
                     currentObject.attr.append(Attribute(line[0]))
                  case 'ATTR_poly_on':
                     if len(line) != 2:
                        logger.error(f"{line[0]} ignored, invalid element found, expected: {line[0]} <n>, received: {line}")
                        continue
                     currentObject.attr.append(Attribute(line[0], (line[1],)))
                  case 'ATTR_cockpit_region':
                     if len(line) != 2:
                        logger.error(f"{line[0]} ignored, invalid element found, expected: {line[0]} <region number>, received: {line}")
                        continue
                     currentObject.attr.append(Attribute(line[0], (line[1],)))
                  case 'ATTR_cockpit_device':
                     if len(line) != 5:
                        logger.error(f"{line[0]} ignored, invalid element found, expected: {line[0]} <name> <bus> <lighting channel> <auto_adjust>, received: {line}")
                        continue
                     currentObject.attr.append(Attribute(line[0], (line[1], line[2], line[3], line[4])))
                  case 'ATTR_shadow_blend <ratio>':
                     if len(line) != 2:
                        logger.error(f"{line[0]} ignored, invalid element found, expected: {line[0]} <region number>, received: {line}")
                        continue
                     currentObject.attr.append(Attribute(line[0], (line[1],)))
                  case 'ATTR_no_blend':
                     if len(line) > 1:
                        # can take an optional ratio between 0.0 and 1.0 that specifies the cutoff
                        # alpha channel. Version: 850+
                        currentObject.attr.append(Attribute(line[0], (line[1],)))
                     else:
                        currentObject.attr.append(Attribute(line[0]))
                  case 'ATTR_hard':
                     if len(line) > 1:
                        # an optional surface anem can be supplied. Version 850+
                        # valid names: water, concrete, asphalt, grass, dirt, gravel, lakebed, snow, shoulder, blastpad
                        currentObject.attr.append(Attribute(line[0], (line[1],)))
                     else:
                        currentObject.attr.append(Attribute(line[0]))
                     
                  case _:
                     # Attribute ID                Version available
                     # ATTR_cockpit
                     # ATTR_cockpit_lit_only
                     # ATTR_light_level_reset
                     # ATTR_draped
                     # ATTR_no_draped
                     # ATTR_shadow                 1010
                     # ATTR_shadow_blend           1000
                     # ATTR_no_shadow              1010
                     # ATTR_hard
                     # ATTR_hard_deck              900
                     # ATTR_no_hard
                     # ATTR_shade_flat
                     # ATTR_shade_smooth
                     # ATTR_depth
                     # ATTR_no_depth
                     # ATTR_no_cull
                     # ATTR_cull
                     # ATTR_blend
                     # ATTR_no_blend
                     # ATTR_solid_camera           930
                     # ATTR_no_solid_camera        930
                     # ATTR_draw_enable            930
                     # ATTR_draw_disable           930
                     currentObject.attr.append(Attribute(line[0]))
               self._firstCommand = False

            case 'TRIS': # Create a new mesh object
               if(currentObject == None):
                  currentObject = ObjectData()
               faceData = self.pointsData.GetTrisData(
                  offset=int(line[1]),
                  count=int(line[2])
               )
               print(currentObject.type, grpObject.name if grpObject else '', currentObject.attr)
               match currentObject.type:
                  case ObjectType.none:
                     # create a standalone mesh object
                     currentObject.type = ObjectType.mesh
                     currentObject.name = f"object"
                     if label != '':
                        currentObject.name += f".{label}"
                     currentObject.faceData = faceData
                     if grpObject:
                        print("appending to group_objects")
                        grpObject.children.append(currentObject)
                     else:
                        print("appending to standard objects")
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
                  currentObject = ObjectData(
                     _type=ObjectType.anim,
                     _name=f"anim{'.' + label if label != '' else ''}"
                  )
                  continue
               match currentObject.type:
                  case ObjectType.none:
                     # repurpose the currentObject as an animation block
                     currentObject.type = ObjectType.anim
                     currentObject.name=f"anim{'.' + label if label != '' else ''}"

                  case ObjectType.anim:
                     # currentObject is still a root level object, and alredy configured for
                     # an animation sequence, add a child animation object
                     # 1. push the currentObject onto the animStack
                     # 2. replace the currentObject with a new instance
                     # 3. configure it for animation
                     childLabel = label if label != '' else ''
                     childObject = ObjectData(
                        _type=ObjectType.anim,
                        _name=f"anim.{childLabel + '.' if childLabel != '' else ''}{len(animStack)+1:003}",
                        attr=currentObject.attr[:])
                     animStack.append(currentObject)
                     currentObject = childObject

                  case _:
                     # no action
                     logger.info(f"ANIM_begin UNDEFINED TYPE: currentObject: {currentObject}")
                     continue

               # reset the label if it was defined
               logger.info(f"ANIM_begin, ObjectType: [{currentObject.type}], name: {currentObject.name}, label: {label}")
               #label = ''

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
      if grpObject:
         self.objects.append(grpObject)


_classes = (
   XplaneImportCollection,
)

register, unregister = bpy.utils.register_classes_factory(_classes)
   