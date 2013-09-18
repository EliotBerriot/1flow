
'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.

// TODO: put this in our own namespace, not in the window…

// ——————————————————————————————————————————————————————————— for memories
// different value for toggle_content()::open_me()
//
// TODO: if (!inViewport(me))
//scrollToElement(me, scroll_speed, $(me).height());
//scrollToElement(me, scroll_speed, 0);
//scrollToElement(me);
// put the current item in the center of the window.
//scrollToElement(me, scroll_speed, $(window).height() / 2);
// put the current item in the upper part of the window.
//scrollToElement(me, scroll_speed, $(window).height() / 4);


common_init();


function eventually_toggle(event) {
    // see http://stackoverflow.com/a/9183467/654755 for the base I used.

    //console.log('toggled: ' + event.target);

    if ($(event.target).attr('href') == undefined) {
        var togglable   = $(this).closest('.slide-togglable');
        var custom_func = togglable.data('toggle-function');
        var custom_cbk  = togglable.data('toggle-callback');
        var target_sel  = togglable.data('toggle-id');

        if (custom_func != 'undefined') {

            if (custom_cbk != 'undefined') {
                window[custom_func](target_sel,
                                    window[custom_cbk]);
            }

            window[custom_func](target_sel);

        } else {

            if (custom_cbk != 'undefined') {
                togglable.slideToggle(function(){
                    // we have to pass the OID in some way, thus we do not
                    // simply pass the callback like we do for `custom_func`.
                    window[custom_cbk](target_sel);
                });
            }

            togglable.slideToggle();
        }
    }

    event.stopPropagation();
}

function read_setup(parent) {
    // this function is run after each ajax call, via setup_everything().

    $(".article-content p").find('img').parent().addClass('img-legend');

    //console.debug('read setup bindings');
    //find_start(parent, 'slide-togglable').dblclick(eventually_toggle);
}

function read_init(){
    // for now, this one does nothing.
    // It's not mandatory to create it,
    // but I keep it here as an example.
};

var open_content = null;
var last_opened  = null;

function notice_element(oid) {

    flash_fade($("#" + oid + " .article"), "#ddd", "#bbb");
}

function toggle_content(oid, callback) {

    var run_callback = function() {
        typeof callback === 'function' && callback(oid);
    };

    var me      = "#" + oid,
        content = $("#content-" + oid),

        open_me = function(scrollTo) {

            if(typeof scrollTo == 'undefined') {
                var scrollTo = true;
            }

            // set everything open before the animation starts,
            // else potential parallely executed function could
            // fail or get the "old" (previous) values.
            last_opened  = oid;
            open_content = oid;
            //console.debug('set open to ' + oid + ' and last to ' + oid);

            if (scrollTo) {
                scrollToElement(me);
            }

            // bindable_hovered NOT USED YET
            //bindable_hovered = content;

            content.slideDown(scroll_speed, "swing", run_callback);
        };

    if (content.is(':visible')) {
        // put the current item to top of window
        scrollToElement(me, scroll_speed, 50);

        // set everything open before the animation starts,
        // else potential parallely executed function could
        // fail or get the "old" (previous) values.
        open_content = null;
        last_opened  = oid;
        //console.debug('set open to null and last to ' + oid);

        content.slideUp(scroll_speed, "swing", run_callback);

        // bindable_hovered NOT USED YET
        //
        // This is not mandatory, but doesn't hurt.
        // As we close the content, there is nothing
        // bindable anymore, anyway.
        //bindable_hovered = null;

    } else {
        if(open_content != null) {
            var to_close   = open_content,
                current    = "#" + open_content,
                cur_height = $(current).height();

            // compensate the slideUp() of the current open
            // element if it's located before us, else the
            // movement in not visually fluent.
            if ($(current).data('index') < $(me).data('index')) {
                scrollToElement(me, scroll_speed, cur_height);
                open_me(false);

            } else {
                open_me(true);
            }

            $("#content-" + to_close).slideUp(scroll_speed, "swing");

        } else {
            open_me(true);
        }
    }
}

function open_next_read() {

    function open_next_internal(which) {

        var next = $("#" + which)
            .closest('.read-list-item')
            .next('.read-list-item');

        toggle_content(next.attr('id'));
    }

    if (open_content) {
        open_next_internal(open_content);

    } else {
        if (last_opened) {
            open_next_internal(last_opened);

        } else {
            notify({
                text: read_actions_messages.open_first,
                type: 'info',
                icon: false,
                sticker: false
            });

            toggle_content($('.read-list-item').first().attr('id'));
        }
    }
}
function open_previous_read() {

    if (last_opened) {

        var previous = $("#" + last_opened)
            .closest('.read-list-item')
            .prev('.read-list-item');

        if (previous) {
            toggle_content(previous.attr('id'));

        } else {
            notify({
                text: "{% trans 'No Previous, captain. You are at the top!' %}",
                type: 'warning',
                icon: false,
                sticker: false
            });
        }

    } else {
        notify({
            text: "{% trans 'Already at the top!' %}",
            type: 'info',
            icon: false,
            sticker: false
        });
    }
}
function close_current_read() {
    if (open_content) {
        return toggle_content(open_content);
    }
}
