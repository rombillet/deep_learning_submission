"""
Chess FEN Parser - Optimized for High Res + Render Region

Strategy:
1. Clear animation data
2. Parse target FEN
3. Move pieces
4. Render ONLY the board region (faster) at High Res
"""

import bpy
import math
from mathutils import Vector, Matrix
import sys
import argparse

# ==========================
# CONFIG
# ==========================
REAL_BOARD_SIZE = 0.53
DESIRED_CAMERA_HEIGHT = 2
DESIRED_ANGLE_DEGREES = 25
LENS = 26
# הרזולוציה והדגימות ייקבעו ע"י הארגומנטים מהסקריפט הראשי
RES = 1024 
SAMPLES = 128
OUT_DIR = "//renders"

def get_board_info():
    """Get board dimensions"""
    plane = bpy.data.objects.get("Black & white")
    frame = bpy.data.objects.get("Outer frame")
    
    if not plane or not frame: return None

    plane_pts = [plane.matrix_world @ Vector(v) for v in plane.bound_box]
    plane_min = Vector((min(p.x for p in plane_pts), min(p.y for p in plane_pts), min(p.z for p in plane_pts)))
    plane_max = Vector((max(p.x for p in plane_pts), max(p.y for p in plane_pts), max(p.z for p in plane_pts)))
    plane_size = max(plane_max.x - plane_min.x, plane_max.y - plane_min.y)
    square_size = plane_size / 8
    
    frame_pts = [frame.matrix_world @ Vector(v) for v in frame.bound_box]
    frame_min = Vector((min(p.x for p in frame_pts), min(p.y for p in frame_pts), min(p.z for p in frame_pts)))
    frame_max = Vector((max(p.x for p in frame_pts), max(p.y for p in frame_pts), max(p.z for p in frame_pts)))
    center = (frame_min + frame_max) / 2
    board_size = max(frame_max.x - frame_min.x, frame_max.y - frame_min.y)
    
    scale_factor = board_size / REAL_BOARD_SIZE
    
    return {
        'square_size': square_size,
        'plane_min': plane_min,
        'plane_max': plane_max,
        'center': center,
        'scale_factor': scale_factor,
    }

def position_to_square(pos, board_info):
    square_size = board_info['square_size']
    plane_min = board_info['plane_min']
    plane_max = board_info['plane_max']
    
    file_idx = 7 - int((pos.x - plane_min.x) / square_size)
    file_idx = max(0, min(7, file_idx))
    file_letter = chr(ord('a') + file_idx)
    rank_idx = int((plane_max.y - pos.y) / square_size)
    rank_idx = max(0, min(7, rank_idx))
    rank_number = rank_idx + 1
    
    return f"{file_letter}{rank_number}"

def detect_starting_positions(board_info):
    print("\n" + "="*70)
    print("DETECTING STARTING POSITIONS")
    print("="*70)
    
    pieces = {}
    
    for obj in bpy.data.objects:
        if obj.type != 'MESH': continue
        
        # === ניקוי אנימציה ===
        if obj.animation_data:
            obj.animation_data_clear()

        name = obj.name
        piece_type = None
        
        if name in ['B', 'C', 'D', 'E', 'F', 'G', 'H', 'A(texture)']: piece_type = 'P'
        elif name in ['B.001', 'C.001', 'D.001', 'E.001', 'F.001', 'G.001', 'H.001', 'A(textures)']: piece_type = 'p'
        elif 'rook' in name.lower(): piece_type = 'R' if 'white' in name.lower() else 'r'
        elif 'knight' in name.lower(): piece_type = 'N' if 'white' in name.lower() else 'n'
        elif 'bitshop' in name.lower() or 'bishop' in name.lower(): piece_type = 'B' if 'white' in name.lower() else 'b'
        elif 'queen' in name.lower(): piece_type = 'Q' if 'white' in name.lower() else 'q'
        elif 'king' in name.lower(): piece_type = 'K' if 'white' in name.lower() else 'k'
        
        if piece_type:
            square = position_to_square(obj.location, board_info)
            pieces[name] = {'square': square, 'piece_type': piece_type, 'start_pos': obj.location.copy()}
            print(f"  {name:20s} → {square:4s} ({piece_type})")
    
    print(f"\n✓ Detected {len(pieces)} pieces")
    return pieces

def parse_fen(fen):
    board_fen = fen.split()[0]
    ranks = board_fen.split('/')
    position = {}
    for rank_idx, rank in enumerate(ranks):
        file_idx = 0
        board_rank = 8 - rank_idx
        for char in rank:
            if char.isdigit(): file_idx += int(char)
            else:
                file_letter = chr(ord('a') + file_idx)
                square = f"{file_letter}{board_rank}"
                position[square] = char
                file_idx += 1
    return position

