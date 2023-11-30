var canvasBg = document.getElementById('background_canvas');
var ctxBg = canvasBg.getContext('2d');
var canvasLayers = document.getElementById('layers_canvas');
var ctxLayers = canvasLayers.getContext('2d');
var Layers = [];
var FilterValues = {}

$(document).ready(function() {
    // Some canvas initialisation
    GLOBAL_IMAGE = document.getElementById('img_preview').src;
    canvas_dim = [canvasBg.getAttribute("width"), canvasBg.getAttribute("height")];
    initFilterValues();

    // Event handlers:
    $('#save_image').on("click", save_image);
})

function drawImage(context, image, x, y, width, height) {
    context.clearRect(0, 0, context.canvas.width, context.canvas.height); // Clear the canvas
    context.drawImage(image, x, y, width, height);
}

function drawLayers() {
    ctxLayers.clearRect(0, 0, canvasLayers.width, canvasLayers.height);
    layers.forEach(function(layer) {
        drawImage(ctxLayers, layer.image, layer.x, layer.y, layer.width, layer.height);
    });
}

function save_image() {
    // Remove selection border around layers & draw preview
    if (Layers.length > 0){
        // background.src = background_canvas.toDataURL();
        ImageLayer.deselect_all(Layers); // Don't save selection border
        // draw_preview();
        draw_layer_preview();
    }

    // Form data
    var formData = new FormData();
    if (!USING_VIDEO){ // If using a video just do layers.
        var bg = background_canvas.toDataURL();
        formData.append('background_dataurl', bg);
    }
    var layers = layers_canvas.toDataURL();
    formData.append('layers_dataurl', layers);

    // AJAX request
    var url = '/visualizers/' + p_v_id + '/preview/edits';  // updated as per the updated Flask route
    $.ajax({
        url: url,
        type: 'PUT',  // updated to PUT as per the updated Flask route
        data: formData,
        processData: false,
        contentType: false,
        success: function(response) {
            console.log("Image changed");
            $('#imagemodal').modal('hide');
            saveFilterValues(); // Save filter vals   
            image_layer_state = get_current_layers(); // Save layer state

            if (!USING_VIDEO) {
                $('#img_preview').attr("src", add_dummy(response.bg_url));
            }
            $('#layers_preview').attr("src", add_dummy(response.layers_url));
            // Done. Inform the user
        },
        error: function(xhr, status, error) {
            console.log("Server didn't like the updated image.");
            console.log(xhr.responseText);
            // Error. Inform the user
        }
    });
}

// Drawing functions:
// - initialisation
ctxLayers.setLineDash([25]);
ctxLayers.strokeStyle = "#378DFC"
ctxLayers.lineWidth = 4;
showhide_layers(false);
// document.getElementById('layers_status').classList.add("visually-hidden");

function draw_layer_preview(){
    // Clear the canvas
    ctxLayers.clearRect(0, 0, canvas_dim[0], canvas_dim[1]);
  
    // Iterate layers
    Layers.forEach((layer) => {
        try {
            ctxLayers.drawImage(layer.img, layer.pos[0], layer.pos[1], layer.size[0], layer.size[1]);
        } catch (err) {
            if(err instanceof DOMException) {
                console.log("Failed to draw the image onto the canvas: ", err);
            }
        }

    if (layer.selected && (layer.id != 0)){
        ctxLayers.strokeRect(layer.pos[0], layer.pos[1], layer.size[0], layer.size[1])
      }
    });
  }

// Prevent filter values from changing if not clicked "save"
var filterValues = {};

function initFilterValues() {
  // Iterate over each input within the FilterControls fieldset
  $("#FilterControls input").each(function() {
      // Save the value of this input in the filterValues object, using the input's id as the key
      filterValues[$(this).attr('id')] = 0;
  });
  // Print the values to the console (for debugging)
  // console.log(filterValues);
}

function saveFilterValues() {
  // Iterate over each input within the FilterControls fieldset
  $("#FilterControls input").each(function() {
      // Save the value of this input in the filterValues object, using the input's id as the key
      filterValues[$(this).attr('id')] = $(this).val();
  });
  // Print the values to the console (for debugging)
  // console.log(filterValues);
}

function loadFilterValues(vals) {
  if (!vals){
    console.log("No filter values in this preset.")
    return;
  }
  // Iterate over each input within the FilterControls fieldset
  $("#FilterControls input").each(function() {
      // Get the id of this input
      var id = $(this).attr('id');
      // If a value was saved for this input
      if (vals.hasOwnProperty(id)) {
          // Set the value of this input
          $(this).val(vals[id]);
          // Find the sibling with class FilterValue and update its text
          $(this).siblings('.FilterValue').text(vals[id]);
      }
  });
}


  