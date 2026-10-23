"""Add humanoid bones, rigid cartoon skin weights and VRM 1.0 expressions."""
import bpy
from pathlib import Path
ROOT=Path(bpy.context.scene['avatar_project_root']); OUT=ROOT/'output/avatar'
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and 'bind_bone' in o]
ad=bpy.data.armatures.new('Pineapple humanoid')
rig=bpy.data.objects.new('PineappleRig',ad); bpy.context.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
def bone(name,head,tail,parent=None):
    b=ad.edit_bones.new(name); b.head=head; b.tail=tail
    if parent: b.parent=ad.edit_bones[parent]
bone('hips',(0,0,.56),(0,0,.83))
bone('spine',(0,0,.83),(0,0,1.05),'hips')
bone('chest',(0,0,1.05),(0,0,1.255),'spine')
bone('neck',(0,0,1.255),(0,0,1.36),'chest')
bone('head',(0,0,1.36),(0,0,1.94),'neck')
for side,s in [('left',1),('right',-1)]:
    bone(side+'UpperArm',(s*.10,0,1.255),(s*.48,0,1.255),'chest')
    bone(side+'LowerArm',(s*.48,0,1.255),(s*.74,0,1.255),side+'UpperArm')
    bone(side+'Hand',(s*.74,0,1.255),(s*.87,0,1.255),side+'LowerArm')
    bone(side+'UpperLeg',(s*.15,0,.57),(s*.175,0,.33),'hips')
    bone(side+'LowerLeg',(s*.175,0,.33),(s*.20,0,.11),side+'UpperLeg')
    bone(side+'Foot',(s*.20,0,.11),(s*.20,-.16,.07),side+'LowerLeg')
bpy.ops.object.mode_set(mode='OBJECT')
ext=ad.vrm_addon_extension; ext.spec_version='1.0'
hb=ext.vrm1.humanoid.human_bones.human_bone_name_to_human_bone()
for key,val in hb.items():
    name=key.value if hasattr(key,'value') else str(key)
    if name in ad.bones: val.node.bone_name=name
for o in parts:
    g=o.vertex_groups.new(name=o['bind_bone']); g.add(list(range(len(o.data.vertices))),1.0,'REPLACE')
    m=o.modifiers.new('Humanoid skin','ARMATURE'); m.object=rig
    o.parent=rig
# Blink compresses the ink eyes and highlights; aa stretches the smile vertically.
for o in parts:
    if o.name.startswith(('Eye','Smile')):
        o.shape_key_add(name='Basis')
        key=o.shape_key_add(name='blink' if o.name.startswith('Eye') else 'aa')
        center=sum(v.co.z for v in key.data)/len(key.data)
        for v in key.data: v.co.z=center+(v.co.z-center)*(.07 if key.name=='blink' else 1.8)
        expression=getattr(ext.vrm1.expressions.preset,key.name)
        bind=expression.morph_target_binds.add(); bind.node.mesh_object_name=o.name
        bind.index=key.name; bind.weight=1.0
meta=ext.vrm1.meta
meta.vrm_name='Pineapple sketch mascot'; meta.version='0.1.0'
meta.authors.add().value='chukei'
meta.avatar_permission='everyone'; meta.allow_redistribution=False
meta.modification='allowModification'; meta.commercial_usage='personalNonProfit'
meta.credit_notation='required'
meta.other_license_url='https://github.com/tyukei/narou-vtuber-samples/blob/main/examples/chukei/avatar/USAGE.txt'
rig.show_in_front=True; ad.display_type='STICK'
bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'pineapple-avatar.blend'))
result=bpy.ops.export_scene.vrm(filepath=str(OUT/'pineapple-avatar.vrm'),armature_object_name=rig.name)
print('VRM_EXPORT',result)
assert result=={'FINISHED'},result
print('VRM_BYTES',(OUT/'pineapple-avatar.vrm').stat().st_size)
