class ImageLayer {
  id;
  src;
  pos;
  original_size;
  selected;
  img;
  scale;
  filename;

  constructor(id, src, pos, scale, selected, filename){
    this.id = id;
    this.src = src;
    this.pos = pos;
    this.selected = selected;
    this.filename = filename;
    this.size = [0,0];
    this.scale = scale;
    this.original_size = this.size;
    this.centre; //describes the centre of the image in pixels
    this.image_central_anchor; //describes the canvas coordinates of the center of the image
  }

  static select(all_layers, selected){
    //for layers set selected to false for all but one
    all_layers.forEach((layer) => {
      if (layer == selected){
        layer.selected = true;
      }
      else{
        layer.selected = false;
      }
    });
  }

  static deselect_all(all_layers){
    all_layers.forEach((layer) => {
        layer.selected = false;
    });
  }

  get selected(){
    return this._selected;
  }

  set selected(sel){
    this._selected = sel;
  }

  get pos(){
    return this.pos;
  }

  set setPos(p){
    this.pos = p;
  }

  get size(){
    return this._size;
  }

  set size(size){
    this._size = size;
    this.calcCentre();
  }

  get original_size(){
    return this.original_size;
  }

  set original_size(os){
    this.original_size = os;
  }

  get img(){
    return this.img;
  }

  get centre(){
    return this._centre;
  }

  set centre(c){
    this._centre = c;
  }

  get scale(){
    return this._scale
  }

  set scale(s){
    this._scale = s;
  }

  get image_central_anchor(){
    return this._image_central_anchor;
  }

  set image_central_anchor(ica){
    this._image_central_anchor = ica;
  }

  calcCentre(){
    var x = this.size[0]/2;
    var y = this.size[1]/2;
    // var x = Math.floor(this.size[0]/2);
    // var y = Math.floor(this.size[1]/2);
    this.centre = [x,y];
  }

  toImg(){
    var img = new Image();
    img.src = this.src;
    this.img = img

    return img;
  }
}

////////////////////////////////////////////////////////////////
// LAYER EDITING:
////////////////////////////////////////////////////////////////
var LayerCount = 1; //including background
var Layers = [];
var selected_layer;

$(document).ready(function () {
  $("#source_select").change(function() {
    // This function will be called whenever the selected option of the #mySelect dropdown changes
    var selectedValue = $(this).val();  // Gets the value of the selected option
    switch_layer_source();
  });
});

function create_layer(src = null, pos = null, scale = 1, selected = true, filename = null){
  $('#ico_modal_loading').css("opacity", "1")
  
  // HTML Formatting etc.
  var layers_parent = document.getElementById('layer-parent');
  var add_layer_btn = document.getElementById('add-layer-btn');
  var layer = document.createElement('div');
  var layer_btn = document.createElement('button');
  layer_btn.classList.add("col", "btn", "btn-primary", "mx-auto", "px-4", "py-1", "w-75", "btn-img-layer");
  layer_btn.appendChild(document.createTextNode("Layer " + LayerCount));
  layer_btn.setAttribute("onclick", `select_layer(${LayerCount})`);
  layer_btn.setAttribute("disabled", true);
  layer_btn.id = `layer_btn_${LayerCount}`
  layer.classList.add("row", "mt-2");
  layer.id = `layer_row_${LayerCount}`;
  trash = document.createElement('i');
  trash.id =  `layer_trash_${LayerCount}`;
  trash.setAttribute("onclick", `delete_layer(${LayerCount})`);
  trash.classList.add('bi', 'bi-trash', 'mx-2');
  trash.setAttribute("style", 'float:right;cursor:pointer;font-size: 18px;');
  trash_container = document.createElement("div");
  trash_container.classList.add("col-md-auto", "p-0", "align-self-center");
  trash_container.appendChild(trash);
  layer.appendChild(layer_btn);
  layer.appendChild(trash_container);
  layers_parent.insertBefore(layer, add_layer_btn);

  // Create ImageLayer instance
  var imageLayer = new ImageLayer(LayerCount, src, pos, scale, selected, filename);

  // Important program flow
  init_img_layer(imageLayer);
  LayerCount += 1;
}

