
'use strict';

common_init();


function read_setup() {
    // this function is run after each ajax call, via setup_everything().

    $(".article-content p").find('img').parent().addClass('img-legend');

}

// for now, this one does nothing.
// It's not mandatory to create it,
// but I keep it here as an example.
function read_init(){};

var open_content = null;
var scroll_speed = 750;

function scrollToElement(target, speed, topoffset) {

    var element = jQuery(target);

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

    //console.log(target);
    //console.log(topoffset);

    var destination = element.offset().top - topoffset;

    jQuery('html:not(:animated),body:not(:animated)')
        .animate({scrollTop: destination}, speed, function() {
            // disabled, it doesn't play nice with Bootstrap's
            // topnav: the target get hidden behind, and the end
            // of the scrolling is flaky.
            //
            //window.location.hash = target;
        });

    return false;
}

function toggle_content(oid) {

    var me      = "#" + oid,
        content = $("#content-" + oid),

        open_me = function(scrollTo) {

            if(typeof scrollTo == 'undefined') {
                var scrollTo = true;
            }

            if (scrollTo) {
                scrollToElement(me);
            }

            content.slideDown(scroll_speed, "swing");
        };

    if (content.is(':visible')) {
        content.slideUp(scroll_speed, "swing");
        open_content = null;

    } else {
        if(open_content != null) {

            var current    = "#" + open_content,
                cur_height = $(current).height();

            // compensate the slideUp() of the current open element if
            // it is before us, else the movement in not visually fluent.
            if ($(current).data('index') < $(me).data('index')) {
                scrollToElement(me, scroll_speed, cur_height);
                open_me(false);

            } else {
                open_me();
            }

            $("#content-" + open_content).slideUp(
                scroll_speed, "swing",
                function(){
                    open_content = oid;
                }
            );

        } else {
            open_me();
            open_content = oid;
        }

    }

    // in case we where clicked.
    return false;
}

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.
