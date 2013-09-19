
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

    debug_notify('eventually_toggle ' + event);

    if ($(event.target).attr('href') == undefined) {
        var togglable   = $(this).closest('.slide-togglable');
        var custom_func = togglable.data('toggle-function');
        var custom_cbk  = togglable.data('toggle-callback');
        var target_sel  = togglable.data('toggle-id');

        if (custom_func != 'undefined'
                && typeof window[custom_func] == 'function') {

            if (custom_cbk != 'undefined'
                    && typeof window[custom_cbk] == 'function') {

                window[custom_func](target_sel,
                                    window[custom_cbk]);
            } else {
                window[custom_func](target_sel);
            }

        } else {

            if (custom_cbk != 'undefined'
                    && typeof window[custom_cbk] == 'function') {

                togglable.slideToggle(function(){

                    // we have to pass the OID in some way, thus we do not
                    // simply pass the callback like we do for `custom_func`.
                    window[custom_cbk](target_sel);
                });
            } else {
                togglable.slideToggle();
            }
        }
    }

    event.stopPropagation();
}

function read_setup(parent) {
    // this function is run after each ajax call, via setup_everything().

    //console.debug('read setup bindings');
   //debug_notify('read_setup(' + parent + ')');

    $(".article-content p").find('img').parent().addClass('img-legend');

    if(!Modernizr.touch) {
        find_start(parent, 'content-toggle').on('click', function(ev){
            var target   = $(this).data('toggle-id'),
                callback = $(this).data('toggle-callback');

            if(!target) {
                console.error('No target (data-toggle-id) for ' + this + '!');
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            toggle_content(target, callback);
        });

        find_start(parent, 'slide-togglable').on('tripleclick', eventually_toggle);
    }
}

function read_init(){
    // for now, this one does nothing.
    // It's not mandatory to create it,
    // but I keep it here as an example.
};

// These will hold IDs of DOM/jQuery elements.
var open_content = null;
var last_opened  = null;
var open_actions = null;

function notice_element(oid) {

    flash_fade($("#" + oid + " .article"), "#ddd", "#bbb");
}
function toggle_content(oid, callback) {

    debug_notify('toggle_content(' + oid + ', ' + callback + ')');

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
        //console.debug(oid + ' not visible.');

        if(open_content != null) {

            //console.debug('open_content: ' + open_content);

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

        if (next.length) {
            toggle_content(next.attr('id'));
        } else {
            notify({
                text: read_actions_messages.already_at_end,
                type: 'warning',
                icon: false,
                sticker: false
            });
        }
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

    function open_previous_internal(which) {
        var previous = $("#" + which)
            .closest('.read-list-item')
            .prev('.read-list-item');

        if (previous.length) {
            toggle_content(previous.attr('id'));

        } else {
            notify({
                text: read_actions_messages.already_top_first,
                type: 'warning',
                icon: false,
                sticker: false
            });
        }
    }

    if (open_content) {
        open_previous_internal(open_content);

    } else {
        if (last_opened) {
            open_previous_internal(last_opened);

        } else {
            notify({
                text: read_actions_messages.already_top_more,
                type: 'info',
                icon: false,
                sticker: false
            });
        }
    }
}
function close_current_read() {
    if (open_content) {
        return toggle_content(open_content);
    }
}
function open_last_opened() {
    if (last_opened && !open_content) {
        debug_notify('re-opening ' + last_opened);
        return toggle_content(last_opened);
    }
}
function mark_current_read_as_read() {
    if (open_content) {
        var read = $("#" + open_content);

        if (read.hasClass('not_is_read')) {
            return mark_something(open_content, 'is_read');
        }
    }
}
function mark_current_read_as_starred() {
    if (open_content) {
        var read = $("#" + open_content);

        if (read.hasClass('not_is_starred')) {
            return mark_something(open_content, 'is_starred');
        }
    }
}
function mark_current_read_as_bookmarked() {
    if (open_content) {
        var read = $("#" + open_content);

        if (read.hasClass('not_is_bookmarked')) {
            return mark_something(open_content, 'is_bookmarked');
        }
    }
}
function toggle_current_read_is_read() {

    if (open_content) {
        return toggle_is_read(open_content);

    } else {
        notify({
            text: read_actions_messages.is_read.nothing,
            type: 'warning',
            icon: false,
            sticker: false
        });
    }
}
function toggle_current_read_is_starred() {

    if (open_content) {
        return toggle_is_starred(open_content);

    } else {
        notify({
            text: read_actions_messages.is_starred.nothing,
            type: 'warning',
            icon: false,
            sticker: false
        });
    }
}
function toggle_current_read_is_bookmarked() {

    if (open_content) {
        return toggle_is_bookmarked(open_content);

    } else {
        notify({
            text: read_actions_messages.is_bookmarked.nothing,
            type: 'warning',
            icon: false,
            sticker: false
        });
    }
}

function show_actions(objekt) {
    // objekt is a DOM entity

    debug_notify('Opening actions for ' + objekt);

    if (open_actions) {
        hide_actions(document.getElementById(open_actions));
    }

    show_hover_muted.call(objekt);
    open_actions = objekt.getAttribute('id');
}
function hide_actions(objekt) {
    // objekt is a DOM entity

    debug_notify('Closing actions for ' + objekt);

    hide_hover_muted.call(objekt);
    open_actions = null;
}

function handle_tap(ev) {

    var $this  = $(this),
        target = $this.data('toggle-id') || $this.attr('id');

    function open_or_hide_actions() {

        debug_notify('Acting on ' + target);

        if (open_content && open_content == target) {
            show_actions(document.getElementById(target));

        } else {
            hide_actions(document.getElementById(target));
        }
    }

    if (ev.gesture.touches.length > 3) {
        return;
    }

    // WOW. without ev.preventDefault(), the 2 others
    // don't suffice to avoid the event being sent twice.
    ev.gesture.preventDefault();
    ev.stopPropagation();
    ev.preventDefault();

    if (ev.gesture.touches.length == 3) {
        debug_notify('3-fingers tap on ' + target);
        open_or_hide_actions();

    } else if (ev.gesture.touches.length == 2) {
        debug_notify('2-fingers tap on ' + target);
        toggle_is_starred(target);

    } else {
        debug_notify('1-finger tap on ' + target);
        toggle_content(target, open_or_hide_actions);
    }
    return false;
}

// ——————————————————————————————————————————————————— open first/next/previous

// “Next”, “Goto Next”, “Open Next”
Mousetrap.bind(['n', 'g n', 'o n'], function() {
    open_next_read();
    return false;
});

// “Previous”, “Goto Previous”, “Open Previous”
Mousetrap.bind(['p', 'g p', 'o p'], function() {
    open_previous_read();
    return false;
});

// “Close”
Mousetrap.bind(['c'], function() {
    close_current_read();
    return false;
});

// “Last Open” (re-open last closed one)
// WARNING: using just 'o' as only shortcut won't work because
//          of other multi-key shortcuts starting with an 'o'.
Mousetrap.bind(['l o', 'o l'], function() {
    open_last_opened();
    return false;
});

// —————————————————————————————————————————————————— actions on currently open

// “Mark Read”, “Toggle Read”
Mousetrap.bind(['m r', 't r'], function() {
    toggle_current_read_is_read();
    return false;
});

// “Mark Starred”, “Toggle Starred”
Mousetrap.bind(['m s', 't s'], function() {
    toggle_current_read_is_starred();
    return false;
});
// “Mark [fF]or Later”, “Toggle Later status”,
// “Mark Bookmarked”, “Toggle Bookmarked”,
// “Keep For Later”, “Read Later”
Mousetrap.bind(['m l', 't l', 'm b', 't b',
                'r l', 'm f l', 'k f l'], function() {
    toggle_current_read_is_bookmarked();
    return false;
});

// —————————————————————————————————————————————————————————— read-flow actions

// “Mark Read” + “Next”, “Goto Next”, “Open Next”
Mousetrap.bind(['shift+r', 'shift+n'], function() {
    mark_current_read_as_read();
    open_next_read();
    return false;
});


// “Mark Read” + “Next”, “Goto Next”, “Open Next”
Mousetrap.bind(['shift+p'], function() {
    mark_current_read_as_read();
    open_previous_read();
    return false;
});

// “Star and go next”
Mousetrap.bind(['shift+s'], function() {
    mark_current_read_as_starred();
    open_next_read();
    return false;
});

// “mark for Later and go next”
Mousetrap.bind(['shift+l'], function() {
    mark_current_read_as_bookmarked();
    open_next_read();
    return false;
});

// ——————————————————————————————————————————————————————————————— touch events

if (Modernizr.touch) {

    //console.debug('touch events start…');

    hammertime.on("swipeleft", ".read-list-item", function(ev) {

        if (ev.gesture.touches.length != 1) {
            return;
        }

        var $this = $(this);

        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        $this.animate({marginLeft: -50}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });
        toggle_is_read($this.attr('id'));

        return false;
    });

    hammertime.on("swiperight", ".read-list-item", function(ev) {

        if (ev.gesture.touches.length != 1) {
            return;
        }

        var $this = $(this);

        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        $this.animate({marginLeft: 50}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        toggle_is_bookmarked($this.attr('id'));

        return false;
    });

    hammertime.on("swipeleft", ".article-content", function(ev) {
        var $this = $(this);

        if(ev.gesture.touches.length == 2) {

            ev.gesture.preventDefault();
            ev.stopPropagation();
            ev.preventDefault();

            open_next_read();
        }

        return false;
    });

    hammertime.on("swiperight", ".article-content", function(ev) {
        var $this = $(this);

        if(ev.gesture.touches.length == 2) {

            ev.gesture.preventDefault();
            ev.stopPropagation();
            ev.preventDefault();

            open_previous_read();
        }

        return false;
    });

    /*
        NOT READY YET

    hammertime.on("swipeleft", ".read-list-item", function(ev) {
        var $this = $(this);

        $this.animate({marginLeft: -ev.distance}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        var something_done = false;

        if (ev.distance > 100) {
            if ($this.hasClass("hover-muter-open")) {
                $this.removeClass("hover-muter-open");
                hide_hover_muted.call(this);
            }

            something_done = true;

        } else if (ev.distance > 25) {
            toggle_is_read($this.attr('id'));
            something_done = true;
        }

        if (something_done) {
            ev.gesture.preventDefault();
            ev.stopPropagation();
        }
    });

    hammertime.on("swiperight", ".read-list-item", function(ev) {
        var $this = $(this);

        $this.animate({marginLeft: ev.distance}, 200, function(){
            $this.animate({marginLeft: 0}, 150);
        });

        var something_done = false;

        if (ev.distance > 100) {
            if (!$this.hasClass("hover-muter-open")) {
                $this.addClass("hover-muter-open");
                show_hover_muted.call(this);
            }
            something_done = true;

        } else if (ev.distance > 25) {
            toggle_is_bookmarked($this.attr('id'));
            something_done = true;

        }

        if (something_done) {
            ev.gesture.preventDefault();
            ev.stopPropagation();
        }
    });

        END NOT READY YET
    */

    hammertime.on("tap", ".article-meta .heading", handle_tap);
    hammertime.on("tap", ".article-meta .meta",    handle_tap);

    hammertime.on("pinchin doubletap", ".article-content", function(ev) {

        // WOW. without ev.preventDefault(), the 2 others
        // don't suffice to avoid the event being sent twice.
        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        var $this  = $(this),
            target = $this.data('toggle-id');

        debug_notify('pinch/dbltap event on ' + target);

        toggle_content(target, function() {
            hide_actions(document.getElementById(target));
        });
    });

    hammertime.on("pinchout", ".article-meta", function(ev) {

        // WOW. without ev.preventDefault(), the 2 others
        // don't suffice to avoid the event being sent twice.
        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        var $this  = $(this),
            target = $this.data('toggle-id');

        debug_notify('pinchout event on ' + target);

        toggle_content(target, function() {
            show_actions(document.getElementById(target));
        });
    });

    hammertime.on("hold", ".read-list-item", function(ev) {

        // WOW. without ev.preventDefault(), the 2 others
        // don't suffice to avoid the event being sent twice.
        ev.gesture.preventDefault();
        ev.stopPropagation();
        ev.preventDefault();

        var $this = $(this);

        if ($this.hasClass("hover-muter-open")) {
            hide_actions(this);

        } else {
            show_actions(this);
        }
    });
}
