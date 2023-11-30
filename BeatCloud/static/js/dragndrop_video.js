  var USING_VIDEO = false, VIDEO_PATH;
  let video_dropArea = document.getElementById('video-drop-area')
  let video_input = document.getElementById('input_video')

  $(document).ready(function(){
    $('#video_progress_container').hide();
  })

  ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    video_dropArea.addEventListener(eventName, preventDefaults, false)
  })

  ;['dragenter', 'dragover'].forEach(eventName => {
    video_dropArea.addEventListener(eventName, highlight, false)
  })

  ;['dragleave', 'drop'].forEach(eventName => {
    video_dropArea.addEventListener(eventName, unhighlight, false)
  })

  video_dropArea.addEventListener('drop', handleVideoDrop, false)

  video_input.onclick = function () {
    this.value = null;
  };
  video_input.onchange = function () {
    handleVideoFiles(this.files);
  };

  //all
  function highlight(e) {
    this.classList.add('bg-secondary', 'text-white');
    $('#video-drop-icon').addClass('text-white');
    // this.classList.remove('bg-info');
  }

  function unhighlight(e) {
    this.classList.remove('bg-secondary', 'text-white');
    $('#video-drop-icon').removeClass('text-white');
    // this.classList.remove('bg-info');
  }

  function preventDefaults (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  //Videos (create.html)
  function handleVideoDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;

    handleVideoFiles(files);
  }

  function handleVideoFiles(files) {
    // change to only 1!
    ([...files]).forEach(uploadVideoFile);
  }

  function show_progress(){
    // Clicked create
    $('#video_input').fadeOut("fast", function(){
      $('#video_progress_container').fadeIn("fast");
   });
  }

  function hide_progress(){
    // Clicked create
    $('#video_progress_container').fadeOut("fast", function(){
      $('#video_input').fadeIn("fast");
   });
  }

  function uploadVideoFile(file) {
    var url = `/visualizers/${p_v_id}/preview`;
    var xhr = new XMLHttpRequest();
    var formData = new FormData();
    xhr.open('PUT', url, true);

    //Fire change event
    let input = document.getElementById('video_input');
    var event = new Event('change');
    input.value = file.name;
    input.dispatchEvent(event);

    //Reset image controls & filters on images
    set_base("video");
    $(document).trigger('BCBaseUploadStarted');

    //progress
    show_progress()
    // document.getElementById('video_progress_container').classList.remove("visually-hidden");
    
    xhr.upload.addEventListener('progress', function (e) {
      var filesize = file.size;

      if (e.loaded <= filesize) {
          var percent = Math.round(e.loaded / filesize * 100);
          $('#video_progress').width(percent + '%');
      }

      if(e.loaded == e.total){
          $('#video_progress').width(100 + '%');
      }
    });

    xhr.addEventListener('readystatechange', function(e) {
      if (xhr.readyState == 4 && xhr.status == 202) {
        console.log("Started GIF render")
        r = JSON.parse(xhr.responseText); //Response data
        checkGIFTaskStatus(r.task_id, file.name)
        VIDEO_PATH = r.base_path; //might be used in create form. Not sure.
      }
      else if (xhr.readyState == 4 && xhr.status == 413) {
        // 413 FILE TOO LARGE
        //Fire change event
        let input = document.getElementById('video_input');
        var event = new Event('change');
        input.value = "";
        input.dispatchEvent(event);
        // Error. Inform the user
        showAlert("danger", "<strong>Error:</strong> Uploaded file too large. Maximum File Upload size is <strong>300MB</strong>", true);
        $('#video_progress').width(0 + '%');
        // document.getElementById('video_progress_container').classList.add("visually-hidden");
        hide_progress();
        //Trigger uploaded event:
        $(document).trigger('BCBaseUploadFinished');
      }
      else if (xhr.readyState == 4 && xhr.status != 202) {
        // Other errors
        //Fire change event
        let input = document.getElementById('video_input');
        var event = new Event('change');
        input.value = "";
        input.dispatchEvent(event);
        // Error. Inform the user
        showAlert("danger", `Error uploading video: <strong>${xhr.responseText}</strong>`, false);
        $('#video_progress').width(0 + '%');
        // document.getElementById('video_progress_container').classList.add("visually-hidden");
        hide_progress();
        //Trigger uploaded event:
        $(document).trigger('BCBaseUploadFinished');
      }
    })

    formData.append('video-file', file)
    formData.append('id', p_v_id) // Visualizer ID
    xhr.send(formData)
  }

