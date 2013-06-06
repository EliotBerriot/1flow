/*
    1flow base utils.
    Copyright Olivier Cortès <oc@1flow.io>
*/

var csrf_token = $("input[name=csrfmiddlewaretoken]").val();
$.ajaxPrefilter(function(options, originalOptions, xhr) {
    xhr.setRequestHeader('X-CSRFToken', csrf_token);
});
