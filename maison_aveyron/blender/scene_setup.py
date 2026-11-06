"""World (physical sky), sun, camera and render settings."""
import math
import bpy
from mathutils import Vector
from lib import NT

# Golden hour: sun low in the west-north-west (summer evening in Aveyron)
SUN_AZ = math.radians(298.0)      # compass azimuth (0 = +Y north, 90 = +X east)
SUN_EL = math.radians(5.5)


def sun_vector():
    """Unit vector pointing *towards* the sun."""
    return Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))


def setup_world(strength=1.0):
    w = bpy.data.worlds.new('sky')
    bpy.context.scene.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    s = NT(w.node_tree)
    sky = s.node('ShaderNodeTexSky', sky_type='MULTIPLE_SCATTERING')
    sky.sun_disc = False
    sky.sun_elevation = SUN_EL
    # Blender's sky rotation: 0 => sun towards -Y ; we want compass az
    sky.sun_rotation = math.radians(360.0) - SUN_AZ + math.radians(180.0)
    sky.altitude = 600.0
    sky.air_density = 1.0
    sky.aerosol_density = 2.2
    sky.ozone_density = 1.0
    bg = s.node('ShaderNodeBackground', ins={'Strength': strength})
    s.t.links.new(sky.outputs[0], bg.inputs[0])
    out = s.node('ShaderNodeOutputWorld')
    s.t.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


def setup_sun(strength=4.0):
    ld = bpy.data.lights.new('sun', 'SUN')
    ld.energy = strength
    ld.angle = math.radians(0.55)
    ld.color = (1.0, 0.60, 0.33)
    ob = bpy.data.objects.new('sun', ld)
    bpy.context.scene.collection.objects.link(ob)
    d = -sun_vector()                        # light travels along -sun
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def setup_camera(loc, target, lens=24.0, shift_x=0.0, shift_y=0.0, pano=False):
    cd = bpy.data.cameras.new('cam')
    if pano:
        cd.type = 'PANO'
        try:
            cd.panorama_type = 'EQUIRECTANGULAR'
        except Exception:
            cd.cycles.panorama_type = 'EQUIRECTANGULAR'
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.sensor_height = 24.0
    cd.sensor_fit = 'HORIZONTAL'
    cd.shift_x, cd.shift_y = shift_x, shift_y
    cd.clip_start = 0.1
    cd.clip_end = 30000.0
    ob = bpy.data.objects.new('cam', cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    # level camera (vertical lines stay vertical): only yaw
    dx, dy = target[0] - loc[0], target[1] - loc[1]
    yaw = math.atan2(dy, dx) - math.pi / 2
    pitch = math.radians(90.0) + math.atan2(target[2] - loc[2], math.hypot(dx, dy))
    ob.rotation_euler = (pitch, 0.0, yaw)
    bpy.context.scene.camera = ob
    return ob


def render_settings(res=(1800, 1200), samples=256, path='render.exr', noise=0.015, passes=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = noise
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.cycles.max_bounces = 8
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transmission_bounces = 6
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.volume_bounces = 0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 8.0
    sc.cycles.blur_glossy = 1.0
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Base Contrast'
    sc.view_settings.exposure = 0.0
    sc.render.use_persistent_data = False
    sc.render.threads_mode = 'AUTO'
    try:
        sc.cycles_curves.shape = 'RIBBONS'
        sc.cycles_curves.subdivisions = 2
    except Exception:
        pass
    vl = sc.view_layers[0]
    if passes:
        vl.use_pass_z = True
        vl.use_pass_position = True
        vl.use_pass_environment = True
        sc.render.film_transparent = True
    st = sc.render.image_settings
    if path.endswith('.exr'):
        if passes:
            try:
                st.media_type = 'MULTI_LAYER_IMAGE'
            except Exception:
                pass
        try:
            st.file_format = 'OPEN_EXR_MULTILAYER' if passes else 'OPEN_EXR'
        except TypeError:
            st.file_format = 'OPEN_EXR'
        st.color_depth = '32'
        st.exr_codec = 'ZIP'
    else:
        st.file_format = 'PNG'
        st.color_depth = '8'
    sc.render.filepath = path
