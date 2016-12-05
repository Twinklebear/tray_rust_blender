import bpy
import math
import mathutils
import json
import re
import os
from bpy_extras.io_utils import ExportHelper

bl_info = {
    "name": "tray_rust export",
    "author": "Will Usher",
    "blender": (2, 7, 8),
    "version": (0, 0, 10),
    "location": "File > Import-Export",
    "description": "Export the scene to a tray_rust scene",
    "category": "Import-Export"
}

TRANSFORM_MAT = mathutils.Matrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])

# Convert a matrix from Blender's coordinate system to tray_rust's
def convert_blender_matrix(mat):
    return TRANSFORM_MAT.inverted() * mat * TRANSFORM_MAT * mathutils.Matrix.Rotation(math.radians(90), 4, "X")

# Convert a matrix from Blender's OBJ export coordinate system to tray_rust's
def convert_obj_matrix(mat):
    return TRANSFORM_MAT.inverted() * mat * mathutils.Matrix.Scale(-1, 4, [1, 0, 0]) * TRANSFORM_MAT

# Sample and export the keyframes of the object's animation to a dict for saving to the scene file
# mat_convert is a function that will convert the object's matrix to tray_rust's coordinate
# system. Returns the dict of control points, knots and degree required to specify the curve
# for the animation in the scene file
def export_animation(obj, mat_convert, scene):
    current_frame = scene.frame_current
    frame_time = 1.0 / scene.render.fps
    knots = []
    control_points = []
    start = None
    end = None
    parent_iter = obj
    while parent_iter != None:
        if parent_iter.animation_data and parent_iter.animation_data.action:
            parent_anim_data = parent_iter.animation_data
            if start == None and end == None:
                start = int(parent_anim_data.action.frame_range[0])
                end = int(math.ceil(parent_anim_data.action.frame_range[1]))
            else:
                start = min(start, int(parent_anim_data.action.frame_range[0]))
                end = max(end, int(math.ceil(parent_anim_data.action.frame_range[1])))

        if parent_iter.parent and parent_iter.parent_type == "OBJECT":
            parent_iter = parent_iter.parent
        else:
            break

    knots.append((start - 1) * frame_time)
    for f in range(start - 1, end):
        scene.frame_set(f + 1)
        mat = mat_convert(obj.matrix_world)
        knots.append(f * frame_time)
        control_points.append({
            "transform": [
                {
                    "type": "matrix",
                    "matrix": [mat[0][0:], mat[1][0:], mat[2][0:], mat[3][0:]]
                }
            ]})
    knots.append((end - 1) * frame_time)
    scene.frame_set(current_frame)
    return {
        "control_points": control_points,
        "knots": knots,
        "degree": 1
    }

# Export the user's film settings to their tray_rust equivalents
def export_film(operator, context):
    scene = context.scene
    return {
        "width": scene.render.resolution_x,
        "height": scene.render.resolution_y,
        "samples": scene.cycles.samples,
        "frames": scene.frame_end - scene.frame_start + 1,
        "start_frame": scene.frame_start - 1,
        "end_frame": scene.frame_end - 1,
        "scene_time": (scene.frame_end - scene.frame_start + 1) / scene.render.fps,
        "filter" : {
            "type": "mitchell_netravali",
            "width": 2.0,
            "height": 2.0,
                "b": 0.333333333333333333,
                "c": 0.333333333333333333
        },
    }

# TODO: Maybe we could have some kind of UI for the integrator settings?
def export_integrator(operator, context):
    return {
        "type": "pathtracer",
        "min_depth": 4,
        "max_depth": 8
    }

# TODO: Maybe we can add support for some of Blender's/Cycle's material models
# and add UI for ones in tray_rust but not in Blender?
def export_materials(operator, context):
    # TODO: Currently this just exports the viewport material info, we really want
    # Cycle's material info, maybe just the first node I guess?
    material_json = []
    for name, mat in bpy.data.materials.items():
        material_json.append({
            "type": "matte",
            "name": name,
            "diffuse": [mat.diffuse_color.r, mat.diffuse_color.g, mat.diffuse_color.b],
            "roughness": 1.0
        })
    # TODO: How will Blender's default material appear? do we still want to provide
    # this default white one?
    material_json.append({
        "type": "matte",
        "name": "default_white_wall",
        "diffuse": [0.740063, 0.742313, 0.733934],
        "roughness": 1.0
    })
    return material_json

