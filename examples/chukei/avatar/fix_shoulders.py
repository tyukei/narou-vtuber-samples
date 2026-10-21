"""Historical correction applied after the first viewport inspection.

The corrected build_avatar.py already incorporates this change.
"""
import bpy
from pathlib import Path
for side,s in [('left',1),('right',-1)]:
    obj=bpy.data.objects[side+' upper arm']
    for v in obj.data.vertices:
        if abs(v.co.x)<.3: v.co.x-=s*.09
rig=bpy.data.objects['PineappleRig']
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for side,s in [('left',1),('right',-1)]: rig.data.edit_bones[side+'UpperArm'].head.x=s*.10
bpy.ops.object.mode_set(mode='OBJECT')
for screen in bpy.data.screens:
    for a in screen.areas:
        if a.type=='VIEW_3D': a.spaces.active.region_3d.view_distance=3.1
out=Path(bpy.context.scene['avatar_project_root'])/'output/avatar'
bpy.ops.wm.save_as_mainfile(filepath=str(out/'pineapple-avatar.blend'))
print(bpy.ops.export_scene.vrm(filepath=str(out/'pineapple-avatar.vrm'),armature_object_name=rig.name))