def apply_fen(fen, starting_pieces, board_info):
    print("\nAPPLYING FEN: " + fen)
    target_position = parse_fen(fen)
    square_size = board_info['square_size']
    
    available_pieces = {}
    for piece_name, info in starting_pieces.items():
        key = (info['square'], info['piece_type'])
        if key not in available_pieces: available_pieces[key] = []
        available_pieces[key].append(piece_name)
    
    pieces_used = set()
    
    for target_square, piece_type in target_position.items():
        candidates = []
        for piece_name, info in starting_pieces.items():
            if info['piece_type'] == piece_type and piece_name not in pieces_used:
                from_square = info['square']
                from_file = ord(from_square[0]) - ord('a')
                from_rank = int(from_square[1]) - 1
                to_file = ord(target_square[0]) - ord('a')
                to_rank = int(target_square[1]) - 1
                distance = abs(to_file - from_file) + abs(to_rank - from_rank)
                candidates.append((distance, piece_name, from_square))
        
        if not candidates: continue 
        
        candidates.sort()
        _, piece_name, from_square = candidates[0]
        
        obj = bpy.data.objects.get(piece_name)
        if obj:
            # Force update scene
            bpy.context.view_layer.update()
            
            from_file = ord(from_square[0]) - ord('a')
            from_rank = int(from_square[1]) - 1
            to_file = ord(target_square[0]) - ord('a')
            to_rank = int(target_square[1]) - 1
            
            file_diff = to_file - from_file
            rank_diff = to_rank - from_rank
            
            obj.location.x -= file_diff * square_size
            obj.location.y -= rank_diff * square_size
            
            obj.hide_render = False
            obj.hide_viewport = False
            pieces_used.add(piece_name)

    # Hide unused
    for piece_name in starting_pieces.keys():
        if piece_name not in pieces_used:
            obj = bpy.data.objects.get(piece_name)
            if obj:
                obj.hide_render = True
                obj.hide_viewport = True

def render_all_views(board_info, view='black'):
    print("\n" + "="*70)
    print(f"RENDERING ({view.upper()} VIEW)")
    print("="*70)
    
    center = board_info['center']
    scale_factor = board_info['scale_factor']
    
    camera_height = DESIRED_CAMERA_HEIGHT * scale_factor
    angle_radians = math.radians(DESIRED_ANGLE_DEGREES)
    
    # --- RENDER REGION OPTIMIZATION (החלק החדש והחשוב) ---
    scene = bpy.context.scene
    scene.render.use_border = True
    scene.render.use_crop_to_border = False 
    
    # חיתוך סביב המרכז (מותאם לקואורדינטות שלך)
    scene.render.border_min_x = 0.35
    scene.render.border_max_x = 0.65
    scene.render.border_min_y = 0.35
    scene.render.border_max_y = 0.65
    # ----------------------------------

    # Clean cameras
    for obj in bpy.data.objects:
        if obj.type == "CAMERA": bpy.data.objects.remove(obj, do_unlink=True)
    
    # Lighting
    if not any(o.type == "LIGHT" for o in bpy.data.objects):
        light_height = center.z + camera_height * 2
        bpy.ops.object.light_add(type="SUN", location=(center.x, center.y, light_height))
        bpy.context.active_object.data.energy = 3.0
    
    # Settings
    scene.render.engine = "CYCLES"
    scene.cycles.samples = SAMPLES
    scene.render.resolution_x = RES
    scene.render.resolution_y = RES
    scene.render.image_settings.file_format = 'PNG'
    try: scene.cycles.device = 'GPU'
    except: pass
    
    camera_z = center.z + camera_height
    
    # Only Overhead camera
    views = [((center.x, center.y, camera_z), "1_overhead", True)]
    z_rotation_offset = math.radians(180) if view == 'white' else 0
    
    for location, name, point_at_center in views:
        print(f"\nRendering: {name}")
        bpy.ops.object.camera_add(location=location)
        cam = bpy.context.active_object
        
        if point_at_center:
            direction = center - cam.location
            cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        else:
            cam.rotation_euler = (0, 0, 0)
        
        cam.rotation_euler.z += z_rotation_offset
        cam.data.lens = LENS
        
        bpy.context.scene.camera = cam
        bpy.context.scene.render.filepath = f"{OUT_DIR}/{name}.png"
        bpy.ops.render.render(write_still=True)
        print(f"  ✓ Saved: {name}.png")
        bpy.data.objects.remove(cam, do_unlink=True)

def main():
    argv = sys.argv
    if "--" in argv: argv = argv[argv.index("--") + 1:]
    else: argv = []
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--fen', type=str, default="rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR")
    parser.add_argument('--resolution', type=int, default=800)
    parser.add_argument('--samples', type=int, default=128)
    parser.add_argument('--view', type=str, default='black', choices=['white', 'black'])
    args = parser.parse_args(argv)
    
    global RES, SAMPLES, OUT_DIR
    RES = args.resolution
    SAMPLES = args.samples
    OUT_DIR = "./renders"

    board_info = get_board_info()
    if not board_info: return

    # --- התיקון שהיה חסר בקוד המקוצר (סיבוב הלוח) ---
    plane = bpy.data.objects.get("Black & white")
    if plane:
        frame = bpy.data.objects.get("Outer frame")
        frame_pts = [frame.matrix_world @ Vector(v) for v in frame.bound_box]
        frame_min = Vector((min(p.x for p in frame_pts), min(p.y for p in frame_pts), min(p.z for p in frame_pts)))
        frame_max = Vector((max(p.x for p in frame_pts), max(p.y for p in frame_pts), max(p.z for p in frame_pts)))
        center = (frame_min + frame_max) / 2
        
        original_pos = plane.location.copy()
        offset = original_pos - center
        plane.rotation_euler.z = math.radians(90)
        rot_matrix = Matrix.Rotation(math.radians(90), 3, 'Z')
        rotated_offset = rot_matrix @ offset
        plane.location = center + rotated_offset
    # -----------------------------------------------

    starting_pieces = detect_starting_positions(board_info)
    apply_fen(args.fen, starting_pieces, board_info)
    render_all_views(board_info, view=args.view)

if __name__ == "__main__":
    main()