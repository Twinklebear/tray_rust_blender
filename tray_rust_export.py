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

# TODO: Hardcoded film properties for now
film = {
    "width": bpy.data.scenes["Scene"].render.resolution_x,
    "height": bpy.data.scenes["Scene"].render.resolution_y,
    "samples": bpy.data.scenes["Scene"].cycles.samples,
    "frames": 1,
    "start_frame": 0,
    "end_frame": 0,
    "scene_time": 0,
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

print("\n\n\n\n\n\n\n")
print("film = {}".format(json.dumps(film, indent=4)))
print("integrator = {}".format(json.dumps(integrator, indent=4)))
print("materials = {}".format(json.dumps(materials, indent=4)))

scene = bpy.context.scene
camera = scene.objects["Camera"]
camera.select = False
cam_mat = camera.matrix_world
print(camera.matrix_world)

cam_mat = convert_blender_matrix(cam_mat)
camera = {
    "fov": math.degrees(bpy.data.cameras["Camera"].angle_y),
    "transform": [
        {
            "type": "matrix",
            "matrix": [cam_mat[0][0:], cam_mat[1][0:], cam_mat[2][0:], cam_mat[3][0:]]
        }
    ]
}
print("camera = {}".format(json.dumps(camera, indent=4)))

match_instance = re.compile("(\w+)\.\d+")
mesh_transforms = {}
objects = []
obj_file = "test.obj"
# Add the scene objects
for name, obj in scene.objects.items():
    print("Appending {} to the objects, type = {}".format(name, obj.type))
    # Append all the meshes in the scene
    if obj.type == "MESH":
        # Note: We don't perform the X rotation on meshes because they get rotated when exporting to the OBJ file
        transform_mat = mathutils.Matrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
        obj_mat = mathutils.Matrix.Scale(-1, 4, [1, 0, 0]) * transform_mat.inverted() \
                * obj.matrix_world * transform_mat
        mesh_transforms[name] = obj.matrix_world.copy()
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
                "model": instance.group(1),
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
            "transform": [
                {
                    "type": "matrix",
                    "matrix": [obj_mat[0][0:], obj_mat[1][0:], obj_mat[2][0:], obj_mat[3][0:]]
                }
            ]
        })
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
    "camera": camera,
    "integrator": integrator,
    "materials": materials,
    "objects": objects
}

with open(filepath + scene_file, "w") as f:
    json.dump(scene, f, indent=4)

