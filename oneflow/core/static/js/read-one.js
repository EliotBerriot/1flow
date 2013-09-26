
//'use strict';

var change_selector_ids   = []; // not used anymore, thus empty.
var read_actions_messages = {};

function mark_something(read_id, mark_what, mark_inverse, send_notify, message, callback) {

    var run_callback = function() {
        //console.debug('trying to run callback ' + callback + '(' + oid + ')');
        typeof callback === 'function' && callback(read_id, mark_what, mark_inverse, send_notify, message);
    };

    var read = $("#" + read_id);

    console.debug('mark_something(' + read_id + ', ' + mark_what + ', ' + mark_inverse + ');');

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
            //console.debug(read.find(".action-mark-" + klass));
            //console.debug(read.find(".action-mark-" + inverse));

            read.find(".action-mark-" + klass).fadeOut('fast', function(){
                read.find(".action-mark-" + inverse).fadeIn('fast');
            });

            _.each(change_selector_ids, function(sel) {
                $(sel + read_id).removeClass(inverse).addClass(klass);
            });

            read.removeClass(inverse).addClass(klass);

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

            run_callback();
        }
    );

    // avoid any click event to propagate?
    return false;
}

function post_mark_triggers(read_id, attr_name, send_notify) {

    var $read = $("#" + read_id);

    if (attr_name == 'is_bookmarked') {

        if (preferences.bookmarked_marks_unread) {

            //console.debug('item ' + read_id + ' bookmarked.');
            //console.debug($read.hasClass('is_bookmarked'));
            //console.debug($read.hasClass('is_read'));

            if($read.hasClass('is_bookmarked')
                    && $read.hasClass('is_read')) {

                // 'true' means mark 'inverse' of is_read.
                mark_something(read_id, 'is_read', true, send_notify);

                console.log('item ' + read_id + ' bookmarked; marked as unread too.');
            }
        }

    } else if (attr_name == 'is_starred') {

        console.debug('item ' + read_id + ' starred.');

        if (preferences.starred_marks_read) {

            if($read.hasClass('is_starred')
                    && $read.hasClass('not_is_read')) {

                mark_something(read_id, 'is_read', false, send_notify);

                console.log('item ' + read_id + ' starred; marked as read too.');
            }
        }

        if (preferences.starred_removes_bookmarked) {

            if($read.hasClass('is_starred')
                    && $read.hasClass('is_bookmarked')) {

                mark_something(read_id, 'is_bookmarked', true, send_notify);

                console.log('item ' + read_id + ' starred; unbookmarked too.');
            }
        }
    }
}

function toggle_status(read_id, attr_name, send_notify) {

    var $read = $("#" + read_id);

    mark_something(read_id, attr_name,
                   !!$read.hasClass(attr_name),
                   send_notify, null,
                   function() {
                        post_mark_triggers(read_id, attr_name, send_notify);
                   }
                );

    // if (ev) {
    //     ev.stopPropagation();
    // }
    return false;
}
