
'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.

// TODO: put this in our own namespace, not in the window…


common_init();

function eventually_toggle(event) {
    // see http://stackoverflow.com/a/9183467/654755 for the base I used.

    console.log('toggled: ' + event.target);

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

    //console.debug('read setup binding…');

    find_start(parent, 'slide-togglable').click(eventually_toggle);

}

// for now, this one does nothing.
// It's not mandatory to create it,
// but I keep it here as an example.
function read_init(){};

var open_content = null;
var scroll_speed = 750;

function scrollToElement(target, speed, topoffset) {

    var element = $(target);

    if(typeof speed == 'undefined') {
        var speed = scroll_speed;
    }

    //
    // NOTE: 10px is the "comfort margin" to avoid cropping the article
    //       title or rewinding while sliding up an upper element.
    //

    if(typeof topoffset == 'undefined') {
        var topoffset = element.height() + 10;

    } else {
        topoffset += 10;
    }

    // console.log('>>> scrolling back to');
    // console.log(target);
    // console.log(element);
    // console.log('>>> with offset');
    // console.log(topoffset);

    var destination = element.offset().top - topoffset;

    $('html:not(:animated),body:not(:animated)')
        .animate({scrollTop: destination}, speed, function() {
            // disabled, it doesn't play nice with Bootstrap's
            // topnav: the target get hidden behind, and the end
            // of the scrolling is flaky.
            //
            //window.location.hash = target;
        });

    return false;
}

function notice_element(oid) {

    flash_fade($("#" + oid + " .article"), "#ddd", "#bbb");
}

function toggle_content(oid, callback) {

    var run_callback = function() {
        typeof callback === 'function' && callback(oid);
    };

    var me      = "#" + oid,
        content = $("#content-" + oid),

        open_me = function(scrollTo, callback) {

            if(typeof scrollTo == 'undefined') {
                var scrollTo = true;
            }

            if (scrollTo) {
                scrollToElement(me);
            }

            content.slideDown(scroll_speed, "swing", run_callback);
        };

    if (content.is(':visible')) {

        // TODO: if (!inViewport(me))
        //scrollToElement(me, scroll_speed, $(me).height());
        //scrollToElement(me, scroll_speed, 0);
        //scrollToElement(me);

        // put the current item to top of window
        scrollToElement(me, scroll_speed, 50);

        // put the current item in the center of the window.
        //scrollToElement(me, scroll_speed, $(window).height() / 2);

        // put the current item in the upper part of the window.
        //scrollToElement(me, scroll_speed, $(window).height() / 4);

        content.slideUp(scroll_speed, "swing", run_callback);
        open_content = null;

    } else {
        if(open_content != null) {

            var current    = "#" + open_content,
                cur_height = $(current).height();

            // compensate the slideUp() of the current open
            // element if it's located before us, else the
            // movement in not visually fluent.
            if ($(current).data('index') < $(me).data('index')) {
                scrollToElement(me, scroll_speed, cur_height);
                open_me(false);

            } else {
                open_me(true, run_callback);
            }

            $("#content-" + open_content).slideUp(
                scroll_speed, "swing",
                function() {
                    open_content = oid;
                    run_callback();
                }
            );

        } else {
            open_me(true, run_callback);
            open_content = oid;
        }

    }

    // in case we where clicked.
    return false;
}
