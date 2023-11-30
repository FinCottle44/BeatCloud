var interval
var ready_to_post = false;
var user_tags = [];

// Submit post on submit
$('#form').on('submit', function(event){
  event.preventDefault();
  post_data();
});


function post_data(){
  // ensure ready to send
  if (!ready_to_post){
    showAlert("danger", "Error - Not ready to post, check you've uploaded a base, title & audio file.", false);
    return;
  }

  // Show spinner
  show_spinner();

  // form data
  var formElement = document.getElementById('form');
  fd = new FormData(formElement);
  font = $('#sl_title_font').find(":selected").val();
  fd.append('title_font', font);
  if (USING_VIDEO) {
    fd.append('video_path', VIDEO_PATH)
  }

  // send
  $.ajax({
    url: `/visualizers/${p_v_id}`,
    type: 'post',
    data: fd,
    processData: false,
    contentType: false,
    success: function(data, textStatus) {
      //Hide create button & show progress bar
      // document.getElementById("btnCreate").setAttribute("disabled", "disabled");      
      // progress_interval = setInterval(function() {check_progress();}, 3000);
      
      //prevent changing of background by preventing opening of modal
      $("#preview-container").prop("onclick", null).off("click");
      
      showAlert("success", "Success! Video added to processing queue. You will now be redirected!", true)
      
      //  redirect to all visualizers view
      console.log("Redirecting!")
      setTimeout(function(){
        window.location = "/visualizers"
      }, 1500);
    },
    // on failure show message for whatever reason
    error: function(data, textStatus) {
      console.log("big stinky error");
      showAlert("danger", "An error ocurred processing this video:<strong> " + data.responseText + "</strong>.", false);
      setTimeout(hide_spinner, 2000);
    }
  });
}


// FADING IN::::: https://stackoverflow.com/questions/5248721/jquery-replacewith-fade-animate
function show_spinner(){
  // Clicked create
  $('#btnCreate').fadeOut("fast", function(){
    var div = $('<div id="create_spinner" class="lds-ring"><div></div><div></div><div></div><div></div></div>').hide();
    $(this).replaceWith(div);
    $('#create_spinner').fadeIn("fast");
 });
}

function hide_spinner(){
  // Clicked create
  $('#create_spinner').fadeOut("fast", function(){
    var div = $('<button class="btn btn-lg btn-primary w-50 mx-auto" type="submit" id="btnCreate">Create</button>').hide();
    $(this).replaceWith(div);
    $('#btnCreate').fadeIn("fast");
 });
}

// let successful_call_counter = 0;
// function check_progress() {
//   $.ajax({
//       url: `/visualizers/${p_v_id}/progress`,
//       type: "GET",
//       success: function(data) {
//           var progress = parseFloat(data);
//           if(progress >= 100) {
//             // Wait a second and redir
//             setTimeout(function() {
//               window.location.href = "/visualizers/" + p_v_id;
//             }, 1000)
//           } else if (successful_call_counter == 0) {
//             show_progress(); // First successful call so create and shnow progress bar
//           } else {
//             $('#progbar').css('width', data+'%').attr('aria-valuenow', data);
//           }
//           successful_call_counter += 1
//       },
//       error: function(error) {
//           console.log("Error:", error);
//       }
//   });
// }

function change_img_preview(){
  p_img = document.getElementById('img_preview');
  upl = document.getElementById('imgFileUpload').files[0];
  var reader = new FileReader();
  reader.onload = function(e) {
    p_img.src = e.target.result;
  }
  reader.readAsDataURL(upl)
}

// research if need as using flask 
$(function() {
    // This function gets cookie with a given name
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    var csrftoken = getCookie('csrftoken');

    /*
    The functions below will create a header with csrftoken
    */

    function csrfSafeMethod(method) {
        // these HTTP methods do not require CSRF protection
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }
    function sameOrigin(url) {
        // test that a given url is a same-origin URL
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }

    $.ajaxSetup({
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type) && sameOrigin(settings.url)) {
                // Send the token to same-origin, relative URLs only.
                // Send the token only if the method warrants CSRF protection
                // Using the CSRFToken value acquired earlier
                xhr.setRequestHeader("X-CSRFToken", csrftoken);
            }
        }
    });

});

function clearImgURLInput(){
  document.getElementById("urlTextBox").value = "";
}

function clearImgFileInput(){
  document.getElementById("fileUpload").value = '';
}

