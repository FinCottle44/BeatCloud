from calendar import monthrange
from datetime import datetime, timedelta
from math import floor
from flask import render_template, url_for, request, redirect, flash, send_from_directory, Response, jsonify, session, json, abort
from flask_login import current_user, login_required, login_user, logout_user
from BeatCloud import app, ALLOWED_IMG_EXTENSIONS, ALLOWED_AUDIO_EXTENSIONS, ALLOWED_FONT_EXTENSIONS, ALLOWED_VIDEO_EXTENSIONS, GOOGLE_DISCOVERY_URL, beatcloud_db, User, s3
from BeatCloud.forms import CreateVidForm, UploadForm
from BeatCloud.engine import ImageTools, yt_upload, tasks
from BeatCloud.engine.models import *
from BeatCloud.engine.db import DecimalEncoder
from werkzeug.utils import secure_filename
import os, requests, json, shutil, glob, re, atexit, botocore, stripe
import shotstack_sdk as shotstack
from shotstack_sdk.api import edit_api

#http methods and codes:
# https://www.restapitutorial.com/lessons/httpmethods.html#:~:text=The%20primary%20or%20most%2Dcommonly,or%20CRUD)%20operations%2C%20respectively.

### Stripe Setup
stripe.api_key = os.environ.get('STRIPE_API_KEY')

###### RENDERING SETUP!!!
### ShotStack Setup
## Keys
 # Development
SHOTSTACK_HOST_URL = 'https://api.shotstack.io/stage'
SHOTSTACK_KEY_TYPE = 'DeveloperKey'
SHOTSTACK_API_KEY = os.environ.get('SHOTSTACK_API_STAGE_KEY')
 # Production
# SHOTSTACK_HOST_URL = 'https://api.shotstack.io/v1'
# SHOTSTACK_KEY_TYPE = 'DeveloperKey'
# SHOTSTACK_API_KEY = os.environ.get('SHOTSTACK_API_PROD_KEY')
##
SS_conf = shotstack.Configuration(host=SHOTSTACK_HOST_URL)
SS_conf.api_key[SHOTSTACK_KEY_TYPE] = SHOTSTACK_API_KEY
SS_api_client = shotstack.ApiClient(SS_conf)
SS_api_instance = edit_api.EditApi(SS_api_client)
atexit.register(lambda: SS_api_client.close())
### Creatomate setup
CREATOMATE_URL = 'https://api.creatomate.com/v1/renders'
CREATOMATE_API_KEY = os.environ.get('CREATOMATE_API_KEY')

@app.route("/")
def home():
    # landing page
    if current_user.is_authenticated:
        return render_template("home.html", name=current_user.name, email=current_user.email, pic=current_user.picture, title="Home")
    else:
        print("User not authenticated - Redirecting to login")
        return redirect(url_for("login"))

@login_required
@app.route("/create/", methods=['GET'])
def create():
    if not current_user.is_authenticated:
        return redirect('login')

    create_form = CreateVidForm()

    #Create unique video ID
    v_id = os.urandom(8).hex() # Maybe increase in production

    # create temp dir
    os.makedirs(os.path.join(app.config["TEMP_FOLDER"], v_id))

    fonts=get_user_fonts(current_user.id)
    layers=get_user_layers(current_user.id)

    return render_template('create.html', title="Create", form=create_form, v_id=v_id, fonts=fonts, user=current_user, layers=layers)

# USER FONTS
def get_user_fonts(u_id):
    try:
        font_path = f"{app.config['UPLOAD_FOLDER']}/{u_id}/fonts"
        fonts = {}
        response = s3.list_objects_v2(Bucket=app.config["S3_BUCKET"], Prefix=font_path)
        if 'Contents' in response:
            for obj in response['Contents']:
                filename = obj['Key'].split('/')[-1]  # Get just the filename
                fontname, _ = os.path.splitext(filename)  # Get the base filename without extension
                fonts[fontname] = filename
        else:
            print('No fonts found in the specified path.')
        return fonts
    except Exception as e:
        print(f"Error fetching user fonts: {e}")
        return {}

@app.route("/users/<u_id>/fonts", methods=["POST"])
def upload_font(u_id):
    if not authenticate_user(u_id):
        return Response("Unauthorized", 401)
    
    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No selected file', 400
    file = request.files['file']

    # Validate filename
    if file and allowed_font_file(file.filename):
        filename = secure_filename(file.filename)
    else:
        return 'Invalid or prohibited file type.', 415
        
    s3_key = f"{app.config['UPLOAD_FOLDER']}/{u_id}/fonts/{filename}"
    
    try:
        curr_usage = beatcloud_db.get_user_asset_usage(u_id)
        if curr_usage + 1 > app.config['TIERS'][current_user.tier]['asset_limit']:
            return "Custom asset limit reached - Upgrade your BeatCloud subscription to increase", 400
        
        # Limit OK - Proceed 
        s3.put_object(Bucket=app.config['S3_BUCKET'], Key=s3_key, Body=file)
        beatcloud_db.increment_user_asset_usage(u_id, 1)
        return filename, 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return Response("Internal Server Error", 500)

@app.route("/users/<u_id>/fonts/<path:fontname>", methods=["DELETE"])
def delete_font(u_id, fontname):
    # Auth
    if not authenticate_user(u_id):
        return {"error": "Unauthorized"}, 403

    # Authorized
    font_path = f"{app.config['UPLOAD_FOLDER']}/{u_id}/fonts/{fontname}"
    try:
        s3.head_object(Bucket=app.config['S3_BUCKET'], Key=font_path)
        s3.delete_object(Bucket=app.config['S3_BUCKET'], Key=font_path)
        beatcloud_db.increment_user_asset_usage(u_id, -1)
        return '', 204
    except s3.exceptions.NoSuchKey:
        return 'Invalid font path', 404
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return Response("Internal Server Error", 500)