// function delete_layer(layer_id){
//   //Remove layer from array
//   Layers.splice(layer_id - 1, 1);
//   //Remove layer button in UI stack
//   $(`#layer_row_${layer_id}`).remove();
//   //Update Layer Count
//   LayerCount -= 1;
//   //id of last to select it (initalised as previous one)
//   var last_id = layer_id - 1;
//   //Update IDs of layers after
//   next_layers = Layers.slice(layer_id - 1);
//   next_layers.forEach(layer => {
//     var new_id = layer.id - 1;
//     //change row id
//     $(`#layer_row_${layer.id}`).attr('id', `layer_row_${new_id}`);
//     //change layer button id, text & onclick
//     $(`#layer_btn_${layer.id}`).text(`Layer ${new_id}`);
//     $(`#layer_btn_${layer.id}`).attr('onclick', `select_layer(${new_id})`);
//     $(`#layer_btn_${layer.id}`).attr('id', `layer_btn_${new_id}`);
//     //change delete button value
//     $(`#layer_trash_${layer.id}`).attr("onclick", `delete_layer(${new_id})`);
//     $(`#layer_trash_${layer.id}`).attr("id", `layer_trash_${new_id}`);

//     layer.id = new_id;
//     last_id = new_id; //kinda hacky
//   });


//   select_layer(last_id)
//   draw_layer_preview();
// }

function delete_layer(layer_id){
  // Find the index of the layer to delete
  var indexToDelete = Layers.findIndex(layer => layer.id === layer_id);
  
  if(indexToDelete === -1) return; // layer not found

  // Remove layer from array
  Layers.splice(indexToDelete, 1);
  
  // Remove layer button in UI stack
  $(`#layer_row_${layer_id}`).remove();
  
  // Update Layer Count
  LayerCount -= 1;

  // Update IDs of layers after the deleted one
  for(let i = indexToDelete; i < Layers.length; i++) {
      let layer = Layers[i];
      let new_id = layer.id - 1;
      
      // Update the DOM
      $(`#layer_row_${layer.id}`).attr('id', `layer_row_${new_id}`);
      $(`#layer_btn_${layer.id}`).text(`Layer ${new_id}`).attr({
          'onclick': `select_layer(${new_id})`,
          'id': `layer_btn_${new_id}`
      });
      $(`#layer_trash_${layer.id}`).attr({
          "onclick": `delete_layer(${new_id})`,
          "id": `layer_trash_${new_id}`
      });
      
      // Update the layer's ID in the Layers array
      layer.id = new_id;
  }

  // Select the previous layer or the next one if it was the first
  let newSelectedLayerId = (indexToDelete > 0) ? Layers[indexToDelete - 1].id : (Layers.length ? Layers[0].id : null);
  if(newSelectedLayerId !== null) select_layer(newSelectedLayerId);
  draw_layer_preview();
}

