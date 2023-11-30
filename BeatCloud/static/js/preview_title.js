//FILE FOR STRICTLY PREVIEWING THE TITLE, NOT THE BACKGROUND
var p_v_id = document.getElementById("v_id").value;
const debounce_interval = 400;

function preview_title(){ //preview the title
  var title = document.getElementById('beatName').value;
  var title_font = document.getElementById('sl_title_font').value;
  var title_font_size = document.getElementById('title_font_size').value;
  var title_font_colour = document.getElementById('title_font_colour').value;
  var title_font_ypos = document.getElementById('title_ypos').value;
  var showTitle = document.getElementById('chkShowTitle').checked;
  var action = `/visualizers/${p_v_id}/title`

  $('#ico_loading').css('opacity', '1'); // Loading icon

  //xhr
  var formData = new FormData();
  var xhr = new XMLHttpRequest();

  if (title == '' || !showTitle){
    $('#title_preview').addClass("visually-hidden");
    $('#ico_loading').css('opacity', '0'); // Loading icon
    return;
  } else {
    $('#title_preview').removeClass("visually-hidden");
  }

  formData.append('title', title);
  formData.append('title_font', title_font)
  formData.append('title_font_size', title_font_size)
  formData.append('showTitle', showTitle)
  formData.append('title_font_colour', title_font_colour)
  formData.append('title_ypos', title_font_ypos)

  xhr.addEventListener('readystatechange', handle_title_response, false);
  xhr.open("PUT", action);
  xhr.send(formData);
}

function handle_title_response(evt){
  var status, text, readyState;

  try {
    readyState = evt.target.readyState;
    text = evt.target.responseText;
    status = evt.target.status;
  }
  catch(e) {
    console.log(e);
    return;
  }

  if (readyState == 4 && status == '202' && evt.target.responseText) {
    id = JSON.parse(evt.target.responseText).task_id
    checkTitleTaskStatus(id);
  }
}

function debounce(func, delay) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      func.apply(this, args);
    }, delay);
  };
}

const debouncedInputChange = debounce(preview_title, debounce_interval);

$(document).ready(function() {
  $(".preview-control").on("input", function(e){ // Doesn't fire programatically unless specifically called
      // preview_title(); 
      debouncedInputChange(e);
  });
  $("#title_font_colour_picker").on("change", function(e){ // not input as would fire too often
      // preview_title();
      debouncedInputChange(e);
  });
  // Font size slider & text input consistency:
  $("#range_fontsize").on("change", function(e){ //'change' uses less bandwidth, but worse experience
      $("#title_font_size").val(this.value);
      // preview_title();
      debouncedInputChange(e);
  });
  $("#title_font_size").on("input", function(){ //'change' uses less bandwidth, but worse experience
      $("#range_fontsize").val(this.value); // fire onchange once^
  });
  // Font y offset slider & text input consistency:
  $("#range_title_ypos").on("change", function(e){ //'change' uses less bandwidth, but worse experience
      $("#title_ypos").val(this.value);
      // preview_title();
      debouncedInputChange(e);
  });
  $("#title_ypos").on("input", function(){ //'change' uses less bandwidth, but worse experience
      $("#range_title_ypos").val(this.value);
  });
  // Disable title controls if not showing title:
  $('#chkShowTitle').on('change', function (e) {
    $('.title_control').prop('disabled', !e.target.checked);
  })
});

function checkTitleTaskStatus(taskId) {
  fetch(`/check_task/${taskId}`)
    .then(response => response.json())
    .then(data => {
      if (data.status === 'SUCCESS') {
        // console.log('Task complete!');
        // The task is complete, fetch the image
        fetchTitleImage();
      } else if (data.status === 'FAILURE') {
        // console.error('Task failed:', data.error);
        $('#ico_loading').css('opacity', '0');
        showAlert("danger", `Preview task failed. Please contact help@usebeatcloud.com quoting preview ID: ${taskId}`)
      } else {
        // console.log('Task still running...');
        $('#ico_loading').css('opacity', '1');
        // If the task is still running, check again after a delay
        setTimeout(() => checkTitleTaskStatus(taskId), 1000);
      }
    })
    .catch(error => console.error('Error checking task status:', error));
}

function fetchTitleImage() {
  // Logic to fetch and display the image goes here
  $('#ico_loading').css('opacity', '0');
  console.log('Fetching image...');
  // set im src with url 
  
  var title_img = document.getElementById("title_preview")
  var modal_title = document.getElementById("modal_title_preview")
  var dummy = Math.random().toString(36).substr(2, 5); //append to prevent caching of image
  
  url = `/visualizers/${p_v_id}/title`;
  title_img.src = url + "?dummy=" + dummy;
  modal_title.src = url + "?dummy=" + dummy;
}

function show_fx_preview(show){
  if (show) {
    document.getElementById('fx_preview').classList.remove("visually-hidden");
  }
  else{
    document.getElementById('fx_preview').classList.add("visually-hidden");
  }
}