# USER LAYERS
@app.route("/users/<u_id>/layers", methods=["POST"])
def upload_layer(u_id):
    # Auth
    if not authenticate_user(u_id):
        return Response("Unauthorized", 401)
    
    # check if the post request has the file part
    if 'file' not in request.files:
        return 'No selected file', 400
    
    file = request.files['file']

    # Validate filename
    if file and allowed_img_file(file.filename):
        filename = secure_filename(file.filename)
    else:
        return 'Invalid or prohibited file type.', 415
        
    s3_key = f"{app.config['UPLOAD_FOLDER']}/{u_id}/layers/{filename}"
    
    try:
        curr_usage = beatcloud_db.get_user_asset_usage(u_id)
        if curr_usage + 1 > app.config['TIERS'][current_user.tier]['asset_limit']:
            return "Custom asset limit reached - Upgrade your BeatCloud subscription to increase", 400
        
        # Limit OK - Proceed 
        s3.put_object(Bucket=app.config['S3_BUCKET'], Key=s3_key, Body=file)
        beatcloud_db.increment_user_asset_usage(u_id, 1)
        return filename, 200
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return Response("Internal Server Error", 500)

# Returns user layers for template rendering
def get_user_layers(u_id):
    try:
        layer_path = f"{app.config['UPLOAD_FOLDER']}/{u_id}/layers"
        layers = {}
        response = s3.list_objects_v2(Bucket=app.config["S3_BUCKET"], Prefix=layer_path)
        if 'Contents' in response:
            for obj in response['Contents']:
                filename = obj['Key'].split('/')[-1]  # Get just the filename
                layername, _ = os.path.splitext(filename)  # Get the base filename without extension
                layers[layername] = filename
        else:
            print('No layers found in the specified path.')
        return layers
    except Exception as e:
        print(f"An error occurred when feching user {u_id}'s layers: {e}")
        return {}

@app.route("/users/<u_id>/layers/<path:filename>", methods=["GET"])
def get_layer(u_id, filename):
    # Auth
    if not authenticate_user(u_id):
        return {"error": "Unauthorized"}, 403

    # Authorized
    file_key = f"{app.config['UPLOAD_FOLDER']}/{u_id}/layers/{filename}"

    try:
        # Generate a pre-signed URL for the S3 object
        # return Response(url, status=200)
        s3_response = s3.get_object(Bucket=app.config['S3_BUCKET'], Key=file_key)
        response = Response(s3_response['Body'].read())
        response.headers['Content-Type'] = s3_response['ContentType']
        response.headers['Content-Disposition'] = f'attachment; filename={file_key.split("/")[-1]}'
        return response

        # when in production: redirect to s3 link and apply policy to bucket.
        # [
        #   {
        #     "AllowedHeaders": ["*"],
        #     "AllowedMethods": ["GET"],
        #     "AllowedOrigins": ["https://your-web-application.com"],
        #     "ExposeHeaders": [],
        #     "MaxAgeSeconds": 3000
        #   }
        # ]
        # url = s3.generate_presigned_url('get_object',
        #                                 Params={'Bucket': app.config['S3_BUCKET'], 'Key': file_key},
        #                                 ExpiresIn=3600)
        # return redirect(url)
        # This is because when editing a canvas with an image from a diff origin without CORS you cannot save it to dataurl

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return Response("Internal Server Error", 500)

@app.route("/users/<u_id>/layers/<path:layer_name>", methods=["DELETE"])
def delete_layer(u_id, layer_name):
    # Auth
    if not authenticate_user(u_id):
        return {"error": "Unauthorized"}, 403

    # Authorized
    layer_path = f"{app.config['UPLOAD_FOLDER']}/{u_id}/layers/{layer_name}"
    try:
        s3.head_object(Bucket=app.config['S3_BUCKET'], Key=layer_path)
        s3.delete_object(Bucket=app.config['S3_BUCKET'], Key=layer_path)
        beatcloud_db.increment_user_asset_usage(u_id, -1)
        return '', 204
    except s3.exceptions.NoSuchKey:
        return 'Invalid font path', 404
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return Response("Internal Server Error", 500)

### Auxiliary filename methods:
def allowed_video_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

def allowed_img_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_IMG_EXTENSIONS

def allowed_audio_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO_EXTENSIONS

def allowed_font_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_FONT_EXTENSIONS

# @app.route('/media/<v_id>/<filename>')
#  s3 route
    # key = f"{app.config['TEMP_FOLDER']}/{v_id}/{filename}"

    # try:
    #     # Generate a pre-signed URL for the S3 object
    #     url = s3.generate_presigned_url('get_object',
    #                                     Params={'Bucket': app.config['S3_BUCKET'],
    #                                             'Key': key},
    #                                     ExpiresIn=3600)  # Link expires in 1 hour
    # except Exception as e:
    #     print(f"Could not generate pre-signed URL: {str(e)}")
    #     return abort(500, description="Internal Server Error")
    # return redirect(url)

@app.route('/temp/<v_id>/<filename>')
def download_file_from_temp(v_id, filename):
    return send_from_directory(os.path.join(app.config["TEMP_FOLDER"], v_id), filename)

