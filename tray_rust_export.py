import bpy
import math
import mathutils
import json

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
cam_mat = camera.matrix_world
print(camera.matrix_world)

transform_mat = mathutils.Matrix([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
mat = transform_mat.inverted() * cam_mat * transform_mat * mathutils.Matrix.Rotation(math.radians(90), 4, "X")
# TODO: FOV computation is not quite correct, we don't match. Is the FOV we get from Blender via
# bpy.data.camera["Camera"].angle the vertical or horizontal FOV?
camera = {
    "fov": math.degrees(bpy.data.cameras["Camera"].angle_y),
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

objects = []
obj_file = "test.obj"
# Add the scene objects
for name, obj in scene.objects.items():
    print("Appending {} to the objects, type = {}".format(name, obj.type))
    # Append all the meshes in the scene
    if obj.type == "MESH":
        obj.select = True
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
    # Convert meta balls to analytic spheres
    if obj.type == "META":
        obj.select = False
        obj_mat = transform_mat.inverted() * obj.matrix_world * transform_mat * mathutils.Matrix.Rotation(math.radians(90), 4, "X")
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
                },
                {
                    "type": "scale",
                    "scaling": [-1, 1, 1]
                }
            ]
        })
    # Export lights
    if obj.type == "LAMP":
        lamp = bpy.data.lamps[name]
        # TODO: Point lights
        if lamp.type == "POINT":
            pos, _, _ = obj.matrix_world.decompose()
            objects.append({
                "name": name,
                "type": "emitter",
                "emitter": "point",
                "emission": [0.780131, 0.780409, 0.775833, 100],
                "position": [pos[0], pos[2], pos[1]],
                "transform": []
            })
        elif lamp.type == "AREA":
            obj_mat = transform_mat.inverted() * obj.matrix_world * transform_mat * mathutils.Matrix.Rotation(math.radians(90), 4, "X")
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
                    },
                    {
                        "type": "scale",
                        "scaling": [-1, 1, 1]
                    }
                ]
            })

# Save out the OBJ containing all our meshes
bpy.ops.export_scene.obj("EXEC_DEFAULT", False, filepath=filepath + "test.obj",
    axis_forward="Z", use_materials=False, use_uvs=True, use_normals=True,
    use_triangles=True, use_selection=True)

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
