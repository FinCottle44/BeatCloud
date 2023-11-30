#Import required Image library
import os, requests
from random import uniform
import subprocess
from PIL import Image
from binascii import a2b_base64
from . import tasks

# Basically downloads or opens image ready for use
def InitOriginal(save_path, imgUrl=None, UploadedImg=None):
    # fetch image
    if UploadedImg == None: # then assume img is being downloaded from url
        original=Image.open(requests.get(imgUrl, stream=True).raw)
    else:
        original=Image.open(UploadedImg)

    if original.mode in ("RGBA", "P"):
        original = original.convert("RGB")
    
    original.save(save_path)
    return save_path

def fromDataUrl(temp_folder, data, filename):
    binary_data=a2b_base64(data)
    path = os.path.join(temp_folder, filename)
    try:
        with open(path, 'wb') as fd:
            fd.write(binary_data)
            fd.close()
        return True, filename
    except Exception as e:
        return False, e

def create_blank_layers(path, dim):
    image = Image.new('RGBA', dim)
    image.save(path, 'PNG')
    image.close()
    print(f"No layer file so created one in temp dir")
    return path

# Video to GIF functions
def get_frames(id, vid_path, tmp_path):
    #if dur over 30s else do first few
    dur = tasks.get_duration(vid_path, tmp_path)
    out = os.path.join(tmp_path, f"{id}_bg.gif")
    dur = uniform(1, dur - 10)
    cmd = ['ffmpeg', '-ss', str(dur), '-t', '3', '-i', vid_path, '-vf', 'fps=10,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse', '-loop', '0', '-y', out]
    process = subprocess.Popen(cmd, cwd=tmp_path)
    stdout, stderr = process.communicate()
    return out