@app.route("/visualizers/<v_id>/status", methods=["GET"])
def check_status(v_id):
    possible_values =  ['Pending', 'Pre-Processing', 'Queued', 'Rendering', 'Ready', 'Uploading', 'Uploaded', 'Failed']
    user_id = current_user.id
    ok, status_info = beatcloud_db.get_visualizer_status_info(user_id, v_id)
    v_key = f"{app.config['UPLOAD_FOLDER']}/{current_user.id}/videos/{v_id}/{v_id}.mp4" # s3 key

    # ping db for status:
    if ok:
        status = status_info.get('visualizer_status')
        if status in ["Queued", "Rendering"]:
            # ping shotstack / creatomate
            ss_task_id = status_info.get('ss_task_id')
            cm_task_id = status_info.get('cm_task_id')
            if ss_task_id: # we used shotstack
                ss_status = get_ss_status(ss_task_id)
                # Translate from ss status to beatcloud status
                ss_conversion = {'queued': 'Queued', 'fetching':'Queued', 'rendering':'Rendering', 'saving':'Rendering', 'done':'Ready', 'failed':'Failed'}
                converted_status = ss_conversion[ss_status]
            elif cm_task_id:
                cm = get_cm_info(cm_task_id)
                cm_status = cm['status']
                cm_conversion = {'planned': 'Queued', 'rendering':'Rendering', 'succeeded':'Ready', 'failed':'Failed'}
                converted_status = cm_conversion[cm_status]
                if converted_status == 'Ready':
                    # Download from CM into s3 when ready
                    r = requests.get(cm['url'], stream=True)
                    file = r.raw
                    data = file.read()
                    s3.put_object(Bucket=app.config['S3_BUCKET'], Key=v_key, Body=data)
                    # Thumb
                    r = requests.get(cm['snapshot_url'], stream=True)
                    file = r.raw
                    data = file.read()
                    s3.put_object(Bucket=app.config['S3_BUCKET'], Key=f"{app.config['UPLOAD_FOLDER']}/{current_user.id}/videos/{v_id}/{v_id}-thumb.jpg", Body=data)
            else:
                # log to db
                print("Failed to get either SS or CM task id.")
                converted_status = 'Failed'

            # Update Our DB
            if status != converted_status:
                beatcloud_db.set_visualizer_status(user_id, v_id, converted_status)

            # if 'ready' but not in S3 yet - return rendering as still saving to s3
            if converted_status=='Ready':
                try:
                    s3.head_object(Bucket=app.config['S3_BUCKET'], Key=v_key)
                    beatcloud_db.increment_user_video_usage(current_user.id, 1) # Increment value by 1
                except botocore.exceptions.ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        print(f"Video ready but not yet in S3... Returning rendering still.")
                        converted_status="Rendering"
            return converted_status, 200
        elif status not in possible_values:
            return f"Invalid Visualizer status: {status}", 400
        else:
            return status, 200
    else:
        # ok is False so status_info is error from db function 'e'
        return f"Could not fetch status for visualizer {v_id}: {status_info}", 500

def get_ss_status(id):
    try:
        api_response = SS_api_instance.get_render(id, data=False, merged=True)
        status = api_response['response']['status']
        return status
    except Exception as e:
        print(f"Unable to resolve API call: {e}")

def get_cm_info(id):
    try:
        response = requests.get(
            f'{CREATOMATE_URL}/{id}',
            headers={
                'Authorization': f'Bearer {CREATOMATE_API_KEY}',
                'Content-Type': 'application/json',
            }
        )
        return response.json()
    except Exception as e:
        print(f"Unable to resolve API call: {e}")

@app.route('/assets', methods=["GET"])
@login_required
def assets():
    fonts=get_user_fonts(current_user.id)
    layers=get_user_layers(current_user.id)
    asset_usage=beatcloud_db.get_user_asset_usage(current_user.id)
    tier_config = app.config['TIERS'][current_user.tier] # Defines limits etc.  
    return render_template("assets.html", user=current_user, title="Assets", user_fonts=fonts, user_layers=layers, asset_usage=int(asset_usage), user_tier_config=tier_config)

@app.route('/account', methods=["GET"])
@login_required
def account():
    user_templates = beatcloud_db.get_all_templates(current_user.id)
    user_presets = beatcloud_db.get_all_presets(current_user.id)
    # GET USER ONCE NOT ALL THOSE THINGS 
    usage = beatcloud_db.get_user(current_user.id)
    asset_usage = usage["asset_count"]
    video_usage = usage["monthly_video_count"]
    preset_usage = usage["preset_count"]
    tier_config = app.config['TIERS'][current_user.tier] # Defines limits etc.  

    # Time until usage reset
    user_reset_timestamp = current_user.user_billing_reset
    now = datetime.now().timestamp()
    time_delta = float(user_reset_timestamp) - now
    limit_reset_countdown = floor(time_delta / (60 * 60 * 24)) 
        
    # for unlimited there is no limit so no countdown
    return render_template("account.html", user=current_user, title="Account", user_templates=user_templates, user_presets=user_presets, user_tier_config=tier_config, asset_usage=asset_usage, video_usage=video_usage, preset_usage=preset_usage, limit_reset_countdown=limit_reset_countdown)

@app.route("/login/", methods=["POST", "GET"])
def login():
    if current_user.is_authenticated:
        #send to home
        return redirect('/')
    return render_template("login.html", title="Login")


######################################################
## STRIPE ROUTES
######################################################
@app.route('/portal', methods=["GET"])
@login_required
def create_stripe_portal():
    stripe_id = current_user.stripe_id
    portal = stripe.billing_portal.Session.create(
        customer=stripe_id,
        return_url="https://app.usebeatcloud.com/account", # the return URL
    )
    return redirect(portal['url'])

@app.route('/changeplan', methods=["GET"])
@login_required
def change_plan():
    if current_user.tier != "free": # User already subscribed and can change plan in customer portal
        return redirect(url_for('create_stripe_portal'))
    else:
        # pricing table
        return render_template('pricing.html', title="Plans", user=current_user)

# @app.route('/webhook', methods=['POST'])
# def webhook():
#     event = None
#     payload = request.data

#     try:
#         event = json.loads(payload)
#     except json.decoder.JSONDecodeError as e:
#         print('⚠️  Webhook error while parsing basic request.' + str(e))
#         return jsonify(success=False)
#     if endpoint_secret:
#         # Only verify the event if there is an endpoint secret defined
#         # Otherwise use the basic event deserialized with json
#         sig_header = request.headers.get('stripe-signature')
#         try:
#             event = stripe.Webhook.construct_event(
#                 payload, sig_header, endpoint_secret
#             )
#         except stripe.error.SignatureVerificationError as e:
#             print('⚠️  Webhook signature verification failed.' + str(e))
#             return jsonify(success=False)

#     # Handle the event
#     if event and event['type'] == 'payment_intent.succeeded':
#         payment_intent = event['data']['object']  # contains a stripe.PaymentIntent
#         print('Payment for {} succeeded'.format(payment_intent['amount']))
#         # Then define and call a method to handle the successful payment intent.
#         # handle_payment_intent_succeeded(payment_intent)
#     elif event['type'] == 'payment_method.attached':
#         payment_method = event['data']['object']  # contains a stripe.PaymentMethod
#         # Then define and call a method to handle the successful attachment of a PaymentMethod.
#         # handle_payment_method_attached(payment_method)
#     else:
#         # Unexpected event type
#         print('Unhandled event type {}'.format(event['type']))

