var last_info_btn = "";

function update_other_items(data) {
    for(let i in data) {
        let field = data[i]
                
        let id = field["id"];
        let new_val = field["value"];
        let onclick_val = field["onclick"];
        let action_val = field["action"];
        
        // Make sure webapage has the specified id item
        if (id != undefined) {
            element = document.getElementById(id);
            }
        else {
            element = undefined;
            }
        
        if (element != undefined) {
                            
            if (new_val != undefined) {
                element.innerHTML = new_val;
                element.value = new_val;
                element.setAttribute("orig_val", new_val);
                }

            if (onclick_val != undefined) {
                // console.log("Updating onclick to", onclick_val);
                element.setAttribute("onclick", onclick_val);
                }

            if (action_val != undefined) {
                // console.log("Updating action to", action_val);
                element.setAttribute("action", action_val);
                }
            }
        }
    }

function update_info_box(data, btn_id) {
    let new_text = data["msg"];
    let block = document.getElementById("info_block");
    let txt = document.getElementById("info_out");
    let l_button = document.getElementById("l_button");
    let r_button = document.getElementById("r_button");
    let textbox_div = document.getElementById("info_textbox");

    if (new_text != "") {

        txt.innerHTML = new_text;

        // Roughly center the item if "center" mode is enabled
        if (data["center"] == true) {
            block.style.left = "40%";
            block.style.top  = "25%";            

            block.style.display = "block";

            last_info_btn = btn_id;
            }
        else if (btn_id != undefined) {
            // If a button is given, place the box near the box
            let btn = document.getElementById(btn_id);
            let btn_rect = btn.getBoundingClientRect();
            
            block.style.left = (btn_rect.left + 45) + "px";
            block.style.top = (btn_rect.top - 10) + "px";

            block.style.display = "block";

            last_info_btn = btn_id;
            }

        l_button.innerHTML = data["l_button_text"];
        r_button.innerHTML = data["r_button_text"];
        
        //  Are the buttons supposed to be visible?
        if (data["l_button_enabled"]) {
            l_button.style.display = "block";
            }
        else {
            l_button.style.display = "none";
            }
            
        if (data["r_button_enabled"]) {
            r_button.style.display = "block";
            }
        else {
            r_button.style.display = "none";
            }
        
        // Set the action for the two buttons
        //  (blank url == just close the window)
        if (data["l_button_action"] == "") {
            l_button.setAttribute("onclick", "javascript: hideInfoBlock();");
            }
        else {
            l_button.setAttribute("onclick",
                                  "javascript: " + data["l_button_action"]);
            }

        if (data["textbox"] != undefined) {
             let textbox1 = document.getElementById("textbox1");

             if (textbox1 != undefined) {
                   console.log("Updating textbox to", data["textbox"]);
                   textbox1.value = data["textbox"];
                   }

             textbox_div.style.display = "block";
            }
        else {
            textbox_div.style.display = "none";
            }

        if (data["r_button_action"] == "") {
            r_button.setAttribute("onclick", "javascript: hideInfoBlock();");
            }
        else {
            r_button.setAttribute("onclick",
                                  "javascript: " + data["r_button_action"]);

            }
        }

    else {
        block.style.display = "none";
        }
    }

function handle_json_response(req, btn_id) {
    //console.log("Rcvd:", req.responseText);

    let data = JSON.parse(req.responseText);
    let hidden_form = document.getElementById("hidden_form");
  
    if ("update" in data) {
        update_other_items(data["update"]);
        }
    
    update_info_box(data, btn_id);

    if ((data["submit_form"] == true) && (hidden_form != undefined)) {
        hidden_form.submit();
        }

    // Allow the server to request the page be reloaded
    if (data["refresh"] == true) {
        location.reload();
        }

    // Allow the server to request the browser go to a different page
    if (data["redirect"] != undefined) {
        window.location.href = data["redirect"];
        }
    }

// hide_second => the second click on the same button closes the window
function showInfoViaPOST(url, btn_id,
                         in_textbox = null,
                         hide_second = false) {

    let block = document.getElementById("info_block");
    let btn = document.getElementById(btn_id);
    let data = null;
    let in_box = null;

    if ((hide_second == true) &&
        (btn_id == last_info_btn) &&
        (block.style.display != "none")) {
            block.style.display = "none";
            }
    else {
        
        if (in_textbox != null) {
            in_box = document.getElementById(in_textbox);

            let value = in_box.value;
            data = JSON.stringify({ "value" : value });
            }

        let req = new XMLHttpRequest();

        req.open("POST", url, false); // synchronous
        req.setRequestHeader("Content-Type", "application/json");
        req.send(data);

        handle_json_response(req, btn_id);
        }
    }
   

