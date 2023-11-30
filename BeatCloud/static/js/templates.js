// const { start } = require("@popperjs/core");

var image_layer_state = {};

$(document).ready(function() {
    // Fetch all templates on load
    fetch_all_templates();

    // Open save template modal
    $('#drop-save-template').on("click", function(){
        $('#saveTemplateModal').modal('show')
        $('#templateName').val('');
        $('#title_template').val($('#video_title').val());
        $('#description_template').val($('#video_desc').val());
    });

    // Open update template modal
    $('#drop-update-template').on("click", function(){
        $('#templateNewName').val($('#templateList').children("option:selected").text());
        $('#updateTemplateModal').modal('show')
        $('#update_title_template').val($('#video_title').val());
        $('#update_description_template').val($('#video_desc').val());
    });

    // Open delete template modal
    $('#drop-delete-template').on("click", function(){
        $('#deleteTemplateModal').modal('show')
    });

    // Save templates
    $('#saveTemplateButton').on('click', function() {
        var templateName = $('#templateName').val();
        save_template(templateName);
        $('#saveTemplateModal').modal('hide')
    });
    
    // Update template button
    $('#updateTemplateButton').on('click', function() {
        var templateId = $('#templateList').val();
        var template_name = $('#templateList option:selected').text()
        update_template(templateId, template_name);

        $('#updateTemplateModal').modal('hide');
        $('#templateNewName').val('');
        $('#update_title_template').val('');
        $('#update_description_template').val('');
    });

    // Update input field with selection
    $('#templateList').on('input', function(){
        $('#templateNewName').val($(this).children("option:selected").text());
    });
    
    // Delete templates
    $('#deleteTemplateButton').on('click', function() {
        var templateId = $('#templateDeleteList').val();
        delete_template(templateId);
    });
});

function fetch_all_templates(){
    //Clear lists:
    $('#templateList').empty();
    $('#create-template-parent').empty();
    $('#templateDeleteList').empty();

    $.ajax({
        url:`/users/${session_user_id}/templates`,
        type: 'GET',
        dataType: 'json', // Expect a JSON response
        success: function(templates) {
            // Show message if no templates
            if (templates.length == 0){
                var no_template = '<h6 id="NoTemplateWarning" class="dropdown-header">No templates found. Create one!</h6>'
                $('#create-template-parent').append(no_template);
                $('#drop-delete-template').addClass('disabled');
                $('#drop-delete-template').removeClass('text-danger');
                $('#drop-update-template').addClass('disabled');
            } else {
                $('#drop-delete-template').removeClass('disabled');
                $('#drop-delete-template').addClass('text-danger');
                $('#drop-update-template').removeClass('disabled');
            }

            // Populate dropdown
            $.each(templates, function(index, template){
                let id = template.SK.split('#')[1]
                let name = template.template_name
                var templateElement = $('<a>', {
                    class: "dropdown-item create-template",
                    href: "#",
                    'data-value':id,
                    text: name
                });
                
                // set onclick to use id
                templateElement.click(function(){
                    load_template(id, name);
                })

                // Add to children of load list
                $('#create-template-parent').append(templateElement);
                
                // add to children of update list
                $('#templateList').append($('<option>', {
                    value: id,
                    text: name
                }));

                // Add to children of delete list
                $('#templateDeleteList').append($('<option>', {
                    value: id,
                    text: name
                }));
            })
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // Handle any errors here
            showAlert('error', 'Error fetching user templates')
            console.log(textStatus, errorThrown);
        }
    });
    
}

function determine_placeholders(template_data){
    // Remove all previous instances of placeholder inputs
    $('.placeholder_input_row').remove();

    // find placeholders
    var regex = /\[\[(\w+)\]\]/g;
    let placeholders = new Map();
    var match;
    
    // title
    while ((match = regex.exec(template_data.title)) !== null){
        // match[0] is [[placeholder_name]], match[1] is placeholder_name
        placeholders.set(match[0], "");
    }

    while ((match = regex.exec(template_data.desc)) !== null){
        // match[0] is [[placeholder_name]], match[1] is placeholder_name
        placeholders.set(match[0], "");
    }
    // show modal
    return placeholders;
}

function populate_modal(placeholders, template){
    placeholders.forEach((value, key) => {
        var row = $('<div class="row m-2 placeholder_input_row"></div>')
        var col_left = $('<div class="col-4 my-auto"></div>');
        var p_elem = $("<p class='m-0 float-end'></p>").text(key); 
        col_left.append(p_elem);
        
        var col_right = $('<div class="col-8 my-auto"></div>');
        var inp_elem = $(`<input type="text" data-key="${key}" class="form-control placeholder_value" placeholder="Replacement for '${key}'">`); 
        col_right.append(inp_elem);

        row.append(col_left);
        row.append(col_right);
        $('#placeholder_parent').append(row);
    });
    // load onclick replace_placeholders
    $('#loadTemplateButton').on('click', function() {
        placeholders = get_new_placeholder_values(placeholders);
        replace_placeholders(placeholders, template.template_data);
        showAlert('info', `Loaded template '<strong>${template.template_name}</strong>'.`, true)
    });
    $('#loadTemplateModal').modal('show');
}

function get_new_placeholder_values(placeholders){
    $('.placeholder_value').each(function(i){
        var key = $(this).data('key');
        placeholders.set(key, $(this).val());
    })
    return placeholders;
}

