import atexit
import os, boto3, subprocess, json, shutil
from urllib.parse import quote_plus
from PIL import Image, ImageFilter, ImageFont, ImageDraw
from cv2 import VideoCapture, CAP_PROP_FRAME_WIDTH, CAP_PROP_FRAME_HEIGHT
import requests
from . import ImageTools, models, yt_upload
from .db import BC_Table
import shotstack_sdk as shotstack
from shotstack_sdk.api import edit_api

### Celery setup
from celery import Celery
from celery.backends import dynamodb
msg_aws_id = quote_plus(os.environ['AWS_MSG_ACCESS_KEY_ID'])
msg_aws_key = quote_plus(os.environ['AWS_MSG_SECRET_ACCESS_KEY'])
c_app = Celery('BeatCloud', broker=f"sqs://{msg_aws_id}:{msg_aws_key}@")
c_app.conf.broker_transport_options = {
    'region': 'eu-west-2',
    'polling_interval': 10
}
read_credits = write_credits = 1 
c_app.conf.result_backend = f"dynamodb://{os.environ['AWS_DB_ACCESS_KEY_ID']}:{os.environ['AWS_DB_SECRET_ACCESS_KEY']}@eu-west-2/celery?read={read_credits}&write={write_credits}"
c_app.conf.task_default_queue = 'preview'
c_app.conf.task_routes = {
    'preview.*': {'queue':'preview'},
    'process.*': {'queue':'process'}
}

# Font caching (reduces s3 requests)
font_cache_dir = '/app/instance/fontcache'
os.makedirs(font_cache_dir, exist_ok=True)

### S3 setup
S3_REGION = 'eu-west-2'
S3_BUCKET = 'beatcloud-sandbox'
# S3_BUCKET = 'beatcloud-production'
S3_UPLOAD_PREFIX = 'media'
S3_ASSET_PREFIX = 'bc_assets'
S3_CLIP_PREFIX = 'clip_assets'
s3 = boto3.client('s3',               
    aws_access_key_id=os.environ['AWS_S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_S3_SECRET_ACCESS_KEY'],
    region_name=S3_REGION
)

###### RENDERING SETUP!!!
CHOSEN_SERVICE = "creatomate"
### ShotStack Setup
## Keys
 # Development
# SHOTSTACK_HOST_URL = 'https://api.shotstack.io/stage'
# SHOTSTACK_KEY_TYPE = 'DeveloperKey'
# SHOTSTACK_API_KEY = os.environ.get('SHOTSTACK_API_STAGE_KEY')
 # Production
SHOTSTACK_HOST_URL = 'https://api.shotstack.io/v1'
SHOTSTACK_KEY_TYPE = 'DeveloperKey'
SHOTSTACK_API_KEY = os.environ.get('SHOTSTACK_API_PROD_KEY')
##
SS_conf = shotstack.Configuration(host=SHOTSTACK_HOST_URL)
SS_conf.api_key[SHOTSTACK_KEY_TYPE] = SHOTSTACK_API_KEY
SS_api_client = shotstack.ApiClient(SS_conf)
SS_api_instance = edit_api.EditApi(SS_api_client)
atexit.register(lambda: SS_api_client.close())
### Creatomate setup
CREATOMATE_URL = 'https://api.creatomate.com/v1/renders'
CREATOMATE_API_KEY = os.environ.get('CREATOMATE_API_KEY')

### DynamoDB Setup
# Database setup for progress logging etc (NOT MESSAGE RESULT BACKEND)
dynamodb = boto3.resource('dynamodb',               
    aws_access_key_id=os.environ['AWS_DB_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_DB_SECRET_ACCESS_KEY'],
    region_name='eu-west-2'
)
table_name = 'beatcloud'
beatcloud_db = BC_Table(dynamodb)
exists = beatcloud_db.exists(table_name)
if not exists:
    print(f"\nCreating table {table_name}...")
    beatcloud_db.create_table(table_name)
    print(f"\nCreated table {beatcloud_db.table.name}.") 



