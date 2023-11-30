var upload_poll_interval;
document.getElementById("btn_submit_upload").addEventListener("click", function(event){
  event.preventDefault();
  upload_yt_video();
});

function upload_yt_video(){
  var formElement = document.getElementById('yt_form');
  fd = new FormData(formElement);

  $.ajax({
    url: `/visualizers/${v_id}/upload`,
    type: 'post',
    data: fd,
    processData: false,
    contentType: false,
    success: function(data, textStatus) {
      showAlert("info", "Video upload sucessfully started! You can safely leave this page.", true)
      $('#btn_submit_upload').replaceWith('<div id="upload_spinner" class="lds-ring"><div></div><div></div><div></div><div></div></div>')
      // upload_poll_interval = setInterval(poll_db, 2000, v_id); // Start poll interval
      setTimeout(poll_db, 5000, v_id);
    },
    error: function(data, textStatus) {
      console.log(data);
      showAlert("danger", "An error ocurred uploading the video:<strong> " + data.responseText + "</strong>.", false)
    }
  });
}

function poll_db(v_id){
  $.ajax({
    url: `/visualizers/${v_id}/upload/status`,
    type: 'get',
    processData: false,
    contentType: false,
    success: function(data, textStatus, jqXHR) {
      if (jqXHR.status == 200){
        // youtube id is returned by route as 'data' variable
        showAlert("success", "Video upload complete! Click the button below to view the video on YouTube.", true); // only if status code == 200
        $('#upload_spinner').replaceWith(`<a href="https://www.youtube.com/watch?v=${data}" class="shadow btn btn-danger mb-3 py-2 mt-1 btn-main mx-auto">View on YouTube</a>`);
        // clearInterval(upload_poll_interval);
        
        status_color = status_styles['Uploaded'];
        badge = `<span id="status_badge" class="badge py-2 px-3 rounded-pill bg-${status_color} fw-light" style="float:right;">Uploaded</span>`;
        $(`#status_badge`).replaceWith(badge);
      }
      else if (jqXHR.status == 202){
        console.log("Poll successful, video still uploading...");
        status_color = status_styles['Uploading'];
        badge = `<span id="status_badge" class="badge py-2 px-3 rounded-pill bg-${status_color} fw-light" style="float:right;">Uploading</span>`;
        $(`#status_badge`).replaceWith(badge);

        setTimeout(poll_db, 2500, v_id); // call again but w smaller interval
      }
    },
    error: function(data, textStatus) {
      showAlert("danger", "An error occured:<strong> " + data.responseText + "</strong>. Please try again later.", false);
      status_color = status_styles['Upload Failed'];
      badge = `<span id="status_badge" class="badge py-2 px-3 rounded-pill bg-${status_color} fw-light" style="float:right;">Failed to upload</span>`;
      $(`#status_badge`).replaceWith(badge);
      // clearInterval(upload_poll_interval);
      upload_btn = '<input class="shadow btn btn-outline-primary  btn-main  mx-auto mt-4" id="btn_submit_upload" name="submit" type="submit" value="Upload to YouTube">';
      $('#upload_spinner').replaceWith(upload_btn) ;
    }
  });
}