function select_layer(layer_id){
  selected_layer = Layers[layer_id - 1]; 
  ImageLayer.select(Layers, selected_layer);
  var layer_btn;

  // Hide layers if selecting background
  showhide_layers(layer_id != 0);
  // Prevent toggle of hiding layers when manipulating layers
  $('#switch_showlayers').prop('disabled', layer_id != 0);

  if (layer_id != 0){ //non-background layer
    layer_btn = document.getElementById(`layer_btn_${layer_id}`);
    document.getElementById("layer_properties").classList.remove("visually-hidden");
    document.getElementById("background_properties").classList.add("visually-hidden");

    //set control values
    layer = Layers[layer_id - 1]
    $('#slide_xpos').val(layer.pos[0] + (layer.size[0]/2));
    $('#slide_ypos').val(layer.pos[1] + (layer.size[1]/2));
    $('#slide_scale').val(layer.scale);
    $('#source_select').val(layer.filename).trigger('change.source_select');//need to store
  }
  else{ //background
    // Background layer button
    layer_btn = document.getElementById('bg_layer_btn');

    //trigger filter change
    document.getElementById("layer_properties").classList.add("visually-hidden");
    document.getElementById("background_properties").classList.remove("visually-hidden");

    //remove selection box on layer when selecting background
    if (selected_layer != null){
      selected_layer.selected = false;
    }
  }
  draw_layer_preview();

  var layers_parent = document.getElementById('layer-parent');
  var add_layer_btn = document.getElementById('add-layer-btn');
  var children = layers_parent.children;

  //edit clicked layer
  layer_btn.classList.remove("btn-outline-primary");
  layer_btn.classList.add("btn-primary");

  document.getElementById("prop-layer-name").innerHTML = layer_btn.innerHTML;

  //visually deselect rest
  for(var i=0; i < children.length - 1; i++){
    var l = children[i];
    if (l.children[0] != layer_btn && l.children[0] != add_layer_btn && l.id != "layer-heading"){
      l.children[0].classList.add("btn-outline-primary");
      l.children[0].classList.remove("btn-primary");
    }
  };
}

function init_img_layer(layer){
  if (layer.src == null){
    layer.filename = $('#source_select').val(); // Not preset, user has clicked add
  }
  
  layer.src = `/users/${user_id}/layers/${layer.filename}`
  var img = layer.toImg();
  
  // Keep in mind this is not executed now, it is executed when the image loads
  img.addEventListener('load', function() {
    im_size = [img.width, img.height];
    layer.size = im_size;
    layer.original_size = im_size;
    if (layer.pos == null){
      layer.pos = [(canvas_dim[0]/2) - layer.centre[0], (canvas_dim[1]/2) - layer.centre[1]]; //load in centre
    }
    layer.image_central_anchor = [(canvas_dim[0]/2), (canvas_dim[1]/2)]

    ctxLayers.drawImage(img, layer.pos[0], layer.pos[1]);
    ctxLayers.strokeRect(layer.pos[0], layer.pos[1], im_size[0], im_size[1])

    // Scaling changes layer pos as positions based off top-left, so need to preserve location for presets
    pre_scale_pos = layer.pos;
    scale_layer(layer.id, layer.scale);
    layer.pos = pre_scale_pos;
    $('#slide_xpos').val(layer.pos[0] + (layer.size[0]/2));
    $('#slide_ypos').val(layer.pos[1] + (layer.size[1]/2));
    
    draw_layer_preview();
    select_layer(layer.id);
    $('#ico_modal_loading').css("opacity", "0");
    $(`#layer_btn_${layer.id}`).prop("disabled", false);
  }, false);

  img.onerror = function(e) {
    // Code to execute when an error occurs
    console.log(e) // incase not a missing asset error
    if (layer == null){
      showAlert('danger', `Couldn't draw layer: <strong>You have no layer assets.</strong>`, false); // loading presets
    }
    else { 
      showAlert('danger', `Couldn't draw layer: <strong>Missing asset ${layer.filename}</strong>`, false); // loading presets
    }
    delete_layer(layer.id);
  };

  Layers.push(layer);
}

function switch_layer_source(){
  $('#ico_modal_loading').css("opacity", "1")
  //get selected layer
  var filename = $('#source_select').val();
  var old_centre = selected_layer.image_central_anchor;
  //change src of layer to value of dropdown
  selected_layer.src = `/users/${user_id}/layers/${filename}`
  selected_layer.filename = filename;
  img = selected_layer.toImg() //set img object

  img.addEventListener('load', function() {
    im_size = [img.width, img.height];
    selected_layer.size = im_size;
    selected_layer.original_size = im_size;
    selected_layer.pos = [old_centre[0] - selected_layer.centre[0], old_centre[1] - selected_layer.centre[1]];
    scale_val = $('#slide_scale').val();
    scale_layer(selected_layer.id, scale_val);
    draw_layer_preview()
    $('#ico_modal_loading').css("opacity", "0")
    $(`#layer_btn_${layer.id}`).prop("disabled", false);
  }, false);
}

