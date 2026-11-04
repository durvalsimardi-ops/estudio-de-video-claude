"""Xícara 3D girando, feita só com código, no Blender em segundo plano (aula 23).

Uso (na raiz do estúdio):
  blender -b -P .claude/skills/blender-3d/xicara.py -- trabalho/xicara-3d
  blender -b -P .claude/skills/blender-3d/xicara.py -- trabalho/xicara-3d --segundos 6 --rapido

Saída: <pasta>/xicara.mp4 (1080x1920, 30 qps) e os quadros em <pasta>/quadros/.
--rapido usa menos amostras (prévia em poucos segundos; serrilha um pouco).
Precisa do ffmpeg instalado (junta os quadros no mp4).
"""
import math
import os
import shutil
import subprocess
import sys

import bpy

# ===== ARGUMENTOS (o que vem depois do "--") =====
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
if not args:
    print(__doc__)
    sys.exit(1)
PASTA = os.path.abspath(args[0])
SEGUNDOS = float(args[args.index("--segundos") + 1]) if "--segundos" in args else 4.0
RAPIDO = "--rapido" in args
QPS = 30
QUADROS = int(round(SEGUNDOS * QPS))

# ===== CORES (sRGB, como no site de cores; o Blender pede em "linear", a função converte) =====
def linear(hexa):
    """Converte '#2E6BFF' para a cor linear que o Blender usa por dentro."""
    hexa = hexa.lstrip("#")
    c = [int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]

AZUL_FUNDO = linear("#2E6BFF")
LOUCA = linear("#EEEAE3")      # branco de porcelana, levemente quente
CAFE = linear("#2B160C")       # café escuro
FAIXA = linear("#2E6BFF")      # filete azul na borda da xícara e do pires

# ===== CENA VAZIA =====
bpy.ops.wm.read_factory_settings(use_empty=True)
cena = bpy.context.scene


def material(nome, cor, aspereza=0.2):
    """Material simples: cor e quanto brilha (aspereza baixa = mais brilho)."""
    m = bpy.data.materials.new(nome)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = cor
    bsdf.inputs["Roughness"].default_value = aspereza
    return m


def torneado(nome, perfil, mat, suave=2):
    """Gira um perfil (lista de pontos raio, altura) em volta do eixo Z, como num torno de oleiro."""
    malha = bpy.data.meshes.new(nome)
    verts = [(r, 0.0, z) for r, z in perfil]
    arestas = [(i, i + 1) for i in range(len(verts) - 1)]
    malha.from_pydata(verts, arestas, [])
    obj = bpy.data.objects.new(nome, malha)
    cena.collection.objects.link(obj)
    giro = obj.modifiers.new("torno", "SCREW")      # o "torno": gira o perfil 360 graus
    giro.angle = math.tau
    giro.steps = 96
    giro.render_steps = 96
    giro.use_merge_vertices = True                   # fecha o centro (fundo da xícara)
    giro.use_normal_calculate = True
    sub = obj.modifiers.new("liso", "SUBSURF")       # arredonda as quinas
    sub.levels = suave
    sub.render_levels = suave
    malha.polygons.foreach_set("use_smooth", [True] * len(malha.polygons))
    obj.data.materials.append(mat)
    return obj


louca = material("louca", LOUCA, 0.12)
cafe = material("cafe", CAFE, 0.06)
# café liso como espelho e com pouco reflexo: aspereza alta espalha a luz e ele parece leite
cafe.node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.3
faixa = material("faixa", FAIXA, 0.25)

# ===== XÍCARA: perfil de fora (de baixo para cima) e de dentro (de cima para baixo) =====
corpo = torneado("xicara", [
    (0.00, 0.00), (0.26, 0.00), (0.30, 0.02), (0.33, 0.08),       # pé
    (0.38, 0.25), (0.44, 0.50), (0.48, 0.74), (0.50, 0.86),       # parede de fora
    (0.505, 0.89), (0.49, 0.90), (0.465, 0.88),                   # borda arredondada
    (0.455, 0.80), (0.42, 0.55), (0.36, 0.30), (0.29, 0.14),      # parede de dentro
    (0.15, 0.10), (0.00, 0.10),                                   # fundo de dentro
], louca)
corpo.location.z = 0.05

# filete azul logo abaixo da borda: um anel fino torneado
filete = torneado("filete", [(0.493, 0.80), (0.503, 0.83), (0.493, 0.86)], faixa, suave=1)
filete.location.z = 0.05

# café dentro: um disco quase na borda
bpy.ops.mesh.primitive_circle_add(vertices=96, radius=0.445, fill_type="NGON", location=(0, 0, 0.05 + 0.78))
liquido = bpy.context.active_object
liquido.name = "cafe"
liquido.data.materials.append(cafe)

# ===== ALÇA: uma curva em forma de "C" com espessura =====
curva = bpy.data.curves.new("alca", "CURVE")
curva.dimensions = "3D"
curva.bevel_depth = 0.045        # grossura da alça
curva.bevel_resolution = 6
curva.resolution_u = 24
sp = curva.splines.new("BEZIER")
pontos = [(0.42, 0, 0.78), (0.70, 0, 0.74), (0.70, 0, 0.40), (0.34, 0, 0.32)]  # pontas enterradas na parede
sp.bezier_points.add(len(pontos) - 1)
for bp, co in zip(sp.bezier_points, pontos):
    bp.co = co
    bp.handle_left_type = bp.handle_right_type = "AUTO"
