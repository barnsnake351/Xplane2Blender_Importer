import bpy
import bmesh
import math
import mathutils
from mathutils import Vector, Euler
import itertools
import os
import pathlib
from typing import List
from dataclasses import dataclass
from collections import namedtuple

from ..v2.CollectionVertex import CollectionVertex

def stub_filePath():
    base_dir = r'C:\Users\brian_vrow8dy\OneDrive\Blender\Projects\X-Plane\Aircraft\Northrop T-38'
    obj_dir = r'objects'
    file_name = r'T38_cockpit.obj'
    return pathlib.Path(base_dir, obj_dir, file_name)

#def reloadObjectCollection():
#    from importlib import reload
#    from Xplane2Blender_Importer.v2 import ObjectCollection
#    reload(Xplane2Blender_Importer.v2)

@dataclass
class PointCounts:
    tris: int = 0
    lines: int = 0
    lites: int = 0
    indices: int = 0

class ObjectCollection:
    _origin = Vector((0,0,0))
    collection = None
    filePath = None
    lines = []
    material = None
    material_normal_metalness = False
    name = ''
    verts = []
    normals = []
    uv = []
    faces = []
    pointCounts = PointCounts(0,0,0,0)
    def __init__(self, filePath=None):
        if(filePath != None):
            self.filePath = filePath
            self.name = filePath.stem
            self.parseFile()
        
    def __str__(self):
        print(f"collection: {self.collection}...TBD")

    def resetCollection(self, remove_collection_objects=True):
        if self.collection:
            obs = [o for o in self.collection.objects if o.users == 1]
            while obs:
                bpy.data.objects.remove(obs.pop())
            bpy.data.collections.remove(self.collection)
            self.collection = None
        if self.material:
            bpy.data.materials.remove(self.material)
            
        self.filePath = None
        self.faces = []
        self.lines = []
        self.verts = []
        self.material_normal_metalness = False
        self.name = ''

        
    def readAllLines(self, filePath=None):
        if(filePath == None):
            filePath = self.filePath
        try:
            f = open(filePath, 'r')
            self.lines = f.readlines()
            f.close
        except:
            print(f"Failed to read file {filePath}")


    def configureCollection(self, filePath=None):
        if(filePath == None):
            filePath = self.filePath
        self.collection = bpy.data.collections.new(filePath.stem)
        self.collection.hide_render = True
        bpy.context.scene.collection.children.link(self.collection)
        try:
            self.collection.xplane.layer.name = filePath.stem
            self.collection.xplane.is_exportable_collection = True
        except:
            self.collection = None
            print(f"Failed to detect xplane module, ensure that the XPlane2Blender add-on is enabled")

    def loadImageTexture(self, filePath):
        fp = pathlib.Path(self.filePath.parent, filePath)
        print(f"Attempting to load texture: {str(fp)}")
        try:
            tex = bpy.data.textures.new('Texture', type = 'IMAGE')
            tex.image = bpy.data.images.load(str(fp))
            return tex
        except:
            print(f"Unable to locate image {fp}, attempting to load a '.dds' version...")
            fp = pathlib.Path(f"{str(pathlib.Path(self.filePath.parent, filePath.stem))}.dds")
            try:
                tex.image = bpy.data.images.load(str(fp))
                return tex
            except:
                print(f"Unable to locate image file: {fp}")
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
        if(self.material_normal_metalness):
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
            print(f"failed to set collection param [{param}] to value [{value}]")
            return False

    def parseFile(self, filePath=None):
        if(filePath!=None):
            self.resetCollection()
            self.filePath=filePath
            self.name = self.filePath.stem
        self.readAllLines(filePath)
        self.configureCollection(filePath)
        for lineStr in self.lines:
            line = lineStr.split()
            if (len(line) == 0):
                continue
            if(line[0] == 'TEXTURE'):
                texFile = pathlib.Path(line[1])
                tex = self.loadImageTexture(texFile)
                if(tex):
                    self.createMaterial(tex, texFile.stem)
                    self.setCollectionParameter('texture', texFile.name)

            if(line[0] == 'TEXTURE_NORMAL'):
                texFile = pathlib.Path(line[1])
                nrmTex = self.loadImageTexture(texFile)
                if(nrmTex):
                    self.createNormalMap(nrmTex)
                    self.setCollectionParameter('texture_normal', texFile.name)
           
            if(line[0] == 'NORMAL_METALNESS'):
                self.material_normal_metalness = True
                nodes = self.material.node_tree.nodes
                normalNode = nodes.get("Normal Texture")
                if(normalNode):
                    normalNode.inputs.get("Strength").default_value = 0.0
                self.setCollectionParameter('normal_metalness', True)

            if(line[0] == 'TEXTURE_LIT'):
                texFile = pathlib.Path(line[1])
                emissionTex = self.loadImageTexture(texFile)
                if(emissionTex):
                    self.createEmissionShader(emissionTex)
                    self.setCollectionParameter('texture_lit', texFile.name)
            
            if(line[0] == 'BLEND_GLASS'):
                self.setCollectionParameter('blend_glass', True)
            
            if(line[0] == 'GLOBAL_specular'):
                val = line[1]
                if(val != "1.0"):
                    print(f"NOTE: GLOBAL_specular detected at {val}, newer version of Xplane2Blender will override this to 1.0")
            
            if(line[0] == 'POINT_COUNTS'):
                if(len(line) != 5):
                    print(f"error: bad input for [POINT_COUNTS], expected 'POINT_COUNTS <tris> <lines> <lites> <indices>', received {line}")
                self.pointCounts = PointCounts(
                    tris=int(line[1]),
                    lines=int(line[2]),
                    lites=int(line[3]),
                    indices=int(line[4])
                )
                pass

            if(line[0] == 'VT'):
                if(len(line) != 9):
                    print(f"error: invalid VT line format, expected [VT <x> <z> <-y> <nx> <nz> <-ny> <uvx> <uvy>], received [{line}]")
                    continue

                vert = Vector((
                    float(line[1]),
                    (float(line[3]) * -1),
                    float(line[2])
                ))
                norm = Vector((
                    float(line[4]),
                    (float(line[6]) * -1),
                    float(line[5])
                ))
                uv = (float(line[7]),float(line[8]))
                self.verts.append(vert)
                self.normals.append(norm)
                self.uv.append(uv)
                
            if(line[0] == 'IDX10' or line[0] == 'IDX'):
                self.faces.extend(map(int,line[1:]))
                
        # Check to confirm verts and indices match expected valued
        if(len(self.verts) != self.pointCounts.tris):
            print(f"error: captured verts count {len(self.verts)} != defined tris count {self.pointCounts.tris}")
        if(len(self.faces) != self.pointCounts.indices):
            print(f"error: captured face count {len(self.faces)} != defined vertices count {self.pointCounts.indices}")
        
        if(line[0] == 'TRIS'):
            # Create a new mesh object
            print(f"creating mesh for: {line}")
            tris_offset = int(line[1])
            tris_count  = int(line[2])
            face_first  = self.faces[tris_offset:tris_offset+tris_count]
            faceData    = tuple( zip(*[iter(face_first)]*3) )

            obLabel = f"{self.name}.OBJ"
            me = bpy.data.meshes.new(f"{obLabel}.mesh")
            ob = bpy.data.objects.new(obLabel, me)
            ob.location = self._origin
            ob.show_name = False

            self.collection.objects.link(me)
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            me.from_pydata(self.verts, [], faceData)
            
            vIndex = 0
            newNorms = []
            for v in me.vertices:
                newNorms.append(self.normals[vIndex])
                vIndex += 1

            me.normals_split_custom_set_from_vertices(newNorms)
            me.calc_normals_split()
            me.update(calc_edges=True)

            uvl = me.uv_layers.new()
            me.uv_layers.active = uvl

            for face in me.polygons:
                for vert_idx, loop_idx in zip(face.vertices, face.loop_indices):
                    uvl.data[loop_idx].uv = self.uv[vert_idx]

            if(self.material):
                ob.data.materials.append(self.material)

            

            



                
                
