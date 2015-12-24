# tray\_rust\_blender

A [tray\_rust](https://github.com/Twinklebear/tray_rust) plugin for Blender.

## Currently Supported Features

- Exporting static objects and keyframe animated objects to a tray_rust scene file. Note: physics animation is supported but should be baked to keyframes before exporting
- Camera (static and keyframed) exporting, FOV is also exported
- Metaball exporting, these are converted to analytic spheres
- Point and Area light location exporting (the actual emission properties are not read from Blender)
- Render settings from Cycles like resolution, samples, number of frames, framerate

## Missing Features

- Exporting materials from Blender and editing tray_rust materials. Currently you must still edit the material data in the JSON file manually
- Exporting light emission properties. It may be hard to match Cycles here but our own UI would be good
- Running tray_rust directly from Blender similar to Cycles (needs full integration + UI for a lot of stuff)
- Changing integrator settings, e.g. in pathtracer path length and such.
- Changing reconstruction filter settings

## Warnings

- Objects **must** have texture coordinates for tray_rust to read them as they're required for some derivatives in the renderer.
- If your scene doesn't have animation set the end frame equal to the start frame, otherwise tray_rust will render a ton of static frames.
- Instancing detection is a bit rough. The base object that others instance from must have the same name as the mesh that is attached to it, otherwise it will be treated as an instance and not exported properly.

