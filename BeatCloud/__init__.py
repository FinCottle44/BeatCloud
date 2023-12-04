import os, boto3, stripe
from flask import Flask
from flask_login import LoginManager, UserMixin
from flask_crontab import Crontab
from oauthlib.oauth2 import WebApplicationClient
from datetime import datetime, timedelta

### Stripe Setup
stripe.api_key = os.environ.get('STRIPE_API_KEY')

# Google Configuration
GOOGLE_CLIENT_ID = os.environ.get("BC_GOOGLE_CLIENT_ID", None)
GOOGLE_CLIENT_SECRET = os.environ.get("BC_GOOGLE_CLIENT_SECRET", None)
GOOGLE_DISCOVERY_URL = (
    "https://accounts.google.com/.well-known/openid-configuration"
)

#FFMPEG setup
os.environ['FFREPORT'] = 'file=ffreport.log:level=32'

#Flask config
app = Flask(__name__, static_folder="static")
# app.config['SECRET_KEY'] = os.environ.get("BC_SECRET_KEY") or os.urandom(24)
app.config['SECRET_KEY'] = os.environ.get("BC_SECRET_KEY")
app.config['JSON_SORT_KEYS'] = False
app.config['PREFERRED_URL_SCHEME'] = 'https'

# BeatCloud variables
app.config['SYSTEM_FONTS'] = ["Blacklisted.ttf", "coolvetica rg.ttf", "DISTGRG_.ttf"]

# Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Tier Setup
app.config['TIERS'] = {
    'free':{
        'watermark':True,
        'monthly_vid_limit':6,
        'storage_hours':12,
        'asset_limit':1,
        'preset_limit':1,
        'ads':True,
        'max_res':720,
        'max_fps':15,
        'pretty_name':'BeatCloud Free'
    },
    'plus':{
        'watermark':False,
        'monthly_vid_limit':10,
        'storage_hours':168,
        'asset_limit':3,
        'preset_limit':4,
        'ads':False,
        'max_res':720,
        'max_fps':24,
        'pretty_name':'BeatCloud Plus'
    },
    'unlimited':{
        'watermark':False,
        'monthly_vid_limit':999,
        'storage_hours':720,
        'asset_limit':999,
        'preset_limit':999,
        'ads':False,
        'max_res':1080,
        'max_fps':24,
        'pretty_name':'BeatCloud Unlimited'
    }
}

#OAUTH2 setup
client = WebApplicationClient(GOOGLE_CLIENT_ID)

### S3 
s3 = boto3.client('s3',               
    aws_access_key_id=os.environ['AWS_S3_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_S3_SECRET_ACCESS_KEY'],
    region_name='eu-west-2'
)
app.config["S3_BUCKET"] = 'beatcloud-sandbox'
# app.config["S3_BUCKET"] = 'beatcloud-production'
app.config["S3_REGION"] = 'eu-west-2'

# S3
app.config['UPLOAD_FOLDER'] = 'media'
app.config['ASSETS_FOLDER'] = 'bc_assets' # BeatCloud assets such as FX & Fonts
app.config['CLIPS_FOLDER'] = 'clip_assets' # ShotStack Clip assets (Visualizer image & videos etc)
app.config['LOGS_FOLDER'] = 'logs'

# Local
app.config['TEMP_FOLDER'] = os.path.join(app.instance_path, 'temp')

# Allowed file upload extensions
ALLOWED_IMG_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav'}
ALLOWED_FONT_EXTENSIONS = {'ttf', 'otf'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov'}

# DB Connection:
from .engine.db import BC_Table
dynamodb = boto3.resource('dynamodb',               
    aws_access_key_id=os.environ['AWS_DB_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['AWS_DB_SECRET_ACCESS_KEY'],
    region_name='eu-west-2'
)

# Check if table exists and create if not create it
# - Note that this does not define the TTL for items with attribute expiry_time
table_name = 'beatcloud'
beatcloud_db = BC_Table(dynamodb)
exists = beatcloud_db.exists(table_name)
if not exists:
    print(f"\nCreating table {table_name}...")
    beatcloud_db.create_table(table_name)
    print(f"\nCreated table {beatcloud_db.table.name}.")

#### Crontab setup & jobs
crontab = Crontab(app)
@crontab.job() # todo every day
def reset_free_limits():
    # search for users that billing date expired yesterday
    # we set the user expiry date in db
    pass

#####
# Flask-Login helper to retrieve a user from our db
@login_manager.user_loader
def load_user(user_id):
    db_user = beatcloud_db.get_user(user_id)
    if db_user:
        id = db_user["PK"].split('#')[1]
        name = db_user["name"]
        email = db_user["email"]
        picture = db_user["picture"]
        stripe_id = db_user["stripe_id"]
        billing_reset_timestamp = db_user["billing_reset_timestamp"]
        user = User(id, name, email, picture, stripe_id, billing_reset_timestamp)
    else:
        print("User not found")
        user = None
    return user

class User(UserMixin):
    def __init__(self, id, name, email, picture, stripe_id, user_billing_reset):
        self.id = id
        self.name = name
        self.email = email
        self.picture = picture
        self.stripe_id = stripe_id
        self.user_billing_reset = user_billing_reset
        self.tier = self.get_tier(stripe_id)
        self.locked = self.check_tier_limits() # We lock accounts if they exceed tier limits & prompt users to delete some assets/templates (in layout.html)

    def __str__(self) -> str:
        return f"User {self.id} - Email: {self.email}, Tier: {self.tier}, Locked: {self.locked}"
    
    def check_tier_limits(self):
        user_assets = beatcloud_db.get_user_asset_usage(self.id)
        tier_limit = app.config["TIERS"][self.tier]['asset_limit']
        if user_assets > tier_limit:
            return True

    def get_tier(self, cust_id):
        sub = stripe.Subscription.list(customer=cust_id)
        if sub:
            for s in sub.data: # may have multiple (old etc)
                sub_status = s.status
                if sub_status not in ['active', 'trialing']:
                    print("Inactive subscription")
                else:
                    # Reset usage bcus its first time user logging in since next billing cycle started (s.current_peroid_end has changed)
                    if s.current_period_end > self.user_billing_reset:
                        beatcloud_db.set_user_billing_reset(self.id, s.current_period_end)
                        self.user_billing_reset = s.current_period_end
                        # reset usage to 0
                        beatcloud_db.set_user_video_usage(self.id, 0)
                    elif s.current_period_end < self.user_billing_reset: # s.current_period_end <= self.user_billing_reset
                        print("****STRIPE PERIOD RESET END IS BEFORE DB USER_BILLING_RESET****")
                        self.user_billing_reset = s.current_period_end
                        beatcloud_db.set_user_billing_reset(self.id, s.current_period_end)
                    # else == means that stripe & ddb are inline & no changes need to be made

                    prod_id = s.plan.product
                    prod = stripe.Product.retrieve(prod_id)
                    return prod.metadata.tier
        else:
            # free user - check if billing date passed, reset usage & set renewal to 30 days from now
            now = datetime.now().timestamp()
            if self.user_billing_reset <= now:
                month_from_now = int((datetime.now().replace(hour=0, minute=0, second=0) + timedelta(days=30)).timestamp())
                beatcloud_db.set_user_billing_reset(self.id, month_from_now)
                beatcloud_db.set_user_video_usage(self.id, 0)
                self.user_billing_reset = month_from_now
            return 'free'
    
####
#  Imports
from .routes import *