#########################################################################################################
## Preview tasks
#########################################################################################################
@c_app.task(name="preview.CreateBG", bind=True)
def CreateBG(self, v_id, blur, load_path, dim, blur_level=5, temp=False):
    original = Image.open(load_path) # Load original

    # resize image on top
    hpercent = (dim[1] / float(original.size[1]))
    wsize = int((float(original.size[0]) * float(hpercent)))
    originalResized = original.resize((wsize, 720), Image.LANCZOS)

    # make background
    if blur:
        w, h = dim
        original_w, original_h = original.size

        # Force mode:
        if original.mode != 'RGB':
            original = original.convert('RGB')

        # Choose the larger scale to preserve the aspect ratio
        scale = max(w/original_w, h/original_h)

        # New dimensions after scaling
        new_w = int(original_w * scale)
        new_h = int(original_h * scale)
        blurImage = original.filter(ImageFilter.GaussianBlur(blur_level))
        scaledImage = blurImage.resize((new_w, new_h), Image.LANCZOS)

        # Center crop
        left = (scaledImage.width - w) / 2
        top = (scaledImage.height - h) / 2
        right = (scaledImage.width + w) / 2
        bottom = (scaledImage.height + h) / 2

        bg = scaledImage.crop((left, top, right, bottom))
    else:
        bg = Image.new('RGB', dim, (0, 0, 0))

    # Center and overlay
    centerBG = dim[0] / 2
    centerOverlay = originalResized.width / 2
    locW = int(centerBG - centerOverlay)

    bg.paste(originalResized, (locW, 0))

    # Save
    bg.save(f'/app/instance/temp/{v_id}/{v_id}_bg.jpg')
    return "Background rendering completed"

@c_app.task(name="preview.CreateTitleImage", bind=True)
def CreateTitleImage(self, v_id, font, title_font_size, title_font_colour, title_y_offset, u_id, title, dim, system_fonts, temp=False):
    # Init canvas
    canvas = Image.new("RGBA", dim, (0, 0, 0, 0)) 

    # Get font
    cached_font_path = os.path.join(font_cache_dir, font)
    if not os.path.exists(cached_font_path):
        if font in system_fonts:
            font_key = f"{S3_ASSET_PREFIX}/fonts/{font}"
        else:
            font_key = f"{S3_UPLOAD_PREFIX}/{u_id}/fonts/{font}"

        s3.download_file(S3_BUCKET, font_key, cached_font_path)
    
    if title_font_size > 0:  # Skip drawing if font size 0
        title_font = ImageFont.truetype(cached_font_path, title_font_size)

        # Draw
        draw = ImageDraw.Draw(canvas)
        box = draw.textbbox((0, 0), title, font=title_font)
        textW, textH = box[2] - box[0], box[3] - box[1]
        W, H = dim
        centerX = W / 2 - textW / 2
        centerY = H / 2 - textH / 2
        draw.text((centerX, centerY - title_y_offset), title, title_font_colour, font=title_font)

    # Save
    canvas.save(f'/app/instance/temp/{v_id}/{v_id}_title.png')
    return "Title preview rendering completed"

@c_app.task(name="preview.CreateGifPreview", bind=True)
def CreateGifPreview(self, id, video_path, frame_path):
    # Check aspect ratio
    v = VideoCapture(video_path)
    width = int(v.get(CAP_PROP_FRAME_WIDTH))
    height = int(v.get(CAP_PROP_FRAME_HEIGHT))
    assert width/height == 16/9 # Ensure 16/9 video

    # Get and return preview frames
    _ = ImageTools.get_frames(id, video_path, frame_path)
    return "GIF preview rendered successfully"

#######################################################################################################################
#   Render tasks
#######################################################################################################################
@c_app.task(name="preview.render", bind=True) # TODO implement 2 queues using process.* below
# @c_app.task(name="process.render", bind=True)
def render(self, v, tmpdir):
    chain_tasks = (initialise.s(v, tmpdir)
                   | upload_clip_assets.s() # (id, files, filenames) returned by initialise()
                   | create_edit.s()
                    # delete_temp
                   )
    result = chain_tasks.apply_async()
    return result

@c_app.task(name="preview.initialise", bind=True) # TODO implement 2 queues using process.* below
# @c_app.task(name="process.initialise", bind=True)
def initialise(self, visualizer, tmpdir):
    v = json.loads(visualizer) # Passed through as JSON
    # Set DB status as preprocessing
    beatcloud_db.set_visualizer_status(v.get('user_id'), v.get('id'), 'Pre-Processing')
    
    # if video base probe duration
    if v.get('base_type') == 'video':
        v['base_duration'] = get_duration(v.get('base_path'), tmpdir)
    # probe audio duration
    v['audio_duration'] = get_duration(v.get('audio_path'), tmpdir)
    # get_clip_paths
    files, filenames = get_clip_paths(tmpdir, v)
    return (v, files, filenames)
    