// Slider steps
var shift_fired = false;
$(document).on('keydown', function(e){
  if (e.shiftKey && !shift_fired) {
    ranges = document.getElementsByClassName('pos-range')
    shift_fired = true;
    ([...ranges]).forEach(removeStep);
    $('#slide_scale').attr('step', 0.01)
  }
});

$(document).on('keyup', function(e){
  if (shift_fired) {
    ranges = document.getElementsByClassName('pos-range')
    shift_fired = false;
    ([...ranges]).forEach(addStep);
    $('#slide_scale').attr('step', 0.1)
  }
});

function addStep(range){
  range.step = 40
}

function removeStep(range){
  range.step = 1
}

function slide_to_pos(slider_value, layer, axis){
  if (axis == 'x'){
    return [slider_value - layer.centre[0], layer.pos[1]];
  } 
  else if (axis == 'y') {
    return [layer.pos[0], slider_value - layer.centre[1]];
  } 
  else {
    console.log("Invalid axis supplied");
    return [0, 0]
  }
}

function pos_to_slide(pos_value, layer, axis){
  if (axis == 'x'){
    return parseInt(pos_value) + parseInt(layer.centre[0]);
  } 
  else if (axis == 'y') {
    return parseInt(pos_value) + parseInt(layer.centre[1]);
  } 
  else {
    console.log("Invalid axis supplied");
    return 0
  }
}

function move_layer_x(value){
  // selected_layer.pos = [value - selected_layer.centre[0], selected_layer.pos[1]];
  selected_layer.pos = slide_to_pos(value, selected_layer, 'x') //should be in class definition?
  selected_layer.image_central_anchor = [selected_layer.pos[0] + selected_layer.centre[0], selected_layer.image_central_anchor[1]]
  draw_layer_preview();
}
function move_layer_y(value){
  // selected_layer.pos = [selected_layer.pos[0], value - selected_layer.centre[1]];
  selected_layer.pos = slide_to_pos(value, selected_layer, 'y') //should be in class definition?
  selected_layer.image_central_anchor = [selected_layer.image_central_anchor[0], selected_layer.pos[1] + selected_layer.centre[1]]
  draw_layer_preview();
}

function scale_layer(layer_id, slider_value){
  layer_id -= 1;
  var value = Math.pow(slider_value, 2);
  var new_w = Layers[layer_id].original_size[0] * value;
  var new_h = Layers[layer_id].original_size[1] * value;
  var new_x = Layers[layer_id].pos[0] + Layers[layer_id].centre[0] - (new_w / 2);
  var new_y = Layers[layer_id].pos[1] + Layers[layer_id].centre[1] - (new_h / 2);
  Layers[layer_id].size = [new_w, new_h];
  Layers[layer_id].pos = [new_x, new_y];
  Layers[layer_id].scale = slider_value;
  draw_layer_preview();
}

function reset_pos(){
  move_layer_x(canvas_dim[0]/2);
  move_layer_y(canvas_dim[1]/2);
  scale_layer(selected_layer.id, 1);

  $('#slide_xpos').val(canvas_dim[0] / 2);
  $('#slide_ypos').val(canvas_dim[1] / 2);
  $('#slide_scale').val(1);
}

function showhide_title(val){
  if (val){
    //show
    $('#modal_title_preview').removeClass("visually-hidden");
  }
  else{
    //hide
    $('#modal_title_preview').addClass("visually-hidden");
  }
}

function showhide_layers(val){
  if (val){
    //show
    $('#layers_canvas').removeClass("visually-hidden");
  }
  else{
    //hide
    $('#layers_canvas').addClass("visually-hidden");
  }
  $('#switch_showlayers').prop('checked', val)
}