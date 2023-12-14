import json
from shotstack_sdk.model.video_asset import VideoAsset
from shotstack_sdk.model.image_asset import ImageAsset
from shotstack_sdk.model.audio_asset import AudioAsset
from shotstack_sdk.model.clip import Clip
from shotstack_sdk.model.track import Track
from shotstack_sdk.model.timeline import Timeline
from shotstack_sdk.model.output import Output
from shotstack_sdk.model.edit import Edit
from shotstack_sdk.model.s3_destination import S3Destination
from shotstack_sdk.model.s3_destination_options import S3DestinationOptions
from shotstack_sdk.model.thumbnail import Thumbnail

class FXClip():
    style = None
    opacity = 0
    path = None
    duration = -1
    premium = False # only allow certain users to use
    transparent = False # for using .mov

    def __init__(self, type, opacity) -> None:
        # Set properties based on chosen clip
        if type == "dust":
            self.type = "dust"
            self.duration = 10.0
            self.tiers = ['unlimited']
        elif type == "scratch":
            self.type = "scratch"
            self.duration = 10.0
            self.tiers = ['unlimited']
        elif type == "tape":
            self.type = "tape"
            self.duration = 7.0
            self.tiers = ['plus', 'unlimited']
        elif type == "digital":
            self.type = "digital"
            self.duration = 10.0
            self.tiers = ['unlimited']
        elif type == "light":
            self.type = "light"
            self.duration = 10.0
            self.tiers = ['plus', 'unlimited']
        else:
            raise ValueError(f"Invalid FX type. Expected ['dust', 'scratch', 'tape', 'digital', 'light'], got {type}.")
        
        # Common attributes
        self.opacity = opacity
        self.filename = f"{self.type}.mp4" # e.g. Dust.mp4


#######################------------------------------VISUALIZERS
class VisualizerFactory:
    @staticmethod
    def getVisualizer(id, user_id, title, quality, fx, base_image=None, base_video=None):
        #Determine which Visualizer
        # no_fx = fx is None
        dim = (1920,1080) if quality != "720" else (1280, 720) # Improve for shotstack

        if (fx is not None and base_image is not None): #there is some fx & image
            return StillCompositeVisualizer(id, user_id, title, dim, base_path=base_image, base_type='image', fx=fx)
        elif (fx is not None and base_video is not None): #there is some fx & video
            return LoopCompositeVisualizer(id, user_id, title, dim, base_path=base_video, base_type='video', fx=fx)
        elif (fx is None and base_image is not None): #there is NO fx & an image
            return StillVisualizer(id, user_id, title, dim, base_path=base_image, base_type='image', fx=fx)
        elif (fx is None and base_video is not None): #there is NO fx & a video
            return LoopVisualizer(id, user_id, title, dim, base_path=base_video, base_type='video', fx=fx)
        else:
            print(f"Cannot create a Visualizer with the following parameters: FX: {fx}, BaseImage: {base_image}, BaseVideo: {base_video}")
            return None
           

class Visualizer:
    def __init__(self, v_id=None, u_id=None, title=None, dim=(1280, 720), base_path=None, base_type=None, fx=None, dt=None, status=None, _state=None):
        if _state:
            self.__dict__.update(_state)
        else:
            # Meta data
            self.id = v_id
            self.user_id = u_id
            self.title = title
            self.datetime = dt
            self.status = status
            self.dimensions = dim 
            self.fps = 24 # TODO get 60 working
            self.audio_ext = "mp3" # TODO wav if BC plus
            self.audio_path = None 
            self.audio_duration = -1
            self.base_type = base_type # 'video' or 'image' - needed for probing duration for shotstack looping
            self.base_path = base_path # Path to Image or Video in TMP dir
            self.base_duration = -1 # if base is video
            # Components
            self.fx = fx  # FXClip object
            # Paths
            self.base_url = None # image or video-path
            self.audio_url = None # uploaded audio file
            self.layers_url = None
            self.title_url = None
            self.output_url = None

    def __str__(self):
        return f"{type(self).__name__} for {self.title}, ID: {self.id}, User: {self.user_id}"     

    def __repr__(self):
        return f"{type(self).__name__}({self.id}, {self.id}, {self.user_id})"
    
    def to_json(self):
        self.VisualizerType = type(self).__name__
        j = json.dumps(self, default=lambda self: self.__dict__)
        return j
            
    @staticmethod
    def from_json(json_str):
        data = json.loads(json_str)
        visualizer_type = data.pop("VisualizerType", "Visualizer")
        
        # Ensure that the visualizer type is a valid subclass (or the class itself)
        cls = globals().get(visualizer_type)
        if cls is None or not issubclass(cls, Visualizer):
            raise ValueError(f"Invalid VisualizerType: {visualizer_type}")
        return cls(_state=data)
        