@c_app.task(name="preview.upload_clip_assets", bind=True) # TODO implement 2 queues using process.* below
# @c_app.task(name="process.upload_clip_assets", bind=True)
def upload_clip_assets(self, result):
    print("Uploading clip assets to s3... May take a while")
    v, files, filenames = result
    x = 0
    try:    
        for file_path in files:
            filename = filenames[x]
            s3_key = f"{S3_CLIP_PREFIX}/{v.get('id')}/{filename}"
            file = open(file_path, 'rb')
            
            # upload file directly
            s3.put_object(Bucket=S3_BUCKET, Key=s3_key, Body=file)
            x += 1

        # Remove temp dir as all went well.
        shutil.rmtree(os.path.join(os.path.sep, "app", "instance", "temp", v.get('id')))
    except FileNotFoundError as e:
        print(f"ERROR: Could not delete temp folder: {e}")
    except Exception as e:
        print(f"ERROR: Could not upload clip to S3 clips folder: {str(e)}")
        # TODO log db
    return v

@c_app.task(name="preview.create_edit", bind=True) # TODO implement 2 queues using process.* below
def create_edit(self, v):
    vis_json = json.dumps(v)
    v_obj = models.Visualizer.from_json(vis_json)
    
    ### Get asset urls
    # Base (Visualizer Specific)
    exp_base_filename = v_obj.base_path
    v_obj.base_url = get_s3_clip_asset_url(v_obj.id, exp_base_filename)
    # Audio
    exp_audio_filename = f"{v_obj.id}_audio.{v_obj.audio_ext}"
    v_obj.audio_url = get_s3_clip_asset_url(v_obj.id, exp_audio_filename)
    # Title
    if v_obj.show_title:
        exp_title_filename = f"{v_obj.id}_title.png"
        v_obj.title_url = get_s3_clip_asset_url(v_obj.id, exp_title_filename)
    # Layers
    if v_obj.contains_layers:
        exp_layer_filename = f"{v_obj.id}_layers.png"
        v_obj.layers_url = get_s3_clip_asset_url(v_obj.id, exp_layer_filename)

    if isinstance(v_obj, models.CompositeVisualizer):
        v_obj.fx_url = get_s3_BC_asset_url('fx', v_obj.fx["filename"])

    # construct edit & send
    if CHOSEN_SERVICE == "shotstack":
        edit = v_obj.get_ss_edit()
        try:
            api_response = SS_api_instance.post_render(edit)
            id = api_response['response']['id']
            beatcloud_db.set_visualizer_status(v.get('user_id'), v.get('id'), 'Queued')
            beatcloud_db.set_visualizer_shotstack_id(v.get('user_id'), v.get('id'), id)
            return f"Request successfully sent to ShotStack with ID: {id}"
        except Exception as e:
            print(f"Unable to resolve API call: {e}")
            return "Error occurred during API call."
    elif CHOSEN_SERVICE == "creatomate":
        options = v_obj.get_cm_edit()
        response = requests.post(
            CREATOMATE_URL,
            headers={
                'Authorization': f'Bearer {CREATOMATE_API_KEY}',
                'Content-Type': 'application/json',
            },
            json=options
        ).json()
        id = response[0]['id']
        if response[0]['status'] == "failed":
            err = response[0]['error_message']
            raise ValueError(f'Something wrong with API request: {err}. \nOptions:', options)
        else:
            beatcloud_db.set_visualizer_status(v.get('user_id'), v.get('id'), 'Queued')
            beatcloud_db.set_visualizer_creatomate_id(v.get('user_id'), v.get('id'), id)
            return f"Request successfully sent to Creatomate with ID: {id}"


# TODO also plan on using this function for BC watermark
def get_s3_BC_asset_url(type, filename):
    file_key = f"{S3_ASSET_PREFIX}/{type}/{filename}"
    try:
        response = s3.generate_presigned_url('get_object',
                                                Params={'Bucket': S3_BUCKET,
                                                            'Key': file_key},
                                                    ExpiresIn=3600)
        return response
    except s3.exceptions.NoSuchKey:
        print(f"No file in path: {file_key}")
        return False # TODO retry
    except s3.exceptions.NoCredentialsError:
        print("Credentials not available")
        return None
    
