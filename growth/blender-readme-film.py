"""Blender source for the Zero Slop README product film.

The film is a deterministic, silent 24-second product demonstration. Blender
owns the physical terminal, logo, light, camera and transitions. Exact text is
supplied by the rendered xterm screen plates in ``growth/blender-screens``.

Preview a representative frame:
    Blender --background --python growth/blender-readme-film.py -- --preview

Render a PNG sequence (the bundled Blender build has no FFmpeg encoder):
    Blender --background --python growth/blender-readme-film.py -- \
      --frames /tmp/zero-slop-blender-frames

The sequence can be encoded to a silent MP4 with any H.264 encoder. The
repository's release helper uses imageio-ffmpeg when it is available.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parents[1]
SCREEN_DIR = Path(os.environ.get("ZERO_SLOP_BLENDER_SCREENS", ROOT / "growth/blender-screens"))
DEFAULT_OUTPUT = Path(os.environ.get("ZERO_SLOP_BLENDER_OUTPUT", "/tmp/zero-slop-blender-readme.mp4"))
FPS = 30
FRAMES = 720
WIDTH, HEIGHT = 1920, 1080

GOLD = (0.886, 0.647, 0.008, 1.0)  # #e2a500, display-linearised by Blender
INK = (0.012, 0.010, 0.007, 1.0)   # #12100c
RUST = (0.549, 0.078, 0.027, 1.0)  # #8c3f22
WHITE = (0.985, 0.985, 0.978, 1.0)
MUTED = (0.36, 0.34, 0.31, 1.0)


def argv():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    preview = "--preview" in args
    build_only = "--build-only" in args
    frames_dir = None
    out = DEFAULT_OUTPUT
    if "--output" in args:
        out = Path(args[args.index("--output") + 1]).expanduser().resolve()
    if "--frames" in args:
        frames_dir = Path(args[args.index("--frames") + 1]).expanduser().resolve()
    return preview, build_only, frames_dir, out


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves, bpy.data.meshes):
        for block in list(datablocks):
            if block.users == 0:
                datablocks.remove(block)


def set_input(node, name, value):
    socket = node.inputs.get(name)
    if socket is not None:
        socket.default_value = value


def principled_material(name, color, metallic=0.0, roughness=0.35, coat=0.0, noise=False):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    shader = nodes.new("ShaderNodeBsdfPrincipled")
    set_input(shader, "Base Color", color)
    set_input(shader, "Metallic", metallic)
    set_input(shader, "Roughness", roughness)
    set_input(shader, "IOR", 1.46)
    set_input(shader, "Coat Weight", coat)
    set_input(shader, "Coat Roughness", 0.22)
    links.new(shader.outputs.get("BSDF"), out.inputs.get("Surface"))
    if noise:
        tex = nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = 4.0
        tex.inputs["Detail"].default_value = 2.0
        tex.inputs["Roughness"].default_value = 0.65
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.27
        ramp.color_ramp.elements[0].color = (roughness * 0.80,) * 3 + (1.0,)
        ramp.color_ramp.elements[1].position = 0.73
        ramp.color_ramp.elements[1].color = (roughness * 1.16,) * 3 + (1.0,)
        links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], shader.inputs["Roughness"])
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = 0.035
        bump.inputs["Distance"].default_value = 0.035
        links.new(tex.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], shader.inputs["Normal"])
    return mat


def emission_material(name, color, strength=1.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    set_input(emission, "Color", color)
    set_input(emission, "Strength", strength)
    links.new(emission.outputs.get("Emission"), out.inputs.get("Surface"))
    return mat


def beveled_cube(name, dimensions, location, material, bevel=0.12, segments=5, parent=None):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        mod = obj.modifiers.new("Soft physical edge", "BEVEL")
        mod.width = bevel
        mod.segments = segments
        mod.limit_method = "ANGLE"
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    if parent:
        obj.parent = parent
    return obj


def text_object(name, text, location, size, material, parent=None, align="LEFT"):
    curve = bpy.data.curves.new(name, type="FONT")
    curve.body = text
    curve.align_x = align
    curve.align_y = "CENTER"
    curve.size = size
    curve.space_line = 1.18
    curve.extrude = 0.006
    curve.bevel_depth = 0.002
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.radians(90), 0, 0)
    obj.data.materials.append(material)
    if hasattr(obj, "visible_shadow"):
        obj.visible_shadow = False
    if parent:
        obj.parent = parent
    return obj


def keyframe(obj, frame, location=None, rotation=None, scale=None):
    if location is not None:
        obj.location = location
        obj.keyframe_insert(data_path="location", frame=frame)
    if rotation is not None:
        obj.rotation_euler = rotation
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)
    if scale is not None:
        obj.scale = scale if isinstance(scale, Vector) else (scale, scale, scale)
        obj.keyframe_insert(data_path="scale", frame=frame)


def soften_animation(obj):
    if not obj.animation_data or not obj.animation_data.action:
        return
    # Blender 5.2's layered Action API no longer exposes ``fcurves`` on every
    # action. Keyframe insertion already defaults to Bezier, so gracefully
    # skip this optional polish pass when the legacy collection is absent.
    fcurves = getattr(obj.animation_data.action, "fcurves", None)
    if fcurves is None:
        return
    for fcurve in fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"
            point.handle_left_type = "AUTO_CLAMPED"
            point.handle_right_type = "AUTO_CLAMPED"


def look_at(obj, target):
    direction = Vector(target) - obj.location
    obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def screen_material(plates):
    mat = bpy.data.materials.new("Verified xterm screen · opaque and readable")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    set_input(emission, "Strength", 0.72)
    first = nodes.new("ShaderNodeTexImage")
    second = nodes.new("ShaderNodeTexImage")
    first.interpolation = "Linear"
    second.interpolation = "Linear"
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs[0].default_value = 0.0
    links.new(first.outputs["Color"], mix.inputs[1])
    links.new(second.outputs["Color"], mix.inputs[2])
    links.new(mix.outputs["Color"], emission.inputs["Color"])
    links.new(emission.outputs["Emission"], out.inputs["Surface"])
    images = {name: bpy.data.images.load(str(path), check_existing=True) for name, path in plates.items()}
    first.image = images["install"]
    second.image = images["install"]
    return mat, first, second, mix, images


def screen_state(frame):
    # State boundaries are selected around real xterm captures. The short blend
    # masks the image swap while preserving a stable reading interval.
    states = [(1, "install"), (84, "assistant"), (150, "source"), (255, "flags"), (390, "edit"), (510, "checks")]
    current = states[0]
    for state in states:
        if frame >= state[0]:
            current = state
    index = states.index(current)
    if index == len(states) - 1:
        return current[1], current[1], 0.0
    next_frame, next_name = states[index + 1]
    if frame >= next_frame - 6:
        amount = max(0.0, min(1.0, (frame - (next_frame - 6)) / 12.0))
        return current[1], next_name, amount
    return current[1], current[1], 0.0


def build_world(scene):
    world = bpy.data.worlds.new("Zero Slop white studio") if not bpy.data.worlds else bpy.data.worlds[0]
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    # A deliberate white studio: the README embed reads as a clean product
    # plate rather than a dark CG vignette. The floor still carries the soft
    # contact shadow that gives the terminal physical weight.
    bg.inputs["Color"].default_value = (1.0, 1.0, 0.985, 1.0)
    bg.inputs["Strength"].default_value = 0.62
    floor_mat = principled_material("Warm white cyc", WHITE, roughness=0.42, noise=True)
    floor = beveled_cube("Ground plane", (60, 60, 0.12), (0, 2.0, -0.18), floor_mat, bevel=0.06, segments=3)
    floor.parent = None

    backdrop_mat = emission_material("White cyclorama backdrop", (1.0, 1.0, 0.985, 1.0), 0.82)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 10.0, 10.0), rotation=(math.radians(90), 0, 0))
    backdrop = bpy.context.object
    backdrop.name = "Seamless white backdrop"
    backdrop.dimensions = (60, 30, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    backdrop.data.materials.append(backdrop_mat)

    def area(name, location, energy, size, color):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        look_at(light, (0, 0, 3.4))
        return light

    area("Large soft key", (-8.0, -10.0, 15.0), 1300, 8.0, (1.0, 0.93, 0.82))
    area("Cool fill", (10.0, -4.0, 10.0), 900, 6.0, (0.80, 0.88, 1.0))
    area("Edge reflection", (0.0, 7.0, 13.0), 1100, 5.0, (1.0, 0.98, 0.92))


def build_scene():
    clear_scene()
    scene = bpy.context.scene
    # Blender 5.2 exposes the realtime renderer as BLENDER_EEVEE (the
    # internal Eevee Next engine remains the implementation detail).
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.render.use_file_extension = True
    scene.view_settings.look = "Medium High Contrast"
    build_world(scene)

    camera_data = bpy.data.cameras.new("Product camera")
    camera = bpy.data.objects.new("Product camera", camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 52
    camera.data.sensor_width = 36
    camera.location = (0.0, -29.0, 7.4)
    look_at(camera, (0, 0, 4.2))
    keyframe(camera, 1, location=(0.0, -29.0, 7.4))
    keyframe(camera, 120, location=(0.0, -28.0, 7.15))
    keyframe(camera, 390, location=(0.0, -27.6, 7.05))
    keyframe(camera, 560, location=(0.0, -28.7, 7.25))
    keyframe(camera, FRAMES, location=(0.0, -29.0, 7.4))
    soften_animation(camera)

    gold = principled_material("Supplied gold lacquer", GOLD, metallic=0.18, roughness=0.28, coat=0.30, noise=True)
    ink = principled_material("Mark ink", INK, metallic=0.05, roughness=0.30, coat=0.14)
    rust = principled_material("Mark rust enamel", RUST, metallic=0.10, roughness=0.25, coat=0.24)
    metal = principled_material("Anodized terminal shell", (0.45, 0.48, 0.51, 1), metallic=0.84, roughness=0.22, coat=0.18, noise=True)
    porcelain = principled_material("Porcelain bezel", (0.90, 0.90, 0.88, 1), metallic=0.06, roughness=0.26, coat=0.22, noise=True)
    text_ink = emission_material("Crisp ink typography", (0.018, 0.015, 0.012, 1), 0.7)
    text_muted = emission_material("Crisp muted typography", (0.30, 0.28, 0.25, 1), 0.7)
    text_rust = emission_material("Crisp rust typography", (0.42, 0.055, 0.018, 1), 0.8)

    # The original mark is a physically thick tile with individually modeled
    # Z and slash layers, keeping the silhouette recognizable in motion.
    logo = bpy.data.objects.new("Supplied Zero Slop mark", None)
    bpy.context.collection.objects.link(logo)
    tile = beveled_cube("Gold mark tile", (5.7, 0.66, 5.7), (0, 0, 0), gold, bevel=0.42, segments=8, parent=logo)
    top = beveled_cube("Z top", (3.12, 0.14, 0.56), (0, -0.43, 0.92), ink, bevel=0.06, segments=4, parent=logo)
    bottom = beveled_cube("Z bottom", (3.12, 0.14, 0.56), (0, -0.43, -0.92), ink, bevel=0.06, segments=4, parent=logo)
    diagonal = beveled_cube("Z diagonal", (3.72, 0.14, 0.56), (0, -0.43, 0), ink, bevel=0.06, segments=4, parent=logo)
    diagonal.rotation_euler[1] = math.radians(-43)
    slash = beveled_cube("Rust editorial slash", (4.45, 0.18, 0.40), (0, -0.52, 0.0), rust, bevel=0.19, segments=8, parent=logo)
    slash.rotation_euler[1] = math.radians(-8.05)
    logo.location = (-5.35, 0, 3.00)
    logo.rotation_euler = (math.radians(2), math.radians(-12), math.radians(-2))
    logo.scale = (0.93, 0.93, 0.93)
    keyframe(logo, 1, location=(-5.35, 0, 3.00), rotation=logo.rotation_euler, scale=0.82)
    keyframe(logo, 90, location=(-5.45, 0, 2.95), rotation=(math.radians(1), math.radians(-8), math.radians(-1)), scale=0.78)
    keyframe(logo, 390, location=(-5.0, 0, 4.05), rotation=(math.radians(1), math.radians(-7), math.radians(-1)), scale=0.76)
    keyframe(logo, 560, location=(-5.25, 0, 4.05), rotation=(math.radians(1), math.radians(-5), math.radians(-1)), scale=0.68)
    keyframe(logo, FRAMES, location=(-5.35, 0, 4.05), rotation=(math.radians(1), math.radians(-4), math.radians(-1)), scale=0.67)
    soften_animation(logo)

    terminal = bpy.data.objects.new("Physical terminal", None)
    bpy.context.collection.objects.link(terminal)
    shell = beveled_cube("Terminal shell", (14.3, 0.84, 6.18), (0, 0, 0), metal, bevel=0.30, segments=8, parent=terminal)
    bezel = beveled_cube("Ceramic screen bezel", (13.72, 0.18, 5.64), (0, -0.48, 0), porcelain, bevel=0.18, segments=6, parent=terminal)
    screen_back = beveled_cube("Screen recess", (13.42, 0.10, 5.36), (0, -0.59, 0), ink, bevel=0.14, segments=5, parent=terminal)
    plates = {name: SCREEN_DIR / f"{name}.png" for name in ("install", "assistant", "source", "flags", "edit", "checks")}
    missing = [str(path) for path in plates.values() if not path.exists()]
    if missing:
        raise RuntimeError("Missing xterm plate(s): " + ", ".join(missing))
    mat, tex_a, tex_b, mix, images = screen_material(plates)
    bpy.ops.mesh.primitive_plane_add(size=2, location=(0, -0.67, 0), rotation=(math.radians(90), 0, 0))
    screen = bpy.context.object
    screen.name = "Exact xterm renderer screen"
    screen.dimensions = (13.38, 5.30, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    screen.data.materials.append(mat)
    screen.parent = terminal
    for poly in screen.data.polygons:
        poly.use_smooth = True

    # Three restrained window dots complete the physical housing without adding
    # fake interface controls over the real xterm content.
    dot_mat = principled_material("Window control metal", (0.70, 0.70, 0.68, 1), metallic=0.4, roughness=0.30)
    for x in (-6.15, -5.82, -5.49):
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.075, depth=0.025, location=(x, -0.57, 2.73), rotation=(math.radians(90), 0, 0))
        dot = bpy.context.object
        dot.name = "Window control"
        dot.data.materials.append(dot_mat)
        dot.parent = terminal

    terminal.location = (14.8, 0, 4.2)
    terminal.rotation_euler = (math.radians(1), math.radians(2), math.radians(4))
    terminal.scale = (0.90, 0.90, 0.90)
    keyframe(terminal, 1, location=(14.8, 0, 4.2), rotation=terminal.rotation_euler, scale=0.90)
    keyframe(terminal, 55, location=(8.0, 0, 4.2), rotation=(math.radians(0.5), math.radians(1), math.radians(2)), scale=0.90)
    keyframe(terminal, 105, location=(1.2, 0, 4.2), rotation=(0, 0, 0), scale=0.90)
    keyframe(terminal, 390, location=(1.2, 0, 4.2), rotation=(0, 0, 0), scale=0.90)
    keyframe(terminal, 560, location=(3.1, 0, 4.15), rotation=(0, math.radians(-1), math.radians(-3)), scale=0.73)
    keyframe(terminal, FRAMES, location=(3.2, 0, 4.15), rotation=(0, math.radians(-1), math.radians(-3)), scale=0.72)
    soften_animation(terminal)

    # Typography is deterministic geometry, kept separate from the exact screen
    # plate. It stays crisp while the housing receives physical reflections.
    header = text_object("Header", "Zero Slop in your terminal.", (-8.15, -0.72, 8.42), 0.53, text_ink)
    hero = text_object("Hero title", "Zero Slop", (-8.15, -0.72, 7.18), 1.13, text_ink)
    sub = text_object("Hero subtitle", "Find AI-sounding writing.\nKeep the source intact.", (-8.15, -0.72, 5.98), 0.36, text_muted)
    # Let the intro read for a beat, then move it out of the way along the same
    # direction as the terminal's handoff.
    keyframe(hero, 1, location=(-8.15, -0.72, 7.18), scale=1.0)
    keyframe(hero, 92, location=(-8.15, -0.72, 7.18), scale=1.0)
    keyframe(hero, 124, location=(-8.15, -0.72, 7.18), scale=0.001)
    keyframe(hero, 160, location=(-8.15, -0.72, 7.18), scale=0.001)
    keyframe(hero, FRAMES, location=(-8.15, -0.72, 7.18), scale=0.001)
    keyframe(sub, 1, location=(-8.15, -0.72, 5.98), scale=1.0)
    keyframe(sub, 92, location=(-8.15, -0.72, 5.98), scale=1.0)
    keyframe(sub, 124, location=(-8.15, -0.72, 5.98), scale=0.001)
    keyframe(sub, 160, location=(-8.15, -0.72, 5.98), scale=0.001)
    keyframe(sub, FRAMES, location=(-8.15, -0.72, 5.98), scale=0.001)
    keyframe(header, 1, location=(-8.15, -0.72, 8.42), scale=1.0)
    keyframe(header, 92, location=(-8.15, -0.72, 8.42), scale=1.0)
    keyframe(header, 124, location=(-8.15, -0.72, 8.42), scale=0.001)
    keyframe(header, 160, location=(-8.15, -0.72, 8.42), scale=0.001)
    keyframe(header, FRAMES, location=(-8.15, -0.72, 8.42), scale=0.001)
    soften_animation(hero)
    soften_animation(sub)

    cta_left_label = text_object("MCP label", "Optional hosted MCP", (-8.05, -0.72, 2.05), 0.28, text_muted)
    cta_left = text_object("MCP endpoint", "https://mcp.zero-slop.ai/mcp", (-8.05, -0.72, 1.48), 0.48, text_rust)
    cta_right_label = text_object("Browser label", "Or try the free browser editor", (2.15, -0.72, 2.05), 0.28, text_muted)
    cta_right = text_object("Browser editor", "zero-slop.ai/try", (2.15, -0.72, 1.48), 0.52, text_ink)
    for obj in (cta_left_label, cta_left, cta_right_label, cta_right):
        keyframe(obj, 1, scale=0.001)
        keyframe(obj, 555, scale=0.001)
        keyframe(obj, 620, scale=1.0)
        keyframe(obj, FRAMES, scale=1.0)
        soften_animation(obj)
    footer = text_object("Footer", "Reconstructed skill session · timing edited for readability.", (-8.05, -0.72, 0.55), 0.20, text_muted)
    domain = text_object("Domain", "zero-slop.ai", (7.15, -0.72, 0.55), 0.20, text_muted)
    for obj in (footer, domain):
        keyframe(obj, 1, scale=0.001)
        keyframe(obj, 500, scale=0.001)
        keyframe(obj, 560, scale=1.0)
        keyframe(obj, FRAMES, scale=1.0)
        soften_animation(obj)

    # One tiny reflection card sweeps over the metal during the physical handoff.
    reflection = beveled_cube("Controlled reflection", (0.18, 0.03, 6.0), (-7.0, -0.88, 4.2), porcelain, bevel=0.05, segments=3)
    reflection.scale = (1.0, 1.0, 1.0)
    reflection.data.materials[0].node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    # Keep the card subtle and behind the screen plane; it reads as a soft edge
    # glint, not a decorative wipe.
    keyframe(reflection, 1, location=(-8.2, -0.88, 4.2), scale=0.35)
    keyframe(reflection, 104, location=(8.2, -0.88, 4.2), scale=0.35)
    keyframe(reflection, 130, location=(8.2, -0.88, 4.2), scale=0.001)
    keyframe(reflection, FRAMES, location=(8.2, -0.88, 4.2), scale=0.001)
    soften_animation(reflection)

    def update_screen(scene):
        a, b, amount = screen_state(scene.frame_current)
        tex_a.image = images[a]
        tex_b.image = images[b]
        mix.inputs[0].default_value = amount

    # Avoid duplicate handlers when the script is rerun from Blender's console.
    handlers = bpy.app.handlers.frame_change_pre
    handlers[:] = [handler for handler in handlers if getattr(handler, "__name__", "") != "update_screen"]
    handlers.append(update_screen)
    update_screen(scene)
    scene.frame_start = 1
    scene.frame_end = FRAMES
    return scene


def configure_output(scene, output, preview, frames_dir=None):
    if preview:
        scene.frame_set(390)
        scene.render.resolution_percentage = 50
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(output.with_suffix(".png"))
    elif frames_dir is not None:
        frames_dir.mkdir(parents=True, exist_ok=True)
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "PNG"
        scene.render.filepath = str(frames_dir / "frame-####")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        scene.render.resolution_percentage = 100
        scene.render.image_settings.file_format = "FFMPEG"
        scene.render.ffmpeg.format = "MPEG4"
        scene.render.ffmpeg.codec = "H264"
        scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
        scene.render.ffmpeg.audio_codec = "NONE"
        scene.render.ffmpeg.audio_bitrate = 0
        scene.render.ffmpeg.gopsize = 30
        scene.render.filepath = str(output)


def main():
    preview, build_only, frames_dir, output = argv()
    scene = build_scene()
    source = ROOT / "growth/blender-readme-film.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    if build_only:
        print(f"Wrote Blender scene: {source}")
        return
    configure_output(scene, output, preview, frames_dir)
    if preview:
        bpy.ops.render.render(write_still=True)
        print(f"Wrote Blender preview: {scene.render.filepath}")
    elif frames_dir is not None:
        bpy.ops.render.render(animation=True)
        print(f"Wrote Blender PNG sequence: {frames_dir}")
    else:
        raise RuntimeError("This Blender build has no FFmpeg encoder; use --frames and encode the PNG sequence externally.")


if __name__ == "__main__":
    main()
