"""Reimport the VRM 0.x file and preview Blink + A in Blender, not Kalidoface."""
import bpy
import json
from pathlib import Path
from mathutils import Quaternion
import math
root=Path(bpy.context.scene['avatar_project_root'])
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.scene.new(type='EMPTY')
bpy.context.scene.name='Kalidoface VRM0 expression check'
bpy.context.scene['avatar_project_root']=str(root)
assert bpy.ops.import_scene.vrm(filepath=str(root/'output/avatar/pineapple-kalidoface.vrm'))=={'FINISHED'}
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
groups=rig.data.vrm_addon_extension.vrm0.blend_shape_master.blend_shape_groups
presets={g.preset_name:g for g in groups}
assert all(k in presets for k in ['blink','blink_l','blink_r','a','i','u','e','o'])
report={}
for name,g in presets.items():
    report[name]=[]
    for bind in g.binds:
        obj=bpy.data.objects[bind.mesh.mesh_object_name]
        keys=obj.data.shape_keys.key_blocks
        delta=max((v.co-b.co).length for v,b in zip(keys[bind.index].data,keys[0].data))
        assert delta>0
        report[name].append({'mesh':obj.name,'key':bind.index,'max_delta_m':delta})
for g in groups: g.preview=0
presets['blink'].preview=1
presets['a'].preview=1
for a in bpy.context.screen.areas:
    if a.type=='VIEW_3D':
        sp=a.spaces.active; sp.overlay.show_overlays=False
        sp.shading.type='MATERIAL'
        sp.region_3d.view_rotation=Quaternion((1,0,0),math.pi/2)
        sp.region_3d.view_perspective='ORTHO'; sp.region_3d.view_location=(0,0,1.6); sp.region_3d.view_distance=1.65
(root/'output/avatar/kalidoface-blender-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('VRM0_REIMPORT_AND_EXPRESSION_BINDINGS_OK',list(presets))