#------------------------ Shared functions for visualizer rendering
    def get_shotstack_destination_info(self):
        s3_destination_options = S3DestinationOptions(
            region = 'eu-west-2',
            # bucket = 'beatcloud-production',
            bucket = 'beatcloud-sandbox',
            prefix = f'media/{self.user_id}/videos/{self.id}',
            filename = f'{self.id}'
        )

        s3_destination = S3Destination(
            provider = 's3',
            options = s3_destination_options
        )
        return s3_destination

    def ss_get_common_tracks(self):
        all_tracks = []
        ## Title Image
        if self.show_title:
            title_asset = ImageAsset(
                src = self.title_url,
            )
            title_clip = Clip(
                asset = title_asset,
                start = 0.0, # start
                length = self.audio_duration
            )
            title_track = Track(clips=[title_clip])
            all_tracks.append(title_track)

        ### User layers
        if self.contains_layers:
            layers_asset = ImageAsset(
                src = self.layers_url,
            )
            layers_clip = Clip(
                asset = layers_asset,
                start = 0.0, # start
                length = self.audio_duration
            )
            layers_track = Track(clips=[layers_clip])
            all_tracks.append(layers_track)
        return all_tracks
    
    def ss_create_output(self, all_tracks):
        timeline = Timeline(tracks=all_tracks)
        thumbnail = Thumbnail(
            capture = 1.0,
            scale=0.5
        )

        output = Output(
            format = 'mp4',
            resolution = 'hd', # 'sd' - 1024px x 576px @ 25fps 'hd' - 1280px x 720px @ 25fps '1080' - 1920px x 1080px @ 25fps
            quality = 'high', # see if improves audio quality
            thumbnail = thumbnail,
            destinations = [self.get_shotstack_destination_info()]
        )

        final_edit = Edit(
            timeline = timeline,
            output = output
        )
        return final_edit

#------------------------ Visualiser Sub-classes 
class CompositeVisualizer(Visualizer):
    def loop_fx_asset(self):
        clips = []
        start = 0.0
        fx_duration = self.fx["duration"]
        fx_opacity = float(self.fx["opacity"])
        fx_asset = VideoAsset(
            src = self.fx_url, # can no longer have self.fx.url as self.fx turns into a dict when json encoded
            volume = 0.0
        )

        while start + fx_duration < self.audio_duration:
            base_clip = Clip(
                asset = fx_asset,
                start = start, # start
                length = fx_duration,
                opacity = fx_opacity
            )
            clips.append(base_clip)
            start = start + fx_duration

        # add final looping clip
        base_clip = Clip(
            asset = fx_asset,
            start = start, # start
            length = self.audio_duration - start,
            opacity = fx_opacity
        )
        clips.append(base_clip)
        return clips
    
class StillVisualizer(Visualizer):
    def get_ss_edit(self):
        # Gets title & layer tracks
        all_tracks = self.ss_get_common_tracks() # order: [title_track, layers_track, fx_track, base_track, audio_track]

        # Still base
        base_track = self.get_still_base_track()
        all_tracks.append(base_track)

        ### Audio
        audio_asset = AudioAsset(
            src = self.audio_url,
        )
        audio_clip = Clip(
            asset = audio_asset,
            start = 0.0, 
            length = self.audio_duration
        )
        audio_track = Track(clips=[audio_clip])
        all_tracks.append(audio_track)

        ## All
        final_edit = self.ss_create_output(all_tracks)
        return final_edit
    
    def get_still_base_track(self):
        base_asset = ImageAsset(
            src = self.base_url,
        )
        base_clip = Clip(
            asset = base_asset,
            start = 0.0, # start
            length = self.audio_duration
        )
        # Create track
        base_track = Track(clips=[base_clip])
        return base_track
    
    def get_cm_edit(self):
        cm_template_id = '18437314-711d-4e93-a8ad-0d1efb15e8df'
        options = {
            'template_id':cm_template_id,
            'modifications': {
                "BASE": self.base_url,
                "LAYERS": self.layers_url,
                "TITLE": self.title_url,
                "AUDIO FILE": self.audio_url,
                "duration":self.audio_duration, # NEED THIS INCASE VIDEO CLIP IS LONGER THAN AUDIO
                "frame_rate":1
            }
        }
        return options