# Export the camera positon/motion from Blender
def export_cameras(operator, context):
    scene = context.scene
    markers = scene.timeline_markers
    cameras = []
    for name, obj in scene.objects.items():
        if obj.type == "CAMERA":
            camera_json = {}
            # Check if the camera fov is animating
            cam = bpy.data.cameras[name]
            if cam.animation_data and cam.animation_data.action and cam.animation_data.action.id_root == "CAMERA":
                scene.frame_set(1)
                frame_time = 1.0 / scene.render.fps
                knots = []
                control_points = []
                anim_data = cam.animation_data
                start = int(anim_data.action.frame_range[0])
                end = int(math.ceil(anim_data.action.frame_range[1]))
                knots.append((start - 1) * frame_time)
                for f in range(start - 1, end):
                    scene.frame_set(f + 1)
                    knots.append(f * frame_time)
                    control_points.append(math.degrees(cam.angle_y))
                knots.append((end - 1) * frame_time)
                scene.frame_set(1)
                camera_json["fov"] = control_points
                camera_json["fov_knots"] = knots
                camera_json["fov_spline_degree"] = 1
            else:
                camera_json["fov"] = math.degrees(cam.angle_y)
            # Check if the camera object is moving
            if obj.animation_data and obj.animation_data.action:
                camera_json["keyframes"] = export_animation(obj, convert_blender_matrix, scene)
            else:
                cam_mat = convert_blender_matrix(obj.matrix_world)
                camera_json["transform"] = [
                    {
                        "type": "matrix",
                        "matrix": [cam_mat[0][0:], cam_mat[1][0:], cam_mat[2][0:], cam_mat[3][0:]]
                    }
                ]
            camera_json["active_at"] = 0
            # See if we can find a timeline marker that makes this camera active
            for m in markers:
                if obj == m.camera:
                    camera_json["active_at"] = m.frame - 1
            cameras.append(camera_json)
    return cameras

