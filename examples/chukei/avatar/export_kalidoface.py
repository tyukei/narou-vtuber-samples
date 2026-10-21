"""Create a separate VRM 0.x edition, with blink and five vowel expressions.

Run via Blender MCP in the dedicated process. The original VRM 1.0 is retained.
"""
import bpy
import math
import json
from pathlib import Path
root=Path(bpy.context.scene['avatar_project_root'])
out=root/'output/avatar'
if bpy.context.object and bpy.context.object.mode!='OBJECT': bpy.ops.object.mode_set(mode='OBJECT')
# Switch back to the original authoring scene; the roundtrip scene is separate.
scene=next(s for s in bpy.data.scenes if s.objects.get('PineappleRig'))
bpy.context.window.scene=scene
rig=scene.objects['PineappleRig']
ext=rig.data.vrm_addon_extension
ext.spec_version='0.0'
v0=ext.vrm0
v0.humanoid.human_bones.clear()
for b in rig.data.bones:
    h=v0.humanoid.human_bones.add(); h.bone=b.name; h.node.bone_name=b.name
v0.first_person.first_person_bone.bone_name='head'
v0.meta.title='Pineapple mascot - Kalidoface'
v0.meta.version='0.2.0'
v0.meta.author='Sketch owner (sample; replace before distribution)'
v0.meta.allowed_user_name='OnlyAuthor'
v0.meta.license_name='Redistribution_Prohibited'
v0.blend_shape_master.blend_shape_groups.clear()
def group(preset, bindings):
    g=v0.blend_shape_master.blend_shape_groups.add(); g.name=preset; g.preset_name=preset
    for obj,key in bindings:
        b=g.binds.add(); b.mesh.mesh_object_name=obj.name; b.index=key; b.weight=1
    return g
eyes=[o for o in scene.objects if o.type=='MESH' and o.name.startswith('Eye')]
for o in eyes:
    center=1.68-o.location.z
    keys=o.data.shape_keys.key_blocks
    for v,b in zip(keys['blink'].data,keys['Basis'].data):
        v.co.z=center+(b.co.z-center)*.07
group('blink',[(o,'blink') for o in eyes])
group('blink_l',[(o,'blink') for o in eyes if o.location.x>0])
group('blink_r',[(o,'blink') for o in eyes if o.location.x<0])
smile=scene.objects['Smile']
# Keep the neutral U-smile; hide it behind the head while a vowel is active.
hide=smile.data.shape_keys.key_blocks.get('vowel_hide') or smile.shape_key_add(name='vowel_hide')
for v,b in zip(hide.data,smile.data.shape_keys.key_blocks['Basis'].data): v.co=b.co; v.co.y+=.10
# A dark filled oval in front of the face, hidden inside the head at neutral.
for old in list(scene.objects):
    if old.name.startswith('Vowel mouth'): bpy.data.objects.remove(old,do_unlink=True)
verts=[(0,-.13,1.455)]+[(.002*math.cos(i*2*math.pi/48),-.13,1.455+.002*math.sin(i*2*math.pi/48)) for i in range(48)]
faces=[(0,i+1,(i+1)%48+1) for i in range(48)]
me=bpy.data.meshes.new('Vowel mouth mesh'); me.from_pydata(verts,[],faces); me.update()
mouth=bpy.data.objects.new('Vowel mouth',me); scene.collection.objects.link(mouth)
mouth.data.materials.append(smile.data.materials[0]); mouth.parent=rig
vg=mouth.vertex_groups.new(name='head'); vg.add(list(range(len(verts))),1,'REPLACE')
mod=mouth.modifiers.new('Humanoid skin','ARMATURE'); mod.object=rig
mouth.shape_key_add(name='Basis')
for preset,rx,rz in [('a',.084,.086),('i',.104,.028),('u',.037,.053),('e',.090,.050),('o',.055,.072)]:
    key=mouth.shape_key_add(name=preset)
    key.data[0].co=(0,-.269,1.46)
    for i in range(48):
        a=i*2*math.pi/48
        key.data[i+1].co=(rx*math.cos(a),-.269,1.46+rz*math.sin(a))
    group(preset,[(mouth,preset),(smile,'vowel_hide')])
# Exporters apply selected shape keys; ensure neutral and T pose for delivery.
for b in rig.pose.bones: b.rotation_mode='XYZ'; b.rotation_euler=(0,0,0)
for o in scene.objects:
    if o.type=='MESH' and o.data.shape_keys:
        for key in o.data.shape_keys.key_blocks: key.value=0
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(out/'pineapple-kalidoface.blend'))
result=bpy.ops.export_scene.vrm(filepath=str(out/'pineapple-kalidoface.vrm'),armature_object_name=rig.name)
assert result=={'FINISHED'},result
print('KALIDOFACE_EXPORT',result,(out/'pineapple-kalidoface.vrm').stat().st_size)
