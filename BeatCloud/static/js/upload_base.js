$(document).ready(function() {
    // Clear opposite input if one used
    $('#urlTextBox').on("change", function(){
        $('#fileUpload').val("");
    });
    $('#fileUpload').on("change", function() {
        $('#urlTextBox').val("")
    });
    
    // init with image
    set_base("image");

    // blur level update hidden element
    $('#range_blurlevel').on("change", function (){
        $('#blur_level').val($(this).val());
    });    
})

// Prevent base submission whilst uploading (mainly for video)
$(document).on("BCBaseUploadFinished", function () {
    console.log("Upload finished");
    ready_to_post = true;
});

$(document).on("BCBaseUploadStarted", function () {
    console.log("Upload started");
    ready_to_post = false;
});

// Central function for toggling between video & image background
function set_base(basetype){
    if (basetype == 'image'){
        // do stuff
        USING_VIDEO = false;
        // clear video input#
        $('#video_input').val("");
        $('#video_upload_success').val("");
        // allow blur of background now:
        $('#chkBlur').attr('checked', true);
        $('#chkBlur').prop('disabled', false);
        // Allow filter use
        $('#FilterControls').removeAttr("disabled");
        $('#background_properties').tooltip('disable');
        // Remove GIF refresh link
        document.getElementById('random_frame_notifier').classList.add("visually-hidden");
    } else if (basetype == 'video'){
        // do this stuff
        USING_VIDEO = true;
        // clear im inputs
        $('#fileUpload').val("");
        $('#urlTextBox').val("");
        // prevent filter use:
        $('#FilterControls').attr("disabled","disabled");
        $('#background_properties').tooltip('enable');
        // Reset filter values:
        initFilterValues();
    } else {
        console.log("Invalid base type");
        return;
    }
}

$('#uploadButton').click(function() {
    uploadBackground(p_v_id);
});

$('#chkBlur').on("change", function() {
    var blur = $('#chkBlur').is(':checked');
    if (blur){
        $('#range_blurlevel').removeAttr("disabled");
    }
    else {
        $('#range_blurlevel').attr("disabled", "disabled");
    }
    uploadBackground(p_v_id);
});

$('#range_blurlevel').on("change", function() {
    uploadBackground(p_v_id);
});

function uploadBackground(v_id) { // Images only NOT Videos
    set_base('image');
    var imgUrl = $('#urlTextBox').val();
    var imgFile = $('#fileUpload')[0].files[0];
    var blur = $('#chkBlur').is(':checked');
    var blur_level = $('#range_blurlevel').val();

    // create a FormData object and append either the file or the URL
    var formData = new FormData();
    if (imgFile) {
        formData.append('img-file', imgFile);
        formData.append('blur', blur ? 'true' : 'false');
        formData.append('blur-level', blur_level);
    } else if (imgUrl) {
        formData.append('img-url', imgUrl);
        formData.append('blur', blur ? 'true' : 'false');
        formData.append('blur-level', blur_level);
    } else {
        console.log("No base image supplied");
        return;
    }

    //show loading icon
    document.getElementById("ico_loading").style.opacity = 1;
    // Trigger event
    $(document).trigger('BCBaseUploadStarted');
    
    // Send image to server for processing
    $.ajax({
        url: '/visualizers/' + v_id + '/preview',
        type: 'PUT',
        data: formData,
        processData: false, // tell jQuery not to process the data
        contentType: false, // tell jQuery not to set contentType
        success: function(response) {
            checkBGTaskStatus(response.task_id);
        },
        error: function(data, textStatus) {
            //remove loading spinner
            console.log(data)
            document.getElementById("ico_loading").style.opacity = 0;
            if (data.status == 413){
              showAlert("danger", "<strong>Error:</strong> Uploaded file too large. Maximum File Upload size is <strong>300MB</strong>", true);
            } else {
              // other error
              showAlert("danger", `Error uploading image: <strong>${data.responseText}</strong>`, false)
            }
            //Trigger uploaded event:
            $(document).trigger('BCBaseUploadFinished');
        }
    });
}

function checkBGTaskStatus(taskId) {
    fetch(`/check_task/${taskId}`)
      .then(response => response.json())
      .then(data => {
        if (data.status === 'SUCCESS') {
          // console.log('Task complete!');
          // The task is complete, fetch the image
          fetchBGImage();
        } else if (data.status === 'FAILURE') {
          // console.error('Task failed:', data.error);
          $('#ico_loading').css('opacity', '0');
          showAlert("danger", `Preview task failed. Please contact help@usebeatcloud.com quoting preview ID: ${taskId}`)
        } else {
          // console.log('Task still running...');
          $('#ico_loading').css('opacity', '1');
          // If the task is still running, check again after a delay
          setTimeout(() => checkBGTaskStatus(taskId), 1000);
        }
      })
      .catch(error => console.error('Error checking task status:', error));
  }
  
  function fetchBGImage() {
    // Logic to fetch and display the image goes here
    $('#ico_loading').css('opacity', '0');
    console.log('Task complete. Fetching background image...');
    
    // set im src with url 
    url = `/visualizers/${p_v_id}/preview`;
    var img = new Image();
    src_url = add_dummy(url);

    img.onload = function() {
        // Draw on background modal canvas
        drawImage(ctxBg, img, 0, 0, canvasBg.width, canvasBg.height);
        // Update preview image
        $("#img_preview").attr("src", src_url);
        //remove loading spinner
        document.getElementById("ico_loading").style.opacity = 0;
    }
    img.src = src_url;

    //Image uploaded event:
    $(document).trigger('BCBaseUploadFinished');
  }


//--------DRAG N DROP!!
let image_dropArea = document.getElementById('image-drop-area')
let image_input = document.getElementById('fileUpload')

;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    image_dropArea.addEventListener(eventName, preventDefaults, false)
  })

  ;['dragenter', 'dragover'].forEach(eventName => {
    image_dropArea.addEventListener(eventName, highlight, false)
  })

  ;['dragleave', 'drop'].forEach(eventName => {
    image_dropArea.addEventListener(eventName, unhighlight, false)
  })

  image_dropArea.addEventListener('drop', handleImageDrop, false)

  image_input.onclick = function () {
    this.value = null;
  };
  image_input.onchange = function () {
    handleImageFiles(this.files);
  };

  //all
  function highlight(e) {
    this.classList.add('bg-secondary', 'text-white');
    $('#image-drop-icon').addClass('text-white');
  }

  function unhighlight(e) {
    this.classList.remove('bg-secondary', 'text-white');
    $('#image-drop-icon').removeClass('text-white');
  }

  function preventDefaults (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  //Images (create.html)
  function handleImageDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;

    handleImageFiles(files);
  }

  function handleImageFiles(files) {
    // change to only 1!
    $('#fileUpload').prop("files", files);
    uploadBackground(p_v_id);
  }