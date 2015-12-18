import bpy
import math
import mathutils
import json

filepath = "C:/Users/Will/Desktop/"

# TODO: Hardcoded film properties for now
film = {
    "width": 1280,
    "height": 720,
    "samples": 2,
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
cam_mat = camera.matrix_world
print(camera.matrix_world)

transform_mat = mathutils.Matrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
mat = transform_mat.inverted() * cam_mat * transform_mat * mathutils.Matrix.Rotation(math.radians(90), 4, "X")
camera = {
    "fov": 65,
    "transform": [
        {
            "type": "matrix",
            "matrix": [mat[0][0:], mat[1][0:], mat[2][0:], mat[3][0:]]
        },
        {
            "type": "scale",
            "scaling": [-1, 1, 1]
        }
    ]
}
print("camera = {}".format(json.dumps(camera, indent=4)))

# Just a hacked in hardcoded light for now
objects = [
{
    "name": "light",
    "type": "emitter",
    "material": "white_wall",
    "emitter": "area",
    "emission": [1, 0.772549, 0.560784, 40],
    "geometry": {
        "type": "sphere",
        "radius": 3.5,
        "inner_radius": 0.0
    },
    "transform": [
        {
            "type": "rotate_x",
            "rotation": 90
        },
        {
            "type": "translate",
            "translation": [0, 23.8, 0]
        }
    ]
}]

obj_file = "test.obj"
# Add the scene objects
for name, obj in scene.objects.items():
    # TODO: How to properly filter out the camera and other junk here?
    if name == "Area" or name == "Camera":
        continue
    print("Appending {} to the objects".format(name))
    objects.append({
        "name": name,
        "type": "receiver",
        "material": "white_wall",
        "geometry": {
            "type": "mesh",
            "file": obj_file,
            "model": name,
        },
        "transform": []
    })


# Save out the OBJ containing all our meshes
bpy.ops.export_scene.obj("EXEC_DEFAULT", False, filepath=filepath + "test.obj",
    axis_forward="Z", use_materials=False, use_triangles=True)

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
