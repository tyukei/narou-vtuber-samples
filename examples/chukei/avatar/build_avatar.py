"""Execute in Blender through execute_blender_code. Units: meters, front: -Y.

Uses only Blender primitives and generated mesh geometry; no external 3D service.
Run in the dedicated empty scene, never in an unsaved working scene.
"""
import bpy
import math
from mathutils import Vector, Quaternion
from pathlib import Path

ROOT = Path(bpy.context.scene.get('avatar_project_root', Path.cwd()))
OUT = ROOT / 'output/avatar'
OUT.mkdir(parents=True, exist_ok=True)
if bpy.context.scene.get('avatar_created'):
    raise RuntimeError('Already created: use a fresh dedicated scene to rebuild.')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene['avatar_created'] = True
parts = []

def material(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = .72
    return m

white = material('Cream white', (.95, .95, .88))
black = material('Ink charcoal', (.012, .018, .016))
green = material('Leaf green', (.12, .72, .018))
gold = material('Pineapple yellow', (1, .62, .025))

def finish(o, name, mat, bone):
    o.name = name
    o.data.materials.append(mat)
    for p in o.data.polygons: p.use_smooth = True
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o['bind_bone'] = bone
    parts.append(o)
    return o

def sphere(name, loc, scale, mat, bone):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=loc)
    o = bpy.context.object
    o.scale = scale
    return finish(o, name, mat, bone)

def tube(name, points, radius, mat, bone):
    c = bpy.data.curves.new(name, 'CURVE')
    c.dimensions = '3D'
    c.bevel_depth = radius
    c.bevel_resolution = 3
    s = c.splines.new('POLY')
    s.points.add(len(points)-1)
    for p, co in zip(s.points, points): p.co = (*co, 1)
    o = bpy.data.objects.new(name, c)
    bpy.context.collection.objects.link(o)
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.convert(target='MESH')
    return finish(bpy.context.object, name, mat, bone)

# A pear-shaped surface of revolution, continuous grid lines around its back.
def body_point(t, a, expand=0):
    z = .53 + .79*t
    r = .035 + .29 * math.sin(math.pi*t)**.52 * (1.2-.52*t)
    return ((r+expand)*math.cos(a), (r*.80+expand)*math.sin(a), z)

verts = [body_point(j/32, i*2*math.pi/64) for j in range(33) for i in range(64)]
faces = [(j*64+i,j*64+(i+1)%64,(j+1)*64+(i+1)%64,(j+1)*64+i) for j in range(32) for i in range(64)]
faces += [tuple(reversed(range(64))), tuple(32*64+i for i in range(64))]
mesh = bpy.data.meshes.new('Pear mesh'); mesh.from_pydata(verts, [], faces); mesh.update()
o = bpy.data.objects.new('Body', mesh); bpy.context.collection.objects.link(o)
bpy.context.view_layer.objects.active = o; o.select_set(True)
finish(o, 'Body', gold, 'hips')
for direction in (-1,1):
    for k in range(7):
        points = [body_point(.035+.93*j/100, 2*math.pi*k/7+direction*3.0*j/100, .003) for j in range(101)]
        tube('Diamond grid', points, .008, black, 'hips')

sphere('Head', (0,0,1.61), (.345,.255,.325), white, 'head')
eyes=[]
for x in (-.137,.137):
    eyes.append(sphere('Eye', (x,-.235,1.68), (.090,.045,.105), black, 'head'))
    eyes.append(sphere('Eye shine', (x-.020,-.278,1.711), (.032,.010,.038), white, 'head'))
smile=tube('Smile', [(.104*math.cos(math.pi+j*math.pi/32),-.251,1.49+.084*math.sin(math.pi+j*math.pi/32)) for j in range(33)], .015, black, 'head')

# A ring-shaped crown with six points, a plausible depth interpretation.
v=[]
n=48
for level in (0,1):
    for i in range(n):
        a=2*math.pi*i/n
        top=1.995 + .22*(.5+.5*math.cos(6*a))
        r=.30 if level==0 else .36
        v.append((r*math.cos(a), r*.75*math.sin(a), 1.855 if level==0 else top))
f=[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
me=bpy.data.meshes.new('Crown mesh'); me.from_pydata(v,[],f); me.update()
ob=bpy.data.objects.new('Leaf crown',me); bpy.context.collection.objects.link(ob)
bpy.ops.object.select_all(action='DESELECT'); ob.select_set(True); bpy.context.view_layer.objects.active=ob
finish(ob,'Leaf crown',green,'head')
mod=ob.modifiers.new('Leaf thickness','SOLIDIFY'); mod.thickness=.018
bpy.ops.object.modifier_apply(modifier=mod.name)
for level in (0,1):
    tube('Crown ink edge',v[level*n:(level+1)*n]+[v[level*n]],.010,black,'head')

for side,s in [('left',1),('right',-1)]:
    tube(side+' upper arm',[(s*.10,0,1.255),(s*.48,0,1.255)],.026,black,side+'UpperArm')
    sphere(side+' elbow',(s*.48,0,1.255),(.027,.027,.027),black,side+'LowerArm')
    tube(side+' forearm',[(s*.48,0,1.255),(s*.74,0,1.255)],.024,black,side+'LowerArm')
    sphere(side+' mitten',(s*.815,0,1.255),(.085,.055,.069),white,side+'Hand')
    tube(side+' thigh',[(s*.15,0,.57),(s*.175,0,.33)],.028,black,side+'UpperLeg')
    sphere(side+' knee',(s*.175,0,.33),(.029,.029,.029),black,side+'LowerLeg')
    tube(side+' shin',[(s*.175,0,.33),(s*.20,0,.11)],.025,black,side+'LowerLeg')
    sphere(side+' shoe',(s*.20,-.055,.072),(.105,.145,.07),white,side+'Foot')

def view(front=True):
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type=='VIEW_3D':
                sp=a.spaces.active
                sp.shading.type='SOLID'; sp.shading.light='STUDIO'; sp.shading.color_type='MATERIAL'
                sp.shading.show_shadows=True; sp.shading.show_cavity=True
                sp.overlay.show_floor=False; sp.overlay.show_axis_x=False; sp.overlay.show_axis_y=False
                sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2) if front else Quaternion((1,0,0),math.pi/2) @ Quaternion((0,1,0),-.35)
                sp.region_3d.view_perspective='ORTHO'
                sp.region_3d.view_location=(0,0,1.12); sp.region_3d.view_distance=3.1
view()
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'pineapple-model.blend'))
print('MODEL_COMPLETE',len(parts),'meshes')