function replace_placeholders(placeholders, template_data){
    title = template_data.title;
    placeholders.forEach((value, key) => {
        let placeholderPattern = new RegExp(key.replace(/\[/g, '\\[').replace(/\]/g, '\\]'), 'g');
        title = title.replace(placeholderPattern, value);
    });

    desc = template_data.desc;
    placeholders.forEach((value, key) => {
        let placeholderPattern = new RegExp(key.replace(/\[/g, '\\[').replace(/\]/g, '\\]'), 'g');
        desc = desc.replace(placeholderPattern, value);
    });
    
    // Recreating structure of template
    let new_data = {
        title: title,
        desc: desc,
        vis: template_data.vis,
        tags: template_data.tags
    }
    set_template_values(new_data);
}

function set_template_values(data){
    //populate title input
    $('#video_title').val(data.title);
    //populate desc inptt
    $('#video_desc').val(data.desc);
    //populate tag input 


    //set visibility input
    $('#visibility').val(data.vis);

    $('#loadTemplateModal').modal('hide');
}

function load_template(template_id, template_name){
    $.ajax({
        url:`/users/${session_user_id}/templates/${template_id}`,
        type: 'GET',
        dataType: 'json',
        success: function(template) {
            // Open modal to substitute placeholders
            placeholders = determine_placeholders(template.template_data);
            if (placeholders.size > 0){
                populate_modal(placeholders, template);
            }
            else {
                // Populate upload form with template values
                set_template_values(template.template_data);
            }

            $('#loaded_template_name').text(template.template_name);
            // showAlert('info', `Loaded template '<strong>${template.template_name}</strong>'.`, true)
        },
        error: function(jqXHR, textStatus, errorThrown) {
            // Handle any errors here
            console.log(textStatus, errorThrown);
            showAlert('danger', `Error loading template <strong>${template_name}</strong>`, false);
        }
    })
}

function get_current_values(){
    let template_data = {
        // Form values
        title: $('#title_template').val(),
        desc: $('#description_template').val(),
        vis: $('#visibility').val(),
        tags: user_tags
    }
    return template_data
}

function save_template(template_name){
    // get control values
    template_data = get_current_values();
    
    // Create entire string for sending
    let request_data = {template_name:template_name, template_data:template_data};
    let request_string = JSON.stringify(request_data)
    
    // Send request
    $.ajax({
        url:`/users/${session_user_id}/templates`,
        type: 'POST',
        dataType: 'json',
        data: request_string,
        contentType: 'application/json; charset=utf-8',
        success: function(response) {
            showAlert('success', `Successfully saved template <em>'${template_name}'</em>.`, true)
            fetch_all_templates(); //update template list
        },
        error: function(data, textStatus) {
            // Handle any errors here
            console.log(textStatus);
            showAlert('danger', `An error occured saving template '<em>${template_name}</em>': <strong>${data.responseText}</strong>`, false)
        }
    });
}

function get_current_values_update(){
    let template_data = {
        // Form values
        title: $('#update_title_template').val(),
        desc: $('#update_description_template').val(),
        vis: $('#visibility').val(),
        tags: user_tags
    }
    return template_data
}

function update_template(template_id, template_name){
    // get control values
    template_data = get_current_values_update();

    // Create entire string for sending
    let request_data = {template_name:template_name, template_data:template_data};
    let request_string = JSON.stringify(request_data)

    $.ajax({
        url:`/users/${session_user_id}/templates/${template_id}`,
        type: 'PUT',
        dataType: 'json',
        data: request_string,
        contentType: 'application/json; charset=utf-8',
        success: function(response) {
            showAlert("success", `Template <em>'${template_name}'</em> successfully overwritten`, true)
            fetch_all_templates();
        },
        error: function(data, textStatus) {
            // Handle any errors here
            console.log(textStatus);
            showAlert("danger", `Error overwriting template <em>'${template_name}'</em>: <strong>${data.responseText}</strong>`);
        }
    });
}

function delete_template(template_id){
    $.ajax({
        url:`/users/${session_user_id}/templates/${template_id}`,
        type: 'DELETE',
        success: function(deleted_id) {   
            console.log("Deleted template: " + deleted_id);
            //remove from all lists
            $(`#create-template-parent a[data-value='${deleted_id}']`).remove();
            $(`#templateList option[value='${deleted_id}']`).remove();
            $(`#templateDeleteList option[value='${deleted_id}']`).remove();
            $('#deleteTemplateModal').modal('hide');
            showAlert("success", `Successfully deleted template.`, true);
        },
        error: function(data, textStatus) {
            // Handle any errors here
            console.log(textStatus, errorThrown);
            showAlert("danger", `Error deleting template <em>'${template_name}'</em>: <strong>${data.responseText}</strong>`);
        }
    });
}

// called in view.html
function add_placeholder(control) {
    var input = $(`#${control}`);
    var inputValue = input.val();

    var endPos = input[0].selectionEnd;
    var startPos = input[0].selectionStart;
    var input_sub = inputValue.substring(startPos, endPos)

    var newValue; 
    if (endPos == startPos){
        newValue = inputValue.substring(0, startPos) + '[[placeholder_name]]' + inputValue.substring(endPos, inputValue.length);
    } else { // User has selected some text already
        newValue = inputValue.substring(0, startPos) + '[[' + inputValue.substring(startPos, endPos) + ']]' + inputValue.substring(endPos, inputValue.length);
    }
    
    input.val(newValue);
    input[0].selectionStart = startPos + 2 + input_sub.length;
    input[0].selectionEnd = startPos + 2 + input_sub.length;
}