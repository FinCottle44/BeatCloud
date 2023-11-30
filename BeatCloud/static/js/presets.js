var image_layer_state = {};

$(document).ready(function() {
    // Fetch all presets on load
    fetch_all_presets();

    // Open preset name modal
    $('#drop-save-preset').on("click", function(){
        $('#savePresetModal').modal('show')
        $('#presetName').val('');
    });

    // Open update preset modal
    $('#drop-update-preset').on("click", function(){
        $('#presetNewName').val($('#presetList').children("option:selected").text());
        $('#updatePresetModal').modal('show')
    });

    // Open delete preset modal
    $('#drop-delete-preset').on("click", function(){
        $('#deletePresetModal').modal('show')
    });

    // Save presets
    $('#savePresetButton').on('click', function() {
        var presetName = $('#presetName').val();
        save_preset(presetName);
        $('#savePresetModal').modal('hide')
        $('#presetName').val('');
    });
    
    // Update preset button
    $('#updatePresetButton').on('click', function() {
        var presetId = $('#presetList').val();
        var preset_name = $('#presetNewName').val();
        update_preset(presetId, preset_name);
        $('#updatePresetModal').modal('hide');
        $('#presetNewName').val('');
    });

    // Update input field with selection
    $('#presetList').on('input', function(){
        $('#presetNewName').val($(this).children("option:selected").text());
    });
    
    // Delete presets
    $('#deletePresetButton').on('click', function() {
        var presetId = $('#presetDeleteList').val();
        delete_preset(presetId);
    });
});

function fetch_all_presets(){
    //Clear lists:
    $('#presetList').empty();
    $('#create-preset-parent').empty();
    $('#presetDeleteList').empty();

    $.ajax({
        url:`/users/${session_user_id}/presets`,
        type: 'GET',
        dataType: 'json', // Expect a JSON response
        success: function(presets) {
            // Populate dropdown
            $.each(presets, function(index, preset){
                let id = preset.SK.split('#')[1]
                let name = preset.preset_name
                var presetElement = $('<a>', {
                    class: "dropdown-item create-preset",
                    href: "#",
                    'data-value':id,
                    text: name
                });
                
                // set onclick to use id
                presetElement.click(function(){
                    load_preset(id, name);
                })

                // Add to children of load list
                $('#create-preset-parent').append(presetElement);
                
                // add to children of update list
                $('#presetList').append($('<option>', {
                    value: id,
                    text: name
                }));

                // Add to children of delete list
                $('#presetDeleteList').append($('<option>', {
                    value: id,
                    text: name
                }));
            })
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // Handle any errors here
            console.log(textStatus, errorThrown);
        }
    });
    
}

function load_preset(preset_id, preset_name){
    // Save pre-load image modal state incase don't want to load preset layers etc.
    image_layer_state = get_current_layers();
    
    $.ajax({
        url:`/users/${session_user_id}/presets/${preset_id}`,
        type: 'GET',
        dataType: 'json',
        success: function(preset) {
            set_values(preset.preset_data);
            showAlert('info', `Loaded preset '<strong>${preset.preset_name}</strong>'.`, true)
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // Handle any errors here
            console.log(textStatus, errorThrown);
            showAlert('danger', `Error loading preset <strong>${preset_name}</strong>`, false);
        }
    })
}

function set_values(data){
    // Set control values from preset data
    $('#chkShowTitle').prop('checked', JSON.parse(data.disp_title));
    $('#chkShowTitle').trigger('change'); // lock controls if false
    $('#chkBlur').prop('checked', JSON.parse(data.im_blur));
    $('#chkBlur').trigger('change'); // lock controls if false
    $('#range_blurlevel').val(data.im_blur_level);
    $('#sl_title_font').val(data.title_font);
    $('#title_font_colour').val(data.title_colour);
    $('#title_font_colour_picker').val(data.title_colour);
    $('#title_font_size').val(data.title_size);
    $("#range_fontsize").val(data.title_size);
    $('#title_ypos').val(data.title_y_offset);
    $("#range_title_ypos").val(data.title_y_offset);
    $('#fx_dropdown').val(data.fx);
    $(`.nav-link[data-value='${data.fx}']`).tab('show');
    $('#fx_opacity').val(data.fx_opacity);
    $('#fx_opacity').trigger('change');
    $('#quality_select').val(data.resolution);
    $(`input[name=quality_radio][value='${data.resolution}']`).prop('checked', true).change();
    $('#fps_select').val(data.fps);
    $(`input[name=fps_radio][value='${data.fps}']`).prop('checked', true).change();
 
    if (!USING_VIDEO){
        // Set caman filter values:
        loadFilterValues(data.filters); // in editImg.js
    }   

    import_layers(data.layers)

    // Fire preview:
    preview_title();
}

