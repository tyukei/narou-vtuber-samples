"""Reimport the exported file into an empty scene, then check actual deformation."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector
root=Path(bpy.context.scene['avatar_project_root'])
out=root/'output/avatar'
bpy.ops.scene.new(type='EMPTY')
bpy.context.scene.name='VRM roundtrip check'
bpy.context.scene['avatar_project_root']=str(root)
result=bpy.ops.import_scene.vrm(filepath=str(out/'pineapple-avatar.vrm'))
assert result=={'FINISHED'},result
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
rig.show_in_front=True
rig.data.display_type='STICK'
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
mapping={str(k.value if hasattr(k,'value') else k):v.node.bone_name for k,v in rig.data.vrm_addon_extension.vrm1.humanoid.human_bones.human_bone_name_to_human_bone().items() if v.node.bone_name}
required=['hips','spine','head']+[s+p for s in ('left','right') for p in ('UpperArm','LowerArm','Hand','UpperLeg','LowerLeg','Foot')]
assert all(mapping.get(n) in rig.data.bones for n in required)
assert all(o.vertex_groups and any(m.type=='ARMATURE' for m in o.modifiers) for o in meshes)
def centroid(obj):
    bpy.context.view_layer.update()
    ev=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return sum((ev.matrix_world@v.co for v in ev.data.vertices),Vector())/len(ev.data.vertices)
movements={}
for semantic,obj_fragment in [('leftLowerArm','left mitten'),('leftLowerLeg','left shoe')]:
    obj=next(o for o in meshes if obj_fragment in o.name)
    before=centroid(obj)
    bone=rig.pose.bones[mapping[semantic]]
    bone.rotation_mode='XYZ'; bone.rotation_euler.x=math.radians(35)
    after=centroid(obj)
    movements[semantic]=(after-before).length
    assert movements[semantic]>.025,movements
    bone.rotation_euler=(0,0,0)
expression_counts={}
for name in ('blink','aa'):
    binds=getattr(rig.data.vrm_addon_extension.vrm1.expressions.preset,name).morph_target_binds
    assert len(binds)>0
    expression_counts[name]=len(binds)
    for bind in binds:
        obj=bpy.data.objects[bind.node.mesh_object_name]
        key=obj.data.shape_keys.key_blocks[bind.index]
        assert any((a.co-b.co).length>1e-5 for a,b in zip(key.data,obj.data.shape_keys.key_blocks[0].data))
report={'blender':bpy.app.version_string,'vrm_spec':'1.0','reimport':'FINISHED','mesh_count':len(meshes),'humanoid_bone_count':len(mapping),'required_bones':required,'deformation_displacement_m':movements,'expression_bind_counts':expression_counts,'limits':['No external tracking application tested in this check','Rigid segmented mascot skin; no finger bones','aa is a stretched smile, not a mouth cavity','Personal non-commercial use and local modification permitted; redistribution prohibited; see USAGE.txt']}
(out/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
bpy.ops.object.select_all(action='DESELECT'); rig.select_set(True); bpy.context.view_layer.objects.active=rig
rig.pose.bones[mapping['leftLowerArm']].rotation_euler.x=math.radians(60)
rig.pose.bones[mapping['rightUpperArm']].rotation_mode='XYZ'
rig.pose.bones[mapping['rightUpperArm']].rotation_euler.x=math.radians(-25)
rig.pose.bones[mapping['leftLowerLeg']].rotation_euler.x=math.radians(30)
bpy.context.view_layer.update()
bpy.ops.object.mode_set(mode='POSE')
print(json.dumps(report,ensure_ascii=False))