#     return jsonify(success=True)

## ROUTE TO CHECKOUT
# get price ID from user selection
        # price_id = '{{PRICE_ID}}'
        # session = stripe.checkout.Session.create(
        # success_url='https://www.usebeatcloud.com/thankyou/{CHECKOUT_SESSION_ID}',
        # cancel_url='https:///www.usebeatcloud.com/canceled',
        # mode='subscription',
        # customer=current_user.stripe_id,
        # line_items=[{
        #     'price': price_id,
        #     # For metered billing, do not pass quantity
        #     'quantity': 1
        # }],
        # )

        # # Redirect to the URL returned on the session
        # return redirect(session.url, code=303)

################################################################################################################################################################
### Visualizers
################################################################################################################################################################
# Create Visualizer
@app.route("/visualizers/<v_id>", methods=["POST"])
def create_visualizer(v_id):
    if current_user.locked:
        return "Account temporarily locked. Plan limits likely reached.", 400

    # Data
    files = request.files
    v_id = request.form.get("v_id")
    u_id = current_user.id
    # blur_bg = request.form.get('add_blur') == 'y'
    show_title = request.form.get('showtitle') == 'y'
    form_fx = request.form.get('fx_select')
    fx = None if form_fx == "none" else FXClip(form_fx, request.form.get('fx_opacity')) # Create FX Object
    trackname = request.form.get('beatName')
    quality = request.form["video_quality"] # implement secure validation
    base_image = None
    base_video = None

    # Check for unauthorized FX
    if fx is not None:
        if current_user.tier not in fx.tiers:
            return "Invalid request: Incorrect BeatCloud tier for selected FX", 400

    # Check for audio file
    if 'beatFile' not in files or files["beatFile"].filename == "":
        return "No audio file uploaded", 400
    elif not allowed_audio_file(files["beatFile"].filename):
        return "Invalid audio filetype uploaded", 400
    else:
        audioFile = files["beatFile"]

    # Determine visual base
    tmpdir = os.path.join(app.config["TEMP_FOLDER"], v_id)
    ### Video
    if 'video_path' in request.form:
        print("Using supplied video & overriding any images")
        bg_filename = request.form["video_path"]
        base_video = bg_filename # For VisualizerFactory
    ### Image 
    elif request.form['imgURL'] != "" or 'imgFile' in request.files:
        print("Using image base")
        bg_filename = f"{v_id}_bg_edits.jpg" if os.path.exists(os.path.join(tmpdir, f"{v_id}_bg_edits.jpg")) else f"{v_id}_bg.jpg" # Use edited background if exists
        base_image = bg_filename # For VisualizerFactory
    else:
        print("No base media")
        return "No base media uploaded", 400
    
    # Get appropriate Visualizer from factory
    vid = VisualizerFactory.getVisualizer(v_id, u_id, trackname, 
                                          quality, fx, 
                                          base_image, 
                                          base_video)
    
    # Check tier for watermark
    if current_user.tier == "free":
        pass

    # save audio to tmp:
    vid.audio_path = f"{v_id}_audio.{vid.audio_ext}"
    audioFile.save(os.path.join(tmpdir, vid.audio_path))
    
    # Extra params
    vid.show_title = show_title
    vid.contains_layers = os.path.exists(os.path.join(tmpdir, f"{vid.id}_layers.png"))

    if vid is not None: # Has passed validation
        vid_json = vid.to_json() # Convert object to JSON for celery tasks
        tasks.render.delay(vid_json, tmpdir) # Queue render

        # Inform DB:
        info = {
            'user_id':vid.user_id,
            'visualizer_id':vid.id,
            'title':vid.title,
            'created':str(datetime.now().timestamp()),
            'visualizer_status':'Pending'
        }
        beatcloud_db.add_visualizer(**info)
        return "Visualizer added to render queue!", 201
    else:
        return "Visualizer type could not be defined.", 400


# View all vizualizers
@app.route('/visualizers', methods=["GET"])
@login_required
def get_user_visualizers(): 
    sort_by = request.args.get('sort_by', 'date_desc') # default to date_desc
    videos = beatcloud_db.get_user_visualizers(current_user.id, sort_by)

    for v in videos:
        v["user_id"] = v["PK"].split('#')[1]
        v["id"] = v["SK"].split('#')[1]
    return render_template("visualizers.html", user=current_user, title="Videos", videos=videos)

# View specific visualizer
@app.route('/visualizers/<id>', methods=["GET"])
@login_required
def get_visualizer(id):
    upload_form = UploadForm()
    video = beatcloud_db.get_visualizer(current_user.id, id)
    if not video:
        print("No video in database")
        return Response(status=404)
    
    video["user_id"] = video["PK"].split('#')[1]
    video["id"] = video["SK"].split('#')[1]

    # Auth
    if not authenticate_user(video["user_id"]):
        return {"error": "unauthorized"}, 403

    v_uri = url_for('get_video', id=video["id"])
    return render_template("view.html", v_path=v_uri, form=upload_form, title="View", user=current_user, video=video)

# Actual visualiser video files !!move
@app.route('/media/videos/<id>', methods=["GET"])
@login_required
def get_video(id):
    # Construct the S3 key for the video file
    v_key = f"{app.config['UPLOAD_FOLDER']}/{current_user.id}/videos/{id}/{id}.mp4"

    try:
        # Check if the file exists in S3
        s3.head_object(Bucket=app.config['S3_BUCKET'], Key=v_key)
        
        # Generate a pre-signed URL for the S3 object
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': app.config['S3_BUCKET'],
                                                'Key': v_key},
                                        ExpiresIn=3600)  # Link expires in 1 hour
    except s3.exceptions.NoSuchKey:
        print(f"No video file in path: {v_key}")
        return abort(404)
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return abort(500, description="Internal Server Error")

    # Redirect to the pre-signed URL
    return redirect(url)