function import_layers(layers){
    // Remove all current layers:
    // Layers.forEach(function(layer){
    Layers.slice().reverse().forEach(function(layer){
        delete_layer(layer.id);
    })

    if (Object.keys(layers).length < 1) {
        return;
    }

    // Add new ones:
    $.each(layers, function(layerIndex, layerDetails) {
        // For each layer, create_layer (editImg.js) instantiates an ImageLayer object and creates all necessary HTML
        pos = [parseInt(layerDetails.location_x), parseInt(layerDetails.location_y)];
        create_layer(layerDetails.source, pos, layerDetails.scale, false, layerDetails.source.split('/').pop())
    });

    // Allows for calling of functions that are within camanfiltering
    $(document).trigger('BCPresetLoaded');
}

function get_current_layers(){
    let layers = {};
    Layers.forEach((layer, index) => {
        layers[index + 1] = {
            location_x: layer.pos[0],
            location_y: layer.pos[1],
            scale: layer.scale,
            source: layer.filename,
            type: "image" // for now
        }
    });
    return layers;
}

function get_current_values(){
    // Load JSON object
    preset_layers = get_current_layers();

    let preset_data = {
        // Form values
        disp_title: $('#chkShowTitle').prop('checked'),
        fps: $('#fps_select').val(),
        fx: $('#fx_dropdown').val(),
        fx_opacity: $('#fx_opacity').val(),
        im_blur: $('#chkBlur').prop('checked'),
        im_blur_level: $('#range_blurlevel').val(),
        resolution: $('#quality_select').val(),
        title_colour: $('#title_font_colour').val(),
        title_font: $('#sl_title_font').val(),
        title_size: $('#title_font_size').val(),
        title_y_offset: $('#title_ypos').val(),
        // Background filters (set in editImg.js when saving image):
        filters: filterValues,
        // Layers:
        layers: preset_layers
    }
    return preset_data
}

function save_preset(preset_name){
    // get control values
    preset_data = get_current_values();

    // Create entire string for sending
    let request_data = {preset_name:preset_name, preset_data:preset_data};
    let request_string = JSON.stringify(request_data)
    
    // Send request
    $.ajax({
        url:`/users/${session_user_id}/presets`,
        type: 'POST',
        dataType: 'json',
        data: request_string,
        contentType: 'application/json; charset=utf-8',
        success: function(response) {
            showAlert('success', `Successfully saved preset <em>'${preset_name}'</em>.`, true)
            fetch_all_presets(); //update preset list
        },
        error: function(data, textStatus) {
            // Handle any errors here
            console.log(textStatus);
            showAlert('danger', `An error occured saving preset '<em>${preset_name}</em>': <strong>${data.responseText}</strong>`, false)
        }
    });
}

function update_preset(preset_id, preset_name){
    // get control values
    preset_data = get_current_values();

    // Create entire string for sending
    let request_data = {preset_name:preset_name, preset_data:preset_data};
    let request_string = JSON.stringify(request_data)

    $.ajax({
        url:`/users/${session_user_id}/presets/${preset_id}`,
        type: 'PUT',
        dataType: 'json',
        data: request_string,
        contentType: 'application/json; charset=utf-8',
        success: function(response) {
            showAlert("success", `Preset <em>'${preset_name}'</em> successfully overwritten`, true)
            fetch_all_presets();
        },
        error: function(data, textStatus) {
            // Handle any errors here
            console.log(textStatus);
            showAlert("danger", `Error overwriting preset <em>'${preset_name}'</em>: <strong>${data.responseText}</strong>`);
        }
    });
}

function delete_preset(preset_id){
    $.ajax({
        url:`/users/${session_user_id}/presets/${preset_id}`,
        type: 'DELETE',
        success: function(deleted_id) {   
            console.log("Deleted preset: " + deleted_id);
            //remove from all lists
            $(`#create-preset-parent a[data-value='${deleted_id}']`).remove();
            $(`#presetList option[value='${deleted_id}']`).remove();
            $(`#presetDeleteList option[value='${deleted_id}']`).remove();
            $('#deletePresetModal').modal('hide');
            showAlert("success", `Successfully deleted preset.`, true);
        },
        error: function(data, textStatus) {
            // Handle any errors here
            console.log(textStatus, errorThrown);
            showAlert("danger", `Error deleting preset <em>'${preset_name}'</em>: <strong>${data.responseText}</strong>`);
        }
    });
}