class LoopVisualizer(Visualizer):
    def get_ss_edit(self):
        all_tracks = self.ss_get_common_tracks() # order: [title_track, layers_track, fx_track, base_track, audio_track]

        # Loop base
        base_track = self.get_loop_base_track()
        all_tracks.append(base_track)

        ### Audio
        audio_asset = AudioAsset(
            src = self.audio_url,
        )
        audio_clip = Clip(
            asset = audio_asset,
            start = 0.0, 
            length = self.audio_duration
        )
        audio_track = Track(clips=[audio_clip])
        all_tracks.append(audio_track)

        ## All
        final_edit = self.ss_create_output(all_tracks)
        return final_edit

    def get_loop_base_track(self):
        ### Base
        asset = VideoAsset(
            src = self.base_url,
            volume = 0.0,
        )
        clips = []
        start = 0.0

        while start + self.base_duration < self.audio_duration:
            base_clip = Clip(
                asset = asset,
                start = start, # start
                length = self.base_duration
            )
            clips.append(base_clip)
            start = start + self.base_duration

        # add final looping clip
        base_clip = Clip(
            asset = asset,
            start = start, # start
            length = self.audio_duration - start
        )
        clips.append(base_clip)
        # Create track
        base_track = Track(clips=clips)
        return base_track

    def get_cm_edit(self):
        cm_template_id = '6447543a-4015-4152-abb7-4fa190b0928b'
        options = {
            'template_id':cm_template_id,
            'modifications': {
                "BASE": self.base_url,
                "LAYERS": self.layers_url,
                "TITLE": self.title_url,
                "AUDIO FILE": self.audio_url,
                "duration":self.audio_duration, # NEED THIS INCASE VIDEO CLIP IS LONGER THAN AUDIO
                "frame_rate":24 #change with tier or selection
            }
        }
        return options

class StillCompositeVisualizer(StillVisualizer, CompositeVisualizer):
    def get_ss_edit(self):
        all_tracks = self.ss_get_common_tracks() # order: [title_track, layers_track, fx_track, base_track, audio_track]

        # Loop FX
        fx_clips = self.loop_fx_asset()
        # Create track
        fx_track = Track(clips=fx_clips)
        all_tracks.append(fx_track)

        # Still base
        base_track = self.get_still_base_track()
        all_tracks.append(base_track)

        ### Audio
        audio_asset = AudioAsset(
            src = self.audio_url,
        )
        audio_clip = Clip(
            asset = audio_asset,
            start = 0.0, 
            length = self.audio_duration
        )
        audio_track = Track(clips=[audio_clip])
        all_tracks.append(audio_track)

        ## All
        final_edit = self.ss_create_output(all_tracks)
        return final_edit

    def get_cm_edit(self):
        cm_template_id = '1e7d2774-ff97-4e29-a090-59c9ee423155'
        options = {
            'template_id':cm_template_id,
            'modifications': {
                "BASE": self.base_url,
                "FX": self.fx_url,
                "FX.opacity":int(float(self.fx["opacity"])*100),
                "LAYERS": self.layers_url,
                "TITLE": self.title_url,
                "AUDIO FILE": self.audio_url,
                "duration":self.audio_duration, # NEED THIS INCASE VIDEO CLIP IS LONGER THAN AUDIO
                "frame_rate":15
            }
        }
        return options

class LoopCompositeVisualizer(LoopVisualizer, CompositeVisualizer):
    def get_ss_edit(self):
        all_tracks = self.ss_get_common_tracks() # order: [title_track, layers_track, fx_track, base_track, audio_track]

        # Loop FX
        fx_clips = self.loop_fx_asset()
        # Create track
        fx_track = Track(clips=fx_clips)
        all_tracks.append(fx_track)

        # Loop base
        base_track = self.get_loop_base_track()
        all_tracks.append(base_track)

        ### Audio
        audio_asset = AudioAsset(
            src = self.audio_url,
        )
        audio_clip = Clip(
            asset = audio_asset,
            start = 0.0, 
            length = self.audio_duration
        )
        audio_track = Track(clips=[audio_clip])
        all_tracks.append(audio_track)

        ## All
        final_edit = self.ss_create_output(all_tracks)
        return final_edit
    
    def get_cm_edit(self):
        cm_template_id = '6b996af8-ead4-46c1-a1f4-2a00abcd12d3'
        options = {
            'template_id':cm_template_id,
            'modifications': {
                "BASE": self.base_url,
                "FX": self.fx_url,
                "FX.opacity":int(float(self.fx["opacity"])*100),
                "LAYERS": self.layers_url,
                "TITLE": self.title_url,
                "AUDIO FILE": self.audio_url,
                "duration":self.audio_duration, # NEED THIS INCASE VIDEO CLIP IS LONGER THAN AUDIO
                "frame_rate":24
            }
        }
        return options
