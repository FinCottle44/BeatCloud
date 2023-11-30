  let font_dropArea = document.getElementById('font-drop-area')
  let media_dropArea = document.getElementById('media-drop-area')
  let video_dropArea = document.getElementById('video-drop-area')

  ;['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    font_dropArea.addEventListener(eventName, preventDefaults, false)
    media_dropArea.addEventListener(eventName, preventDefaults, false)
  })

  ;['dragenter', 'dragover'].forEach(eventName => {
    font_dropArea.addEventListener(eventName, highlight, false)
    media_dropArea.addEventListener(eventName, highlight, false)
  })

  ;['dragleave', 'drop'].forEach(eventName => {
    font_dropArea.addEventListener(eventName, unhighlight, false)
    media_dropArea.addEventListener(eventName, unhighlight, false)
  })

  font_dropArea.addEventListener('drop', handleFontDrop, false)
  media_dropArea.addEventListener('drop', handleMediaDrop, false)

  //all
  function highlight(e) {
    this.classList.add('bg-secondary', 'text-white');
  }

  function unhighlight(e) {
    this.classList.remove('bg-secondary', 'text-white');
  }

  function preventDefaults (e) {
    e.preventDefault();
    e.stopPropagation();
  }

  //fonts
  function handleFontDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;

    handleFontFiles(files);
  }

  function handleFontFiles(files) {
    ([...files]).forEach(uploadFontFile);
  }

  function uploadFontFile(file) {
    var url = `/users/${session_user_id}/fonts`;
    var xhr = new XMLHttpRequest();
    var formData = new FormData();
    xhr.open('POST', url, true);

    xhr.addEventListener('readystatechange', function(e) {
      if (xhr.readyState == 4 && xhr.status == 200) {
        addToFontList(xhr.responseText);
        document.getElementById('font_input').value = "";
        // Done. Inform the user
        showAlert("success", `Successfully uploaded font ${xhr.responseText}`, true);
        $('#user_asset_count').text(parseInt($('#user_asset_count').text())+1)
      }
      else if (xhr.readyState == 4 && xhr.status == 413) {
        showAlert("danger", "<strong>Error:</strong> Uploaded file too large. Maximum File Upload size is <strong>300MB</strong>", true);
      }
      else if (xhr.readyState == 4 && xhr.status != 200) {
        showAlert("danger", "Error: " + xhr.responseText, true);
        // Error. Inform the user
      }
    })

    formData.append('file', file)
    xhr.send(formData)
  }

  //Media
  function handleMediaDrop(e) {
    let dt = e.dataTransfer;
    let files = dt.files;

    handleMediaFiles(files);
  }

  function handleMediaFiles(files) {
    ([...files]).forEach(uploadMediaFile);
  }

  function uploadMediaFile(file) {
    var url = `/users/${session_user_id}/layers`;
    var xhr = new XMLHttpRequest();
    var formData = new FormData();
    xhr.open('POST', url, true);

    xhr.addEventListener('readystatechange', function(e) {
      if (xhr.readyState == 4 && xhr.status == 200) {
        addToMediaList(xhr.responseText);
        console.log("successfully uploaded");
        document.getElementById('media_input').value = "";
        // Done. Inform the user
        showAlert("success", `Successfully uploaded file ${xhr.responseText}`, true);
        $('#user_asset_count').text(parseInt($('#user_asset_count').text())+1)
      }
      else if (xhr.readyState == 4 && xhr.status == 413) {
        showAlert("danger", "<strong>Error:</strong> Uploaded file too large. Maximum File Upload size is <strong>300MB</strong>", true);
      }
      else if (xhr.readyState == 4 && xhr.status != 200) {
        showAlert("danger", "Error: " + xhr.responseText, true);
        // Error. Inform the user
      }
    })

    formData.append('file', file)
    xhr.send(formData)
  }
