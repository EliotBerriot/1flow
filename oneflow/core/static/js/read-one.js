
//'use strict';

var change_selector_ids   = []; // not used anymore, thus empty.
var read_actions_messages = {};

function mark_something(read_id, mark_what, mark_inverse, send_notify, message) {

    var read = $("#" + read_id);

    //
    // CSS classes are defined in a template-tag.
    //

    if(typeof message == 'undefined') {
        var message = null;
    }

    if(typeof mark_inverse == 'undefined') {
        var mark_inverse = false;
    }

    if (mark_inverse) {
        var klass    = 'not_' + mark_what;
        var inverse  = mark_what;
        var notifmsg = message || read_actions_messages[mark_what]['undone']

    } else {
        var klass   = mark_what;
        var inverse = 'not_' + mark_what;
        var notifmsg = message || read_actions_messages[mark_what]['done']
    }

    if(typeof send_notify == 'undefined') {
        var send_notify = false;
    }

    $.get(read.data('url-action-toggle').replace('@@KEY@@', mark_what),
        function(){
            if (send_notify) {
                notify({
                    text: notifmsg,
                    type: 'success',
                    icon: false,
                    sticker: false,
                    nonblock: true,
                    nonblock_opacity: .2
                });
            }

            //console.debug(read.find(".action-mark-" + klass));
            //console.debug(read.find(".action-mark-" + inverse));

            read.find(".action-mark-" + klass).fadeOut('fast', function(){
                read.find(".action-mark-" + inverse).fadeIn('fast');
            });

            read.removeClass(inverse).addClass(klass);

            _.each(change_selector_ids, function(sel) {
                $(sel + read_id).removeClass(inverse).addClass(klass);
            });
        }
    );

    // avoid any click event to propagate?
    return false;
}

function toggle_status(read_id, attr_name, send_notify) {

    var read = $("#" + read_id);

    mark_something(read_id, attr_name,
                   !!read.hasClass(attr_name), send_notify);

    // if (ev) {
    //     ev.stopPropagation();
    // }
    return false;
}