def export_mesh(obj, obj_file_name, mesh_transforms, selected_meshes, parents_to_restore, scene):
    geometry = {}
    # Check if we've already found and selected the mesh used by this object and re-use
    # that instance's data if so. Otherwise setup a new entry in our selected meshes
    # so instances of this mesh can find the right model to export.
    if not obj.data.name in selected_meshes:
        obj.select = True
        exported_name = obj.data.name
        if obj.name != obj.data.name:
            exported_name = obj.name + "_" + exported_name
        selected_meshes[obj.data.name] = exported_name
    else:
        obj.select = False

    geometry = {
        "type": "mesh",
        "file": obj_file_name,
        "model": selected_meshes[obj.data.name],
    }

    mat_name = "default_white_wall"
    if obj.active_material:
        mat_name = obj.active_material.name
    obj_json = {
        "name": obj.name,
        "type": "receiver",
        "material": mat_name,
        "geometry": geometry,
    }

    # Check if this object or anyone up its parent chain has animation (thus animating it)
    mesh_transforms[obj.name] = obj.matrix_world.copy()
    has_animation = False
    parent_iter = obj
    while parent_iter != None:
        if parent_iter.animation_data and parent_iter.animation_data.action:
            has_animation = True
            break
        if parent_iter.parent and parent_iter.parent_type == "OBJECT":
            parent_iter = parent_iter.parent
        else:
            break

    if has_animation:
        obj_json["keyframes"] = export_animation(obj, convert_obj_matrix, scene)
    else:
        obj_mat = convert_obj_matrix(obj.matrix_world)
        obj_json["transform"] = [
                {
                    "type": "matrix",
                    "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                }
            ]
    if obj.parent:
        parents_to_restore.append((obj, obj.parent))
    return obj_json

def export_metaball(obj, mesh_transforms, scene):
    obj.select = False
    mat_name = "default_white_wall"
    if obj.active_material:
        mat_name = obj.active_material.name
    obj_json = {
        "name": obj.name,
        "type": "receiver",
        "material": mat_name,
        "geometry": {
            "type": "sphere",
            "radius": 1
        }
    }

    mesh_transforms[obj.name] = obj.matrix_world.copy()
    if obj.animation_data and obj.animation_data.action:
        obj_json["keyframes"] = export_animation(obj, convert_blender_matrix, scene)
        # Mute keyframe animation so it doesn't block (location|rotation|scale)_clear
        for curve in obj.animation_data.action.fcurves:
            curve.mute = True
    else:
        obj_mat = convert_blender_matrix(obj.matrix_world)
        obj_json["transform"] = [
                {
                    "type": "matrix",
                    "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                }
            ]
    return obj_json

def export_light(obj, mesh_transforms, scene):
    obj.select = False
    lamp = bpy.data.lamps[obj.name]

    obj_json = {
        "name": obj.name,
        "type": "emitter"
    }
    mesh_transforms[obj.name] = obj.matrix_world.copy()

    has_animation = False
    parent_iter = obj
    while parent_iter != None:
        if parent_iter.animation_data and parent_iter.animation_data.action:
            has_animation = True
            break
        if parent_iter.parent and parent_iter.parent_type == "OBJECT":
            parent_iter = parent_iter.parent
        else:
            break

    if has_animation:
        obj_json["keyframes"] = export_animation(obj, convert_blender_matrix, scene)
    else:
        obj_mat = convert_blender_matrix(obj.matrix_world)
        obj_json["transform"] = [
                {
                    "type": "matrix",
                    "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                }
            ]

    if lamp.type == "POINT":
        obj_json["emitter"] = "point"
        obj_json["emission"] = [0.780131, 0.780409, 0.775833, 100]
    elif lamp.type == "AREA":
        lamp_geometry = {}
        # TODO: Sphere and disk lights
        if lamp.shape == "SQUARE":
            lamp_geometry = {
                "type": "rectangle",
                "width": lamp.size,
                "height": lamp.size
            }
        elif lamp.shape == "RECTANGLE":
            lamp_geometry = {
                "type": "rectangle",
                "width": lamp.size,
                "height": lamp.size_y
            }
        obj_json["material"] = "default_white_wall"
        obj_json["emitter"] = "area"
        obj_json["emission"] = [0.780131, 0.780409, 0.775833, 100]
        obj_json["geometry"] = lamp_geometry
    return obj_json

def export_tray_rust(operator, context, filepath="", check_existing=False):
    scene = context.scene

    mesh_transforms = {}
    parents_to_restore = []
    objects = []
    obj_path, obj_file_name = os.path.split(filepath)
    obj_file_name, _ = os.path.splitext(obj_file_name)
    obj_file_name += ".obj"
    selected_meshes = {}

    # Add the scene objects
    for name, obj in scene.objects.items():
        # Append all the meshes in the scene
        if obj.type == "MESH":
            objects.append(export_mesh(obj, obj_file_name, mesh_transforms, selected_meshes,
                           parents_to_restore, scene))
        # Convert meta balls to analytic spheres
        elif obj.type == "META":
            objects.append(export_metaball(obj, mesh_transforms, scene))
        # Export lights
        elif obj.type == "LAMP":
            objects.append(export_light(obj, mesh_transforms, scene))

    cameras = export_cameras(operator, context)

    # Make sure the camera isn't selected before clearing position data
    camera = scene.objects["Camera"].select = False

    # Mute keyframe animation so it doesn't block (location|rotation|scale)_clear
    for name, obj in scene.objects.items():
        if obj.animation_data and obj.animation_data.action:
            for curve in obj.animation_data.action.fcurves:
                curve.mute = True
    # Clear all parents before clearing positions so we can get the objects actually at
    # their origin transform
    for (obj, par) in parents_to_restore:
        obj.parent = None

    # Reset all transformations
    bpy.ops.object.location_clear()
    bpy.ops.object.rotation_clear()
    bpy.ops.object.scale_clear()

    # Save out the OBJ containing all our meshes
    bpy.ops.export_scene.obj("EXEC_DEFAULT", False, filepath=obj_path + "/" + obj_file_name,
        axis_forward="Z", axis_up="Y", use_materials=False, use_uvs=True, use_normals=True,
        use_triangles=True, use_selection=True)

    # Restore all cleared parenting
    for (obj, par) in parents_to_restore:
        obj.parent = par

    # Restore all transformations
    for name, obj in scene.objects.items():
        if obj.type == "MESH" or obj.type == "META" or obj.type == "LAMP":
            obj.matrix_world = mesh_transforms[obj.name]
            obj.select = False
            if obj.animation_data and obj.animation_data.action:
                # Unmute keyframe animation to restore it
                for curve in obj.animation_data.action.fcurves:
                    curve.mute = False

    # Save out the JSON scene file
    json_scene = {
        "film": export_film(operator, context),
        "cameras": cameras,
        "integrator": export_integrator(operator, context),
        "materials": export_materials(operator, context),
        "objects": objects
    }
    with open(filepath, "w") as f:
        json.dump(json_scene, f, indent=4)

    return { "FINISHED" }

class ExportTrayRust(bpy.types.Operator, ExportHelper):
    """Save a tray_rust scene, exports a JSON scene file + OBJ mesh file"""

    bl_idname = "export_tray_rust.json"
    bl_label = "Export tray_rust"
    bl_options = { "PRESET" }
    filename_ext = ".json"

    def execute(self, context):
        keywords = self.as_keywords()
        return export_tray_rust(self, context, **keywords)

def menu_func(self, context):
    self.layout.operator(ExportTrayRust.bl_idname, text="tray_rust scene (.json + .obj)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()