function get_frames_preview(){
  console.log("Updating frames");
  USING_VIDEO = true;
  // $('#chkBlur').attr('checked', false);  // Temp disabling as it would affect if user changes back to image base
  $('#chkBlur').prop('disabled', true);

  var path = add_dummy("/visualizers/" + p_v_id + "/preview");
  $('#img_preview').attr("src", path);
  $('#modal_gif_preview').attr("src", path);

  document.getElementById('random_frame_notifier').classList.remove("visually-hidden");
}

function refresh_frames(){
  var url = `/visualizers/${p_v_id}/preview/refresh`;
  var xhr = new XMLHttpRequest();
  var formData = new FormData();
  xhr.open('POST', url, true);

  // loading icon
  document.getElementById("ico_loading").style.opacity = 1;

  xhr.addEventListener('readystatechange', function(e) {
    if (xhr.readyState == 4 && xhr.status == 202) {
      // call preview with new video
      checkGIFRefreshStatus(JSON.parse(xhr.responseText).task_id, );
    }
    else if (xhr.readyState == 4 && xhr.status != 200) {
      console.log(xhr.responseText);
      // Error. Inform the user
      showAlert("danger", `<strong>Error</strong> - Could not refresh frames.`)
    }
  })

  formData.append('video_id', p_v_id) //video id
  xhr.send(formData)
}

function checkGIFTaskStatus(taskId, filename) {
  fetch(`/check_task/${taskId}`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'SUCCESS') {
        console.log('Task complete!');
        // The task is complete, fetch the image
        fetchGIFImage(filename);
      } else if (data.status === 'FAILURE') {
        console.error('Task failed:', data.error);
        $('#ico_loading').css('opacity', '0');
        showAlert("danger", `Preview task failed. Please contact help@usebeatcloud.com quoting preview ID: ${taskId}`)
      } else {
        console.log('Task still running...');
        $('#ico_loading').css('opacity', '1');
        // If the task is still running, check again after a delay
        setTimeout(() => checkGIFTaskStatus(taskId, filename), 1000);
      }
    })
    .catch(error => console.error('Error checking task status:', error));
}
function checkGIFRefreshStatus(taskId) {
  fetch(`/check_task/${taskId}`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'SUCCESS') {
        // The task is complete, fetch the image
        
        get_frames_preview();
        $('#ico_loading').css('opacity', '0');
      } else if (data.status === 'FAILURE') {
        
        $('#ico_loading').css('opacity', '0');
        showAlert("danger", `Preview task failed. Please contact help@usebeatcloud.com quotin: 'Preview ID: ${taskId} & Error: ${data.error}'`)
      } else {
        // Still running, check again after a delay
        
        $('#ico_loading').css('opacity', '1');
        setTimeout(() => checkGIFRefreshStatus(taskId), 1000);
      }
    })
    .catch(error => console.error('Error checking task status:', error));
}

function fetchGIFImage(filename) {
  get_frames_preview();

  // Done. Inform the user
  console.log("successfully uploaded");
  hide_progress();
  
  // Do after fade:
  setTimeout(function(){
    $('#video_progress').width(0 + '%');
    $('#video_upload_status').hide().after($('#video_upload_success'));
  }, 1000);

  $('#ico_loading').css('opacity', '0');

  showAlert("success", "Successfully uploaded " + filename + "!", true);

  //Trigger uploaded event:
  $(document).trigger('BCBaseUploadFinished');
}
