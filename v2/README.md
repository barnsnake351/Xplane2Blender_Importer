from Xplane2Blender_Importer.v2 import ObjectCollection

ob = ObjectCollection.ObjectCollection(ObjectCollection.stub_filePath())
ob.readAllLines()
ob.configureCollection()
ob.parseFile()
str(ob.verts[-2:][0])
str(ob.verts[-1:][0])