def get_s3_clip_asset_url(video_id, filename):
    file_key = f"{S3_CLIP_PREFIX}/{video_id}/{filename}"
    try:
        response = s3.generate_presigned_url('get_object',
                                                Params={'Bucket': S3_BUCKET,
                                                            'Key': file_key},
                                                    ExpiresIn=3600)
        return response
    except s3.exceptions.NoSuchKey:
        print(f"No file in path: {file_key}")
        return False # TODO retry
    except s3.exceptions.NoCredentialsError:
        print("Credentials not available")
        return None

def get_duration(filename, temp_dir):
    #gets duration from a specified file in temp dir, as this file is inevitably going to be same length as the final vid
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, cwd=temp_dir)
    return float(result.stdout)

def get_clip_paths(tmpdir, v):
    id = v.get('id')
    title_path = os.path.join(tmpdir, f"{id}_title.png")
    layers_path = os.path.join(tmpdir, f"{id}_layers.png")
    audio_filename = v.get('audio_path')
    audio_path = os.path.join(tmpdir, audio_filename)
    bg_filename = v.get('base_path')
    bg_path = os.path.join(tmpdir, bg_filename)

    # init arrs
    files = []
    filenames = []

    if v.get('show_title'):
        files.append(title_path) # title
        filenames.append(f"{id}_title.png")

    files.append(bg_path) # base image or video
    filenames.append(bg_filename)
    
    files.append(audio_path) # audio
    filenames.append(audio_filename)

    if os.path.exists(layers_path): # layers if any
        files.append(layers_path)
        filenames.append(f"{id}_layers.png")

    return files, filenames

##
########################################### YOUTUBE #################################################
##
import google.oauth2.credentials
import googleapiclient.discovery
import googleapiclient.errors
@c_app.task(name="preview.upload", bind=True) # TODO implement 2 queues using process.* below
# @c_app.task(name="tasks.upload")
def upload(self, user_id, v_id, form, credentials):
    # Inform DB of start of task
    beatcloud_db.set_visualizer_status(user_id, v_id, 'Uploading')

    # init upload
    options = get_options(form, user_id)
    print("----Starting celery upload task")
    youtube = googleapiclient.discovery.build(
        serviceName='youtube',
        version='v3',
        credentials=google.oauth2.credentials.Credentials(
            **credentials
        )
    )

    # attempt upload
    try:
        response = yt_upload.initialize_upload(youtube, options)

        if response['status']['uploadStatus'] == 'uploaded':
            # See if can make this one DB transaction?
            # Add youtube ID to database
            beatcloud_db.set_visualizer_yt_id(user_id, v_id, response['id']) 
            # Update DB
            beatcloud_db.set_visualizer_status(user_id, v_id, 'Uploaded')
            try:
                os.remove(os.path.join(os.path.sep, "app", "instance", "temp", v_id, f'{v_id}.mp4')) # Delete uploaded file
            except BaseException as e:
                # accept error so that video is still returned as successfully uploaded
                # log to db or something so that users can
                print(e)
        else:
            beatcloud_db.set_visualizer_status(user_id, v_id, 'Upload Failed')
    except googleapiclient.errors.HttpError as e:
        # log http error to DB
        print(f"HTTP QUOTA ERROR:  {e}")
        beatcloud_db.set_visualizer_status(user_id, v_id, 'Upload Failed')
        raise e
    except Exception as e:
        # Todo - log to db
        print(f"OTHER ERROR: {e}")
        beatcloud_db.set_visualizer_status(user_id, v_id, 'Upload Failed')
        raise upload.retry(exc=e)

def get_vid_file_from_s3(user_id, v_id):
    save_path = os.path.join(os.path.sep, "app", "instance", "temp", v_id)
    os.makedirs(save_path, exist_ok=True)
    
    obj_name = f'{S3_UPLOAD_PREFIX}/{user_id}/videos/{v_id}/{v_id}.mp4'
    print(f"Downloading file from S3: {obj_name}")
    
    file_path = os.path.join(save_path, f'{v_id}.mp4')
    with open(file_path, 'wb') as f:
        s3.download_fileobj(S3_BUCKET, obj_name, f)
    print(f"File saved to: {file_path}")
    return file_path

def get_options(form, user_id):
    v_id=form['videoid']
    file_path = get_vid_file_from_s3(user_id, v_id)

    options = {
        'title':form['title'],
        'description':form['description'],
        'keywords':form['keywords'],
        'category':10,
        'privacyStatus':form['visibility'],
        'file':file_path
    }
    return options