alca = bpy.data.objects.new("alca", curva)
cena.collection.objects.link(alca)
alca.data.materials.append(louca)

# ===== PIRES: prato raso torneado =====
pires = torneado("pires", [
    (0.00, 0.00), (0.40, 0.00), (0.46, 0.02), (0.70, 0.07),
    (0.84, 0.12), (0.86, 0.14), (0.84, 0.15), (0.70, 0.10),
    (0.46, 0.06), (0.36, 0.05), (0.00, 0.05),
], louca)
pires.location.z = -0.02

# ===== GIRO: tudo preso num ponto vazio que dá uma volta inteira no tempo do vídeo =====
bpy.ops.object.empty_add(location=(0, 0, 0))
eixo = bpy.context.active_object
eixo.name = "giro"
for o in (corpo, filete, liquido, alca, pires):
    o.parent = eixo
# o "driver" calcula o ângulo a partir do número do quadro (sem chaves de animação)
drv = eixo.driver_add("rotation_euler", 2).driver
drv.type = "SCRIPTED"
drv.expression = f"(frame - 1) * {math.tau:.6f} / {QUADROS}"

# ===== CÂMERA: em pé (9:16), um pouco de cima =====
bpy.ops.object.camera_add(location=(0, -5.6, 2.6))
cam = bpy.context.active_object
cam.data.lens = 62
cena.camera = cam
bpy.ops.object.empty_add(location=(0, 0, 0.42))
alvo = bpy.context.active_object
alvo.name = "alvo"
mira = cam.constraints.new("TRACK_TO")      # a câmera olha sempre para o alvo
mira.target = alvo
mira.track_axis = "TRACK_NEGATIVE_Z"
mira.up_axis = "UP_Y"

# ===== LUZ DE ESTÚDIO: principal, preenchimento e contorno =====
def luz(nome, local, energia, tamanho):
    bpy.ops.object.light_add(type="AREA", location=local)
    l = bpy.context.active_object
    l.name = nome
    l.data.energy = energia
    l.data.size = tamanho
    c = l.constraints.new("TRACK_TO")
    c.target = alvo
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return l

luz("principal", (-3.0, -3.0, 4.0), 380, 3.0)
luz("preenchimento", (3.5, -2.5, 1.5), 70, 4.0)
luz("contorno", (0.5, 3.5, 3.0), 220, 2.0)

# ===== FUNDO AZUL: a câmera vê o azul exato; a luz do ambiente é cinza neutro =====
mundo = bpy.data.worlds.new("mundo")
cena.world = mundo
mundo.use_nodes = True
n = mundo.node_tree.nodes
lk = mundo.node_tree.links
n.clear()
saida = n.new("ShaderNodeOutputWorld")
mistura = n.new("ShaderNodeMixShader")
caminho = n.new("ShaderNodeLightPath")
ambiente = n.new("ShaderNodeBackground")
ambiente.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
ambiente.inputs["Strength"].default_value = 0.25
fundo = n.new("ShaderNodeBackground")
fundo.inputs["Color"].default_value = AZUL_FUNDO
fundo.inputs["Strength"].default_value = 1.0
lk.new(caminho.outputs["Is Camera Ray"], mistura.inputs["Fac"])
lk.new(ambiente.outputs["Background"], mistura.inputs[1])
lk.new(fundo.outputs["Background"], mistura.inputs[2])
lk.new(mistura.outputs["Shader"], saida.inputs["Surface"])

# ===== RENDER: EEVEE (rápido), 1080x1920, 30 qps =====
cena.render.engine = "BLENDER_EEVEE"
cena.eevee.taa_render_samples = 8 if RAPIDO else 48
cena.render.resolution_x = 1080
cena.render.resolution_y = 1920
cena.render.resolution_percentage = 100
cena.render.fps = QPS
cena.frame_start = 1
cena.frame_end = QUADROS
cena.view_settings.view_transform = "Standard"   # cor do fundo sai igual ao código #2E6BFF
cena.view_settings.look = "None"
cena.render.image_settings.file_format = "PNG"
cena.render.image_settings.color_mode = "RGB"

quadros = os.path.join(PASTA, "quadros")
if os.path.isdir(quadros):
    shutil.rmtree(quadros)
os.makedirs(quadros)
cena.render.filepath = os.path.join(quadros, "q")
bpy.ops.render.render(animation=True)

# ===== JUNTAR OS QUADROS NUM MP4 (ffmpeg) =====
mp4 = os.path.join(PASTA, "xicara.mp4")
subprocess.run([
    "ffmpeg", "-v", "error", "-y", "-framerate", str(QPS), "-start_number", "1",
    "-i", os.path.join(quadros, "q%04d.png"),
    "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    "-movflags", "+faststart", mp4,
], check=True)
print(f"ok · {QUADROS} quadros · {mp4}")
