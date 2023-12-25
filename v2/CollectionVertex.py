from mathutils import Vector, Euler

class CollectionVertex:
    vert   = Vector( (0.0,0.0,0.0) )
    normal = Vector( (0.0,0.0,0.0) )
    uv     = Vector( (0.0,0.0,0.0) )
    def __init__(self, line=None):
        if(line != None):
            self.SetFromLine(line)

    def __repr__(self):
        return f"CollectionVertex()"
    
    def __str__(self):
        print(hex(id(self)))
        return f"vert={self.vert}, normal={self.normal}, uv={self.uv}"

    def SetFromLine(self, line):
        # VT x z -y xn zn -yn uvx uvy
        self.vert = Vector((
            float(line[1]),
            (float(line[3]) * -1),
            float(line[2])
        ))
        self.normal = Vector((
            float(line[4]),
            (float(line[6]) * -1),
            float(line[5])
        ))
        self.uv = Vector((
            float(line[7]),
            float(line[8]),
            0.0
        ))
        return self
 