# Visualizer thumbnail (created by the system)
@app.route("/visualizers/<v_id>/thumb", methods=["GET"])
@login_required
def get_thumb(v_id):
    v = beatcloud_db.get_visualizer(current_user.id, v_id)
    user_id = v["PK"].split('#')[1] if v else None
    
    if v and user_id:
        # Construct the S3 key for the thumbnail image
        thumb_key = f"{app.config['UPLOAD_FOLDER']}/{user_id}/videos/{v_id}/{v_id}-thumb.jpg"
        
        try:
            # Check if the thumbnail image exists in S3
            s3.head_object(Bucket=app.config['S3_BUCKET'], Key=thumb_key)
            
            # Generate a pre-signed URL for the S3 object
            url = s3.generate_presigned_url('get_object',
                                            Params={'Bucket': app.config['S3_BUCKET'],
                                                    'Key': thumb_key},
                                            ExpiresIn=3600)  # Link expires in 1 hour
            return redirect(url)
        except Exception as e:
            print(f"An error occurred: {str(e)}")
    
    # Serve default image if thumbnail does not exist in S3 or if there is any error
    return send_from_directory('static', 'img/Image_not_available.png'), 404

# Delete visualizer
@app.route('/visualizers/<v_id>', methods=["DELETE"])
@login_required
def delete_visualizer(v_id): 
    vid = beatcloud_db.get_visualizer(current_user.id, v_id)  # Fetch Visualizer
    if not vid:  # If none return 404
        return Response(status=404)
    elif vid['PK'].split('#')[1] != current_user.id:  # Check authorization
        print(f"User {current_user.id} performed unauthorised attempt at deleting video {v_id} (owned by user {vid['PK'].split('#')[1]})")
        return Response(status=401)
    else:  # Delete video
        print(f"deleting user {current_user.id}'s video {v_id}'")
        #remove from db
        beatcloud_db.delete_visualizer(current_user.id, v_id)

        #remove directories
        video_dir = os.path.join(app.config['UPLOAD_FOLDER'], vid['PK'].split('#')[1], 'videos', v_id)
        if os.path.exists(video_dir):
            shutil.rmtree(video_dir)
        temp_dir = os.path.join(app.config["TEMP_FOLDER"], v_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        
        # Return no content as deletion
        return Response(status=204)

    
################################################################################################################################################################
### Preview Routes:
# Preview background. Image or video! NOTE: This is the 'postfilter' background. Rendered to size, but without CAMAN filters applied.
@app.route("/visualizers/<v_id>/preview", methods=['GET'])
def get_preview(v_id):
    # Get the base (unedited) preview of the current visualizer
    try:
        file = glob.glob(f'{os.path.join(app.config["TEMP_FOLDER"], v_id)}/{v_id}_bg.*')[0]
        return send_from_directory(os.path.join(app.config["TEMP_FOLDER"], v_id), os.path.basename(file))
    except (FileNotFoundError, IndexError):
        return send_from_directory('static', 'img/PREVIEWimg.png')

@app.route("/visualizers/<v_id>/preview", methods=['PUT'])
def draw_preview(v_id):
    # The calling of this function indicates user has changed background entirely, so we can delete previous edit files:
    try:
        os.remove(os.path.join(app.config["TEMP_FOLDER"], v_id, f"{v_id}_bg_edits.jpg"))
    except FileNotFoundError:
        pass
    
    ## Determine base type
    # check if the post request has the file part
    if 'img-file' in request.files and request.files['img-file'].filename != '':
        # Get file
        file = request.files['img-file']
        blur = request.form["blur"] == "true" or request.form["blur"] == 'y'
        blur_level = int(request.form["blur-level"])

        if allowed_img_file(file.filename):
            # process image here and return image name back
            path = os.path.join(app.config["TEMP_FOLDER"], v_id, f'{v_id}_original.jpg')
            saved_path = ImageTools.InitOriginal(path, UploadedImg=file)

            # Queue task to start preview
            preview_task = tasks.CreateBG.delay(v_id, blur, saved_path, (1280, 720), blur_level)
            
            # No longer need any video preview files as img base:
            try_delete(v_id, f"{v_id}_bg.gif")
            try_delete(v_id, f"{v_id}_base_video.mp4")
            try_delete(v_id, f"{v_id}_base_video.mov")
            return jsonify({'task_id':preview_task.id}), 202
        else:
            return "Invalid image filetype uploaded - Images must be PNG or JPG.", 400
    elif 'video-file' in request.files and request.files['video-file'].filename != '':
        # Get file
        file = request.files['video-file']
        id = request.form['id']

        if allowed_video_file(file.filename):
            # Save base_video
            filename = secure_filename(file.filename)
            ext = os.path.splitext(filename)[1]
            base_path = os.path.join(app.config["TEMP_FOLDER"], id, f"{v_id}_base_video{ext}") # we know this is a safe filename
            
            file.save(base_path)

            frame_path = os.path.join(app.config["TEMP_FOLDER"], id)
            gif_task = tasks.CreateGifPreview.delay(id, base_path, frame_path)

            # No longer need image preview files as video base:
            try:
                try_delete(v_id, f"{v_id}_bg.jpg")
                try_delete(v_id, f"{v_id}_bg_edits.jpg")
                try_delete(v_id, f"{v_id}_original.jpg")
            except FileNotFoundError:
                pass

            return jsonify({'task_id':gif_task.id, 'base_path':f"{v_id}_base_video{ext}"}), 202
        else:
            return "Non-video or invalid file provided", 400
    else: # Using Image URL
        fileURL = request.form["img-url"]
        blur = request.form["blur"] == "true" or request.form["blur"] == 'y'
        blur_level = int(request.form["blur-level"])
        try:            
            path = os.path.join(app.config["TEMP_FOLDER"], v_id, f'{v_id}_original.jpg')
            saved_path = ImageTools.InitOriginal(path, imgUrl=fileURL)

            # Queue preview drawing:
            preview_task = tasks.CreateBG.delay(v_id, blur, saved_path, (1280, 720), blur_level)

            # Not sure whether to keep below??
            # base_path = preview_bg_name # Prevents returning of underlying file structure

            # No longer need any video preview files as img base:
            try_delete(v_id, f"{v_id}_bg.gif")
            try_delete(v_id, f"{v_id}_base_video.mp4")
            try_delete(v_id, f"{v_id}_base_video.mov")
            return jsonify({'task_id':preview_task.id}), 202
        except IOError as e:
            return "Non-image or invalid file provided via URL", 400
        except BaseException as e:
            print(e)
            return "An unknown error occurred,", 500

    # preview_path = url_for('download_file_from_temp', v_id=v_id, filename=preview_bg_name)
    # return jsonify({'status': 'success', 'preview_path':preview_path, 'base_path':base_path}), 201

def try_delete(v_id, file):
    #  Attempt deletion of file when changing base type
    try:
        os.remove(os.path.join(app.config["TEMP_FOLDER"], v_id, file))
    except FileNotFoundError:
        pass

# Refresh frames of video preview gif
@app.route("/visualizers/<v_id>/preview/refresh", methods=["POST"])
def refresh_frames(v_id):
    tmp_path = os.path.join(app.config["TEMP_FOLDER"], v_id)
    vid_path = os.path.join(tmp_path, f"{v_id}_base_video.mp4")
    if not os.path.exists(vid_path):
        vid_path = os.path.join(tmp_path, f"{v_id}_base_video.mov")
        if not os.path.exists(vid_path):
            return "No base video found", 404
    refresh_task = tasks.CreateGifPreview.delay(v_id, vid_path, tmp_path)
    return jsonify({'task_id':refresh_task.id}), 202

### Image editing routes
@app.route("/visualizers/<v_id>/preview/edits", methods=["GET"])
#  Not actually used at the moment as we return the path once edited in PUT route below, but good to implement for future:
def get_background_edits(v_id):
    # todo: Test for if doesn't exist
    return url_for(download_file_from_temp(v_id, "preview_background_edits.png"))

@app.route("/visualizers/<v_id>/preview/edits", methods=["PUT"])
def update_visualizer_edits(v_id):
    # Get layer data
    layers_data = request.form["layers_dataurl"].split(',')[1]
    layers_outcome = ImageTools.fromDataUrl(os.path.join(app.config["TEMP_FOLDER"], v_id), layers_data, f'{v_id}_layers.png') # Save image to disk
    
    if 'background_dataurl' in request.form:
        # Get background data
        bg_data = request.form["background_dataurl"].split(',')[1]
        bg_outcome = ImageTools.fromDataUrl(os.path.join(app.config["TEMP_FOLDER"], v_id), bg_data, f'{v_id}_bg_edits.jpg') # Save image to disk

        if bg_outcome[0] and layers_outcome[0]: # Both bg and layers were successful
            data = {'bg_url' : f'/temp/{v_id}/{bg_outcome[1]}', 'layers_url' : f'/temp/{v_id}/{layers_outcome[1]}'}
            return jsonify(data), 200
        else:
            return f'A server error occured in ImageTools.fromDataUrl(): \n 1:{bg_outcome[1]} \n 2:{layers_outcome[1]}', 400
    else:
        if layers_outcome[0]: # Only layers were successful
            data = {'layers_url' : f'/temp/{v_id}/{layers_outcome[1]}'}
            return jsonify(data), 200
        else:
            return f'A server error occured in ImageTools.fromDataUrl(): \n 1:{layers_outcome[1]}', 400

# Also not used:
@app.route("/visualizers/<v_id>/preview/edits", methods=["DELETE"])
def delete_background_edits(v_id):
    # todo: Authorisation check
    try:
        os.remove(os.path.join(app.config["TEMP_FOLDER"], v_id), "preview_background_edits.png")
        return "Edits successfully deleted.", 200
    except:
        return "Error deleting edits", 404   

# Preview title
@app.route('/visualizers/<v_id>/title', methods=['PUT'])
def draw_title(v_id):
    # need to Change to proper validation
    if request.form['title'] != "":
        font = request.form['title_font']
        title_font_colour = request.form['title_font_colour']
        title_font_size = int(request.form['title_font_size'])
        title_y_offset = int(request.form['title_ypos'])
        title_task = tasks.CreateTitleImage.delay(v_id, font, title_font_size=title_font_size, 
                                                title_font_colour=title_font_colour, title_y_offset=title_y_offset, u_id=current_user.id, 
                                                title=request.form['title'], dim=(1920, 1080),
                                                system_fonts=app.config["SYSTEM_FONTS"]
                                            )
    return jsonify({'task_id':title_task.id}), 202
    # return  url_for('download_file_from_temp', v_id=v_id, filename="v_id.png")

# Fetched when celery preview task completes
@app.route('/visualizers/<v_id>/title', methods=['GET'])
def get_title(v_id):
    title_path = os.path.join(v_id, f"{v_id}_title.png")
    return send_from_directory(app.config["TEMP_FOLDER"], title_path)

@app.route('/check_task/<task_id>', methods=['GET'])
def check_task(task_id):
    task = tasks.c_app.AsyncResult(task_id)
    if task.state == 'SUCCESS':
        return jsonify({'status': 'SUCCESS', 'result': task.result})
    elif task.state == 'FAILURE':
        return jsonify({'status': 'FAILURE', 'error': str(task.result)}), 500
    return jsonify({'status': 'PENDING'})

################################################################################################################################
#### Preset Routes
@app.route('/users/<u_id>/presets', methods=['POST'])
def new_preset(u_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    
    curr_usage = beatcloud_db.get_user_preset_usage(u_id)
    if curr_usage + 1 > app.config['TIERS'][current_user.tier]['preset_limit']:
        return "Preset & Template limit reached - Upgrade your BeatCloud subscription to increase", 400
    
    preset_name = secure_filename(request.json['preset_name']).replace('_', ' ').strip() # Retain spaces so looks better, users fault if they try some naughty stuff and end up with loads of spaces
    if preset_name is None or preset_name == "":
        return "Preset name cannot be empty", 400
    
    preset_id = os.urandom(6).hex()
    preset_data = beatcloud_db.convert_floats(request.json['preset_data'])
    
    beatcloud_db.add_preset(u_id, preset_id, preset_name, preset_data)
    beatcloud_db.increment_user_preset_usage(u_id, 1)
    return jsonify({'status': 'success', 'message': 'Preset created successfully'}), 201

@app.route('/users/<u_id>/presets', methods=['GET'])
def get_all_presets(u_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    try:
        presets = beatcloud_db.get_all_presets(current_user.id)
        presets_json = json.dumps(presets, cls=DecimalEncoder)
        return jsonify(json.loads(presets_json))
    except BaseException as e:
        print(f"\n An error occured fetching presets:\n{e}\n")
        return "Error fetching presets", 404

@app.route('/users/<u_id>/presets/<preset_id>', methods=['GET'])
def get_preset(u_id, preset_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    
    try:
        preset = beatcloud_db.get_preset(current_user.id, preset_id)
        preset_json = json.dumps(preset, cls=DecimalEncoder)
        return jsonify(json.loads(preset_json))
    except BaseException as e:
        print(f"\n An error occured fetching presets:\n{e}\n")
        return "Error fetching presets", 404


@app.route('/users/<u_id>/presets/<preset_id>', methods=['PUT'])
def update_preset(u_id, preset_id):
    # Auth
    if not authenticate_user(u_id):
        return Response(status=403)
    
    preset_name = secure_filename(request.json['preset_name']).replace('_', ' ').strip() # Retain spaces so looks better, users fault if they try some naughty stuff and end up with loads of spaces
    if preset_name is None or preset_name == "":
        return "Preset name cannot be empty", 400

    try:
        # Update preset
        preset_name = request.json['preset_name']
        preset_data = request.json['preset_data']
        beatcloud_db.update_preset(current_user.id, preset_id, preset_name, preset_data)

        return jsonify(success=True), 200
    except BaseException as e:
        print(f"\n An error occured fetching presets:\n{e}\n")
        return "Error fetching presets", 404

@app.route('/users/<u_id>/presets/<preset_id>', methods=['DELETE'])
def delete_preset(u_id, preset_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    
    try:
        item = beatcloud_db.get_preset(current_user.id, preset_id)
        
        beatcloud_db.delete_preset(current_user.id, preset_id)
        beatcloud_db.increment_user_preset_usage(u_id, -1)
        return preset_id, 200
    except BaseException as e:
        print(f"\n An error occured fetching presets:\n{e}\n")

################################################################################################################################
#### Template Routes
@app.route('/users/<u_id>/templates', methods=['POST'])
def new_template(u_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    
    curr_usage = beatcloud_db.get_user_preset_usage(u_id)
    if curr_usage + 1 > app.config['TIERS'][current_user.tier]['preset_limit']:
        return "Preset & Template limit reached - Upgrade your BeatCloud subscription to increase", 400

    template_name = secure_filename(request.json['template_name']).replace('_', ' ').strip() # Retain spaces so looks better, users fault if they try some naughty stuff and end up with loads of spaces
    if template_name is None or template_name == "":
        return "Template name cannot be empty", 400
    
    template_id = os.urandom(6).hex()
    template_data = request.json['template_data']
    
    # verify validity and security of attempted placeholders
    valid_title, title_status = validate_template(template_data['title'])
    if not valid_title:
        return f"Invalid template placeholders provided. Error description: '{title_status}'", 400
    
    valid_desc, desc_status = validate_template(template_data['title'])
    if not valid_desc:
        return f"Invalid template placeholders provided. Error description: '{desc_status}'", 400

    beatcloud_db.add_template(u_id, template_id, template_name, template_data)
    beatcloud_db.increment_user_preset_usage(u_id, 1)
    return jsonify({'status': 'success', 'message': 'Template created successfully'}), 201

def validate_template(template_str):
    placeholders = re.findall(r'\[\[(.*?)\]\]', template_str)
    
    for placeholder in placeholders:
        if not re.match(r'^\w+$', placeholder):
            return False, f"Invalid placeholder: {placeholder}"
    return True, "Valid template"

@app.route('/users/<u_id>/templates', methods=['GET'])
def get_all_templates(u_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    try:
        templates = beatcloud_db.get_all_templates(current_user.id)
        templates_json = json.dumps(templates, cls=DecimalEncoder)
        return jsonify(json.loads(templates_json))
    except BaseException as e:
        print(f"\n An error occured fetching templates:\n{e}\n")
        return "Error fetching templates", 404

@app.route('/users/<u_id>/templates/<template_id>', methods=['GET'])
def get_template(u_id, template_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    
    try:
        template = beatcloud_db.get_template(current_user.id, template_id)
        template_json = json.dumps(template, cls=DecimalEncoder)
        return jsonify(json.loads(template_json))
    except BaseException as e:
        print(f"\n An error occured fetching templates:\n{e}\n")
        return "Error fetching templates", 404


@app.route('/users/<u_id>/templates/<template_id>', methods=['PUT'])
def update_template(u_id, template_id):
    # Auth
    if not authenticate_user(u_id):
        return Response(status=403)
    
    template_name = secure_filename(request.json['template_name']).replace('_', ' ').strip() # Retain spaces so looks better, users fault if they try some naughty stuff and end up with loads of spaces
    if template_name is None or template_name == "":
        return "Template name cannot be empty", 400

    try:
        # Update template
        template_name = request.json['template_name']
        template_data = request.json['template_data']
        beatcloud_db.update_template(current_user.id, template_id, template_name, template_data)

        return jsonify(success=True), 200
    except BaseException as e:
        print(f"\n An error occured fetching templates:\n{e}\n")
        return "Error fetching templates", 404  

@app.route('/users/<u_id>/templates/<template_id>', methods=['DELETE'])
def delete_template(u_id, template_id):
    if not authenticate_user(u_id):
        return Response(status=403)
    
    try:
        item = beatcloud_db.get_template(current_user.id, template_id)
        beatcloud_db.delete_template(current_user.id, template_id)
        beatcloud_db.increment_user_preset_usage(u_id, -1)
        return template_id, 200
    except BaseException as e:
        print(f"\n An error occured fetching templates:\n{e}\n")

#############################################################################
# YT Upload routes


@app.route('/visualizers/<v_id>/upload', methods=["POST"])
@login_required
def upload(v_id):
    if 'credentials' not in session:
        return redirect('oauth')
    
    if current_user.locked:
        return "Account is temporarily locked. Please ensure you are within your Plan limits", 400
    
    # if having problems, consider setting vis status to uploading here.

    # Queue upload task
    try:
        tasks.upload.delay(current_user.id, v_id, request.form, session["credentials"])
        return "Video upload started", 200
    except BaseException as e:
        print(e)
        # log in db
        return "Oops! An unexpected error prevented the upload from starting. Please try again later.", 500

@app.route('/visualizers/<v_id>/upload/status', methods=["GET"])
@login_required
def check_upload_status(v_id):
    vis = beatcloud_db.get_visualizer(current_user.id, v_id)
    if vis['visualizer_status'] == "Uploaded":
        return vis['yt_id'], 200
    elif vis["visualizer_status"] == "Uploading":
        return "Video uploading", 202
    else:
        # log in db
        print(f"Failed to upload - Visualizers status not in ['Uploaded', 'Uploading']. Instead got {vis['visualizer_status']}!")
        # get error somehow
        return "Video failed to upload", 500

#callback route for shotstack:
        # if success:
        #     beatcloud_db.set_visualizer_status(user_id, id, 'Ready')
        # else:
        #     beatcloud_db.set_visualizer_status(user_id, id, 'Failed')

#############################################################################
# GOOGLE LOGIN routes
import google_auth_oauthlib.flow
import googleapiclient.discovery

def get_google_provider_cfg():
    return requests.get(GOOGLE_DISCOVERY_URL).json()

@app.route("/oauth")
def oauth_login():
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=[
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
            ]
    )
    flow.redirect_uri = request.base_url + "/callback"

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        #prompt='consent' #uncomment for release
    )

    #store state
    session['state'] = state

    return redirect(authorization_url) # Todo - generate self signed cert and use that and see if errors still happen, or change usebeatcloud to point to this machine

# Not great, make RESTful?
@app.route("/error/<error_context>/<error_description>")
def error(error_context, error_description):
    return render_template("error.html", e_context=error_context, e_description=error_description)

@app.route("/oauth/callback")
def callback():
    #error check & redirect
    if request.args.get("error"):
        print("was an error")
        return redirect(f"/error/login/{request.args.get('error')}")

    state = session['state']

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        'client_secrets.json',
        scopes=[
            'https://www.googleapis.com/auth/youtube.upload',
            'https://www.googleapis.com/auth/userinfo.email',
            'https://www.googleapis.com/auth/userinfo.profile',
            'openid'
            ],
        state=state
    )
    flow.redirect_uri = url_for('callback', _external=True, _scheme='https')
    print(f"callback redir: {flow.redirect_uri}")

    #fetch token
    temp_url = request.url
    auth_response = temp_url
    print(f"auth resp: {auth_response}")
    print(request, session.get('_google_authlib_state_'))

    flow.fetch_token(authorization_response=auth_response)

    credentials = flow.credentials
    session['credentials'] = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }

    #fetch user info
    userinfo_service = googleapiclient.discovery.build(
        serviceName='oauth2',
        version='v2',
        credentials=credentials
    )
    userinfo = userinfo_service.userinfo().get().execute()

    # Create a user object for DB
    if not userinfo.get("verified_email"):
        return "User email not available or not verified by Google.", 400

    # Doesn't exist? Add user to the database.
    db_user = beatcloud_db.get_user(userinfo["id"])
    if not db_user:
        # Create stripe customer and get id
        cust = stripe.Customer.create(
            email=userinfo["email"]
        )

        # Add user
        # user_billing_reset = int((datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=30)).timestamp()) # Midnight 30 days from now
        user_billing_reset = int((datetime.now() + timedelta(minutes=2)).timestamp()) # debug 2 min 
        beatcloud_db.add_user(userinfo["id"], userinfo["given_name"], userinfo["email"], userinfo["picture"], cust.id, user_billing_reset) 

        # Stripe ID for tier updates
        cust_id =  cust.id

        # Create directory for permenant storage of video & assets
        # create_user_dirs(userinfo["id"]) # not sure if need??
    else:
        cust_id = db_user["stripe_id"]
        user_billing_reset = db_user["billing_reset_timestamp"]

    # Create User obj
    user = User(userinfo["id"], userinfo["given_name"], userinfo["email"], userinfo["picture"], cust_id, user_billing_reset)

    # Begin session by logging the user in
    login_user(user)

    # Send user back to homepage
    return redirect(url_for("home", _external=True))
   

def create_user_dirs(user_id):
    vid_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id, "videos")
    os.makedirs(vid_dir, exist_ok=True)
    font_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id, "fonts")
    os.makedirs(font_dir, exist_ok=True)
    lay_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id, "layers")
    os.makedirs(lay_dir, exist_ok=True)

@app.route("/logout")
@login_required
def logout():
    name = current_user.name
    logout_user()
    print("logged out user " + name)
    # redirect to '/' no?
    return render_template("logout.html", title="Logout")

# We do not use @loginrequired as this attempts to redirect DELETE requests if the user isn't authenticated, so we instead just check the authentication ourselves
@app.route("/users/<user_id>", methods=["DELETE"])
def deleteuser(user_id):
    print(f"Attempting to delete user: {user_id}")
    user = beatcloud_db.get_user(user_id)
    if user is None or current_user.is_authenticated and not authenticate_user(user_id):
        return Response({'Unauthorized attempt at deletion - Logged.'}, status=403)
    
    if user is None:
        return Response({'User not found'}, status=404)

    # Logout
    logout_user()
    
    # del user
    beatcloud_db.delete_user(user_id)

    #Delete directories
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], user_id)
    if os.path.exists(user_dir):
        print("valid path deleting vid dir: " + user_dir)
        shutil.rmtree(user_dir)

    print(f"Deleted user {user_id}")
    return Response({'Successfully deleted user account'}, status=200)


# Helper function to force authentication for dangerous operations    
def authenticate_user(user_id):
    print(f"authenticating user {user_id} with current user {current_user.id}")
    return current_user.id == user_id