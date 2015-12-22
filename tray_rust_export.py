import bpy
import math
import mathutils
import json
import re

# Convert a matrix from Blender's coordinate system to tray_rust's
def convert_blender_matrix(mat):
    transform_mat = mathutils.Matrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
    return mathutils.Matrix.Scale(-1, 4, [1, 0, 0]) * transform_mat.inverted() * mat \
        * transform_mat * mathutils.Matrix.Rotation(math.radians(90), 4, "X")

filepath = "C:/Users/Will/Desktop/"

scene = bpy.context.scene
film = {
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
integrator = {
    "type": "normals_debug",
    "min_depth": 4,
    "max_depth": 8
}
materials = [
    {
        "type": "matte",
        "name": "white_wall",
        "diffuse": [0.740063, 0.742313, 0.733934],
        "roughness": 1.0
    }
]

camera = scene.objects["Camera"]
camera.select = False
camera_json = {
    "fov": math.degrees(bpy.data.cameras[camera.name].angle_y),
}

if camera.animation_data and camera.animation_data.action:
    print("Animation data for {} = {}".format("Camera", camera.animation_data))
    print("frame range = {}".format(camera.animation_data.action.frame_range))
    frame_time = 1.0 / scene.render.fps
    knots = []
    control_points = []
    anim_data = camera.animation_data
    start = int(anim_data.action.frame_range[0])
    end = int(math.ceil(anim_data.action.frame_range[1]))
    knots.append(start)
    for f in range(start, end + 1):
        scene.frame_set(f)
        cam_mat = convert_blender_matrix(camera.matrix_world)
        knots.append(f * frame_time)
        control_points.append({
            "transform": [
                {
                    "type": "matrix",
                    "matrix": [cam_mat[0][0:], cam_mat[1][0:], cam_mat[2][0:], cam_mat[3][0:]]
                }
            ]})
    knots.append(end)

    scene.frame_set(1)
    camera_json["keyframes"] = {
            "control_points": control_points,
            "knots": knots,
            "degree": 1
        }
else:
    cam_mat = convert_blender_matrix(camera.matrix_world)
    camera_json["transform"] = [
            {
                "type": "matrix",
                "matrix": [cam_mat[0][0:], cam_mat[1][0:], cam_mat[2][0:], cam_mat[3][0:]]
            }
        ]

print("camera = {}".format(json.dumps(camera_json, indent=4)))

match_instance = re.compile("(\w+)\.\d+")
mesh_transforms = {}
objects = []
obj_file = "test.obj"

# Add the scene objects
for name, obj in scene.objects.items():
    print("Appending {} to the objects, type = {}".format(name, obj.type))
    # Append all the meshes in the scene
    if obj.type == "MESH":
        # Check if this is an instance or a "real" object
        instance = match_instance.match(name)
        geometry = {}
        # If it's an instance we expect the real object to be exported without
        # the .### in the name, so use that model in the OBJ file. To prevent exporting
        # this object we also don't select it
        if instance:
            obj.select = False
            geometry = {
                "type": "mesh",
                "file": obj_file,
                "model": obj.data.name,
            }
        else:
            obj.select = True
            geometry = {
                "type": "mesh",
                "file": obj_file,
                "model": name,
            }
        objects.append({
            "name": name,
            "type": "receiver",
            "material": "white_wall",
            "geometry": geometry,
        })

        mesh_transforms[name] = obj.matrix_world.copy()
        # Note: We don't perform the X rotation on meshes because they get rotated when exporting to the OBJ file
        transform_mat = mathutils.Matrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
        if obj.animation_data and obj.animation_data.action:
            print("Animation data for {} = {}".format(name, obj.animation_data))
            print("frame range = {}".format(obj.animation_data.action.frame_range))
            frame_time = 1.0 / scene.render.fps
            knots = []
            control_points = []
            anim_data = obj.animation_data
            start = int(anim_data.action.frame_range[0])
            end = int(math.ceil(anim_data.action.frame_range[1]))
            knots.append(start)
            for f in range(start, end + 1):
                scene.frame_set(f)
                obj_mat = mathutils.Matrix.Scale(-1, 4, [1, 0, 0]) * transform_mat.inverted() \
                        * obj.matrix_world * transform_mat
                knots.append(f * frame_time)
                control_points.append({
                    "transform": [
                        {
                            "type": "matrix",
                            "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                        }
                    ]})
            knots.append(end)

            scene.frame_set(1)
            objects[-1]["keyframes"] = {
                    "control_points": control_points,
                    "knots": knots,
                    "degree": 1
                }
        else:
            obj_mat = mathutils.Matrix.Scale(-1, 4, [1, 0, 0]) * transform_mat.inverted() \
                    * obj.matrix_world * transform_mat
            objects[-1]["transform"] = [
                    {
                        "type": "matrix",
                        "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                    }
                ]

    # Convert meta balls to analytic spheres
    if obj.type == "META":
        obj.select = False
        obj_mat = convert_blender_matrix(obj.matrix_world)
        objects.append({
            "name": name,
            "type": "receiver",
            "material": "white_wall",
            "geometry": {
                "type": "sphere",
                "radius": 1
            },
            "transform": [
                {
                    "type": "matrix",
                    "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                }
            ]
        })
    # Export lights
    if obj.type == "LAMP":
        obj.select = False
        lamp = bpy.data.lamps[name]
        if lamp.type == "POINT":
            obj_mat = convert_blender_matrix(obj.matrix_world)
            objects.append({
                "name": name,
                "type": "emitter",
                "emitter": "point",
                "emission": [0.780131, 0.780409, 0.775833, 100],
                "transform": [
                    {
                        "type": "matrix",
                        "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                    }
                ]
            })
        elif lamp.type == "AREA":
            obj_mat = convert_blender_matrix(obj.matrix_world)
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
            # TODO: Configuring light properties
            objects.append({
                "name": name,
                "type": "emitter",
                "material": "white_wall",
                "emitter": "area",
                "emission": [0.780131, 0.780409, 0.775833, 100],
                "geometry": lamp_geometry,
                "transform": [
                    {
                        "type": "matrix",
                        "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                    }
                ]
            })

# Reset all transformations
bpy.ops.object.location_clear()
bpy.ops.object.rotation_clear()
bpy.ops.object.scale_clear()

# Save out the OBJ containing all our meshes
bpy.ops.export_scene.obj("EXEC_DEFAULT", False, filepath=filepath + "test.obj",
    axis_forward="Z", axis_up="Y", use_materials=False, use_uvs=True, use_normals=True,
    use_triangles=True, use_selection=True)

# Restore all transformations
for name, obj in scene.objects.items():
    if obj.type == "MESH":
        obj.matrix_world = mesh_transforms[name]
        obj.select = False

# Save out the JSON scene file
scene_file = "test.json"
scene = {
    "film": film,
    "camera": camera_json,
    "integrator": integrator,
    "materials": materials,
    "objects": objects
}

with open(filepath + scene_file, "w") as f:
    json.dump(scene, f, indent=4)