function submitFormViaPOST(action_url, textbox_field) {
    let hidden_form = document.getElementById("hidden_form");
    let hidden_textbox = document.getElementById("hidden_form_textbox");

    textbox_field = document.getElementById(textbox_field);
    
    if ((hidden_form != undefined) &&
        (hidden_textbox != undefined) &&
        (textbox_field != undefined)) {

        hidden_textbox.value = textbox_field.value;
        hidden_form.setAttribute("method", "POST");
        hidden_form.setAttribute("action", action_url);

        hidden_form.submit();
        }
    else {
        console.log("Could not submit");
        }
    }

function submitFormViaGET(action_url, textbox_field ) {
    let hidden_form = document.getElementById("hidden_form");

    textbox_field = document.getElementById(textbox_field);

    if ((hidden_form != undefined) &&
        (textbox_field != undefined)) {

        action_url = action_url + "/" + encodeURIComponent(textbox_field.value);
        
        hidden_form.setAttribute("method", "GET");
        hidden_form.setAttribute("action", action_url);

        hidden_form.submit();
        }
    else {
        console.log("Could not submit");
        }
    }


function submitViaNoForm(action_url, textbox_field ) {
    textbox_field = document.getElementById(textbox_field);

    if (action_url != undefined) {
        
        if (textbox_field != undefined) {
            action_url = action_url + "/" +
                    encodeURIComponent(textbox_field.value);
            }
        
        window.location.href = action_url;
        }
    else {
        console.log("Could not submit");
        }
    }

function uploadViaPOST(url, input_box_name, extra_box_name = null) {

    let data = document.getElementById(input_box_name);
    let extra = null;
    
    if (extra_box_name != null) {
        extra = document.getElementById(extra_box_name);
        }


    console.log("upload request", data, extra);
    
    if ((data != undefined) && (url != undefined)) {
        data = data.files[0];   // get the file from the input tag

        submitForm = new FormData();
        
        // Is there any thing else to put in the form?
        if (extra != undefined) {
            submitForm.append("value", extra.value);
            }
        
        submitForm.append("file", data);
        
        let req = new XMLHttpRequest();

        req.open("POST", url, false); // synchronous
        req.send(submitForm);

        handle_json_response(req, null);
        }
    }

function enableOrDisableUpdateAndCheck(button_name, check_button, textbox_name) {
    let btn = document.getElementById(button_name);
    let chk = document.getElementById(check_button);
    let txt = document.getElementById(textbox_name);
    
    let orig_val = txt.getAttribute("orig_val");
    let cur_val  = txt.value;

    btn.disabled = (cur_val == orig_val);

    // Now configure the check button if it exists
    if (chk != null) {
        chk.disabled = (cur_val == "");
        }
    }

function enableOrDisableSubmit(id_prefix) {
    let submit_btn = document.getElementById(id_prefix + "_submit");
    let software_chk = document.getElementById(id_prefix + "_software");
    let settings_chk = document.getElementById(id_prefix + "_settings");
    let file_btn = document.getElementById(id_prefix + "_file");

    let ok = software_chk.checked || settings_chk.checked;

    if (file_btn != undefined) {
        ok = ok && (file_btn.files[0] != undefined)
        }

    submit_btn.disabled = !ok;
    }

function hideInfoBlock() {
    let block = document.getElementById("info_block");
    block.style.display = "none";
    }

// https://stackoverflow.com/questions/5999118/how-can-i-add-or-update-a-query-string-parameter

function updateQueryStringParameter(uri, key, value) {
  var re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
  var separator = uri.indexOf('?') !== -1 ? "&" : "?";
  if (uri.match(re)) {
    return uri.replace(re, '$1' + key + "=" + value + '$2');
  }
  else {
    return uri + separator + key + "=" + value;
  }
}

function new_sync_file() {
  var new_file = prompt("Enter name of file to sync:");

  if (new_file != null) {
      var new_url = updateQueryStringParameter(document.URL, 'add', new_file);
      location.href = new_url;
      };
   }