#---------------------------------------------------------------------------
#
#  Import an X-Plane .obj file into Blender 2.78
#
# Dave Prue <dave.prue@lahar.net>
#
# MIT License
#
# Copyright (c) 2017 David C. Prue
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
#---------------------------------------------------------------------------    
#
# Updated to support current versions of Blender >= 4.0
#
# Original credit to both Dave Prue and Tony Nemec for their work on the
# bulk of this tooling.
#
# Brian Engleman <barnsnake351@gmail.com>
#
# * Migrated to standardized module definition
# * Adjusted animations to use Empties over Armatures
# * Added options to override mesh-import topology characteristics
#   * Tris->Quad
#   * Auto-Smooth
#
#---------------------------------------------------------------------------    


bl_info = {
    "name": "Import: X-Plane (.obj)",
    "author": "Brian Engleman - original authors: Tony Nemec - original script by David C. Prue",
    "version": (0,2,0),
    "blender": (3,10,0),
    "location": "File > Import/Export > X-Plane",
    "description": "Import X-Plane objects/planes (.obj format)",
#    "warning": "Requires installation of dependencies",
    "category": "Import-Export",
}

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())

from .register import *