function AddTag(){
  var tag_input = document.getElementById("tag_input");
  var tag = tag_input.value;
  if (tag.trim() != ""){
    var tags_box = document.getElementById("tags_box");
    var delete_button = '<svg onclick="RemoveTag(this)" xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-x-octagon-fill icon-close ml-2" viewBox="0 0 16 16"><path d="M11.46.146A.5.5 0 0 0 11.107 0H4.893a.5.5 0 0 0-.353.146L.146 4.54A.5.5 0 0 0 0 4.893v6.214a.5.5 0 0 0 .146.353l4.394 4.394a.5.5 0 0 0 .353.146h6.214a.5.5 0 0 0 .353-.146l4.394-4.394a.5.5 0 0 0 .146-.353V4.893a.5.5 0 0 0-.146-.353L11.46.146zm-6.106 4.5L8 7.293l2.646-2.647a.5.5 0 0 1 .708.708L8.707 8l2.647 2.646a.5.5 0 0 1-.708.708L8 8.707l-2.646 2.647a.5.5 0 0 1-.708-.708L7.293 8 4.646 5.354a.5.5 0 1 1 .708-.708z"/></svg>'

    // <span class="badge rounded-pill bg-light">Light</span>

    tag_span = document.createElement("span");
    tag_span.classList.add("badge", "rounded-pill", "bg-secondary", "m-1", "fw-light");
    tag_span.innerHTML = tag.toLowerCase() + delete_button;
    tags_box.appendChild(tag_span);
    
    // For use in user templates in templates.js
    user_tags.push(tag);
  }
  tag_input.value = "";
  tag_input.focus();
  return;
}

function RemoveTag(e){
  e.parentElement.remove()
  user_tags = user_tags.filter(item => item !== e.parentElement.textContent); 
}

//Content loaded function
document.addEventListener('DOMContentLoaded', function() {
  //ensure 1 of 3 base types selected
  const inputs = Array.from(
    document.querySelectorAll('.visualizer_base_input')
  );

  const inputListener = e => {
    inputs
      .filter(i => i !== e.target)
      .forEach(i => (i.required = !e.target.value.length));
  };

  inputs.forEach(i => i.addEventListener('change', inputListener));

  //Make invisble form dropdown change on button press for FX
  $('.fx-tab').on('shown.bs.tab', function(e) {
    t = e.target;
    v = $(t).attr("data-value");
    //change preview
    switch (v) {
      case 'dust':
        $('#fx_preview').removeClass('visually-hidden');
        $('#fx_preview').attr('src', '/static/img/fx-preview/dust_preview.gif');
        $('#fx_opacity').prop('disabled', false);
        break;
      case 'scratch':
        $('#fx_preview').removeClass('visually-hidden');
        $('#fx_preview').attr('src', '/static/img/fx-preview/scratch_preview.gif');
        $('#fx_opacity').prop('disabled', false);
        break;
      case 'digital':
        $('#fx_preview').removeClass('visually-hidden');
        $('#fx_preview').attr('src', '/static/img/fx-preview/digital_preview.gif');
        $('#fx_opacity').prop('disabled', false);
        break;
      case 'light':
        $('#fx_preview').removeClass('visually-hidden');
        $('#fx_preview').attr('src', '/static/img/fx-preview/light_preview.gif');
        $('#fx_opacity').prop('disabled', false);
        break;
      case 'tape':
        $('#fx_preview').removeClass('visually-hidden');
        $('#fx_preview').attr('src', '/static/img/fx-preview/tape_preview.gif');
        $('#fx_opacity').prop('disabled', false);
        break;
      default:
        $('#fx_preview').addClass('visually-hidden');
        $('#fx_opacity').prop('disabled', true);
    }

    $('#fx_dropdown').val(v);
  })

  //FX Opacity
  $('#fx_opacity').on('change', function(e){
    val = e.target.value;
    $('#fx_preview').css('opacity', val);
    $('#fx_opacity_label').text(val);
    $('#form_fx_opacity').val(val);
  })

  //Make invisble form dropdown change on button press for Quality
  $('.quality-check').on('change', function(e) {
    t = e.target;
    v = $(t).attr("value");
    $('#quality_select').val(v);
  })
});

function watchColorPicker(event) {
  $('#title_font_colour').val(this.value);
}

// Add dummy to the end of filenames so that they are not cached by browser (mainly preview files)
function add_dummy(url) {
  var dummy = Math.random().toString(36).slice(2, 7); // generate a 5-char random string
  return url + "?dummy=" + dummy; // append it to the URL as a query parameter
}

function showAlert(type, message, autoDismiss) {
  // Create a dismissible Bootstrap alert
  let alert = $('<div class="alert alert-dismissible fade show" role="alert">'
               + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>'
               + '</div>');

  // Set the type and message
  alert.addClass('alert-' + type);
  alert.prepend(message);
  if (type == "danger"){
    alert.prepend('<i class="bi bi-exclamation-triangle-fill px-2"></i>');
  }
  else {
    alert.prepend('<i class="bi bi-check-circle px-2"></i>');
  }

  // Append the alert to your DOM - replace '#alert-container' with the selector of your container
  $('#alert-container').append(alert);

  // If autoDismiss is true and the type is 'success', set a timeout to dismiss the alert
  if (autoDismiss) {
      setTimeout(function() {
          alert.alert('close');
      }, 5000); // 5 seconds
  }
}



