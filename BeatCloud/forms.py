from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import StringField, BooleanField, SelectField, IntegerField, SubmitField, TextAreaField, DecimalField
from wtforms.validators import DataRequired, Length, URL, NumberRange

class CreateVidForm(FlaskForm):
    v_id = StringField('v_id', validators=[DataRequired()], render_kw={'id':'v_id', 'class':'d-none'})
    beatName = StringField('Beat Name', validators=[DataRequired(), Length(max=30)], render_kw={'class' : 'shadow form-control preview-control', 'placeholder' : 'e.g. Stars'})
    title_font = SelectField('Title font', choices=[], render_kw={'class':'preview-control title_control'})
    title_font_size = IntegerField('Title font size', validators=[DataRequired()], render_kw={'class' : 'form-control preview-control px-3 title_control', 'value' : 72})
    title_font_colour = StringField('Title font colour', validators=[DataRequired()], render_kw={'id':'title_font_colour','class' : 'form-control px-3 title_control', 'value' : '#ffffff', 'readonly':'readonly'})
    title_ypos = IntegerField('Title Y position', validators=[DataRequired(), NumberRange(min=-540, max=540)], render_kw={'class' : 'form-control preview-control px-3 title_control', 'value' : 0, 'min':-540, 'max':540})
    # shotTitle is not title_control! it will disable itself if this is applied to its classes.
    showtitle = BooleanField('Show title', render_kw={'class' : 'form-check-input', 'type' : 'checkbox', 'id' : 'chkShowTitle', 'checked' : 'checked', 'onchange' : 'preview_title()'})
    imgURL = StringField('Image URL', validators=[DataRequired(), URL()], render_kw={'class' : 'form-control text-muted visualizer_base_input', 'placeholder' : 'Or paste URL here', 'id' : 'urlTextBox'})
    imgFile = FileField('Image File', validators=[DataRequired()], render_kw={'id': 'fileUpload', 'class' : "form-control visualizer_base_input visually-hidden",  'accept': '.jpg,.jpeg,.png'})
    beatFile = FileField(render_kw={'class' : "shadow form-control", 'accept': '.mp3,.wav'}, validators=[DataRequired()])
    
    fx_select = SelectField('FX Type', choices=[('none', 'None'), ('dust', 'Dust'), ('scratch', 'Scratch'), ('digital', 'Digital'), ('light', 'Light'), ('tape', 'Tape')], render_kw={'class':'visually-hidden', "id":"fx_dropdown"})
    
    fx_opacity = DecimalField('FX Opacity', validators=[DataRequired(), NumberRange(min=0, max=1)], render_kw={'id':'form_fx_opacity', 'class':'visually-hidden', 'readonly':'readonly', 'value':'0.3'})
    add_blur = BooleanField(render_kw={'class' : 'form-check-input','type' : 'checkbox', 'id' : 'chkBlur', 'checked' : 'checked'})
    blur_level = IntegerField('Blur amount', validators=[DataRequired()], render_kw={'class' : 'form-control visually-hidden', 'value' : 5})
    video_quality = SelectField('Video Quality', choices=[('720', '720p'), ('1080', '1080p')], render_kw={'class':'visually-hidden', "id":"quality_select"})

class UploadForm(FlaskForm):
    title = StringField("title", validators=[DataRequired()], render_kw={'class':"shadow form-control", 'id':"video_title", 'placeholder':"My track"})
    videoid = StringField("videoid", validators=[DataRequired()], render_kw={'class':'visually-hidden'})
    description = TextAreaField("desc", validators=[DataRequired()], render_kw={'class':"shadow form-control", 'id':"video_desc", 'placeholder':"Describe the track", 'style':'min-height:8rem;'})
    visibility = SelectField("visibility", choices=[('private', 'Private'), ('public', 'Public')], render_kw={'class':'shadow form-select'})
    keywords = StringField("keywords", render_kw={'class':'visually-hidden'})
    submit = SubmitField('Upload to YouTube', render_kw={'id':'btn_submit_upload', 'class':'shadow btn btn-outline-primary  btn-main  mx-auto mt-4'})
