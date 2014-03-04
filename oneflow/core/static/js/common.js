// warning: don't "use strict"; here, it will break things.
// I need to learn to write good JS first. Sorry for that.

var page_cleaner_interval;
var scroll_speed = 500;
var debug_touch = false;
var open_hover_muted = [];
var hover_muted_timers = {};
var last_updated = new Date().getTime();

function check_needs_update() {
    // needs a global var "last_updated".
    // works with start_checking_for_needed_updates().

    var now = new Date().getTime();

    //console.log(now - last_updated);

    if (now - last_updated > 5000) {
        try {
            window['update_needed']();

        } catch (err) {
            console.error('Could not run update_needed(): ' + err);
        }
    }

    last_updated = now;
}
function start_checking_for_needed_updates() {
    // works with check_needs_update().

    setInterval(check_needs_update, 1000);
}

try {
    $.pnotify.defaults.delay = 5000;
} catch (err) {
    console.log('Pines notify seems not to be present: ' + err);
}


// bindable_hovered NOT USED YET
//var bindable_hovered = null;

try {
    var hammertime = $("#application").hammer({
    //drag: false,
    // drag_vertical: false,
    // drag_horizontal: false,
    transform: false,
    transformend: false,
    swipe_max_touches: 3,
    swipe_velocity: 0.5
    //stopBrowserBehavior: {userSelect: true}
    // swipe: false,
    // tap: false,
    // tap_double: true,
    // hold: false,
});

} catch (err) {
    console.log("Hammer seems not to be present: " + err);
    var hammertime = null;
}

function csrfSafeMethod(method) {
    // these HTTP methods do not require CSRF protection
    return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
}

function notify(params){
    // did you ever see a that-simple wrapper?
    $.pnotify(params);
}

function debug_notify(message) {
    if (debug_touch) {
        notify({
            text: message,
            type: 'warning',
            icon: false,
            sticker: false,
            width: '500px',
        });
    }
}

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
function find_start(parent, klass){

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    if (parent.hasClass(klass)){
        start = parent;

    } else {

        try {
            // HEADS UP: SORRY THIS TEST IS WEAK.
            // But sufficient for our current needs.
            if (klass.indexOf("[") != -1) {
                // we are not exactly finding a simple CSS class,
                // but any jQuery/HTML/CSS selector.

                start = parent.find(klass);

            } else {
                start = parent.find('.' + klass);
            }

        } catch (err) {
            console.error('Error finding ' + klass + ' in '
                          + parent + ': ' + err)
        }
    }

    //console.debug('start for ' + klass + ' in ' + parent + ':');
    //console.debug(start);

    return start;
}
function parseBool(val) {
    if (typeof val === 'string') {
        if (val.toLowerCase() === 'true') {
            return true;

        } else if (val.toLowerCase() === 'false') {
            return false;

        } else {
            return null;

        }
    } else if (typeof val === 'int') {
        if (val === 0) {
            return false;

        } else {
            return true;

        }
    } else {
        return null;

    }
}
function update_instance(model, iid, created, new_html) {
    // This function will work with anything, but best for replacing a <tr>
    // with a new one, already rendered.
    //

    new_  = $(new_html);

    table = $('#model_' + model + '_table');
    old   = $('#' + model + '_' + iid);

    if (old.length) {
        // this instance was already known.
        // remove the old corresponding ROW.
        old.attr('id', 'old_' + old.attr('id'));
        old.addClass('to-remove');

        // in case of quick-multi-updates
        old.removeClass('new-fade');
        old.stop(true, true);

        old.before(new_);

        old.hide();

    } else {
        // we've got a new challenger, insert it at the end.
        last = table.find('tbody:last');

        last.append(new_);

        // Update the total number of elements.
        count = $('#model_' + model + '_count');
        count.html(parseInt(count.html()) + 1);

        if(parseInt(count.html()) == 1) {
            nomore = table.find('tfoot > tr.no-data');
            nomore.hide();
        }
    }

    new_.addClass('new-fade');
    new_.show();

    // don't forget links, modals, popovers…
    setup_everything(new_);

    //console.log('re-sort on ' + [table.get(0).config.sortList]);

    // re-sort the table.
    table.trigger("update")
        .trigger("sorton", [table.get(0).config.sortList]);
      //.trigger("appendCache");
      //.trigger("applyWidgets");

    // remove old stuff marked as such.
    page_cleaner();
}
function remove_instance(model, iid) {
    // This function will work with anything, but best for replacing a <tr>
    // with a new one, already rendered.

    table = $('#model_' + model + '_table');
    old   = $('#' + model + '_' + iid);

    if (old.length) {
        // this instance is in the page. Make it "whoosh!".
        old.attr('id', 'old_' + old.attr('id'));
        old.addClass('to-remove');

        // in case of quick-multi-updates
        old.removeClass('new-fade');
        old.stop(true, true);

        old.hide();

        // Update the total number of elements.
        count = $('#model_' + model + '_count');
        count.html(parseInt(count.html()) - 1);

        if(parseInt(count.html()) < 1) {
            nomore = table.find('tfoot > tr.no-data');
            nomore.show();
        }
    }

    // re-sort the table.
    table.trigger("update")
        .trigger("sorton", [table.get(0).config.sortList]);

    // remove old stuff marked as such.
    page_cleaner();
}
function popover_placement(objekt, parent) {

    if ($(parent).hasClass('popover-left')){
        return 'left';

    } else if ($(parent).hasClass('popover-bottom')){
        return 'bottom';

    } else if ($(parent).hasClass('popover-top')){
        return 'top';

    } else {
        return 'right';
    }
}
function page_cleaner() {
    // most of the time, this operation fails when run from inside the
    // update_instance() function, but succeeds when run from outside.
    // Don't ask me why. But it has to be done, else the page is more
    // and more cluttered when time passes by.

    try {
        $('body').find('.to-remove').each(function(){
            $(this).remove();
        });

    } catch (err) {
        try {
            console.debug('page_cleaner: ' + err);

        } catch (err) {
            // nothing. Silently ignored.
        }
    }
}
function table_sort_extractor(node) {

    s = $(node).data('sort');

    if (typeof s === 'undefined') {
        return node.innerHTML;

    } else {
        return s;

    }
}
function setup_table_sorter() {
    $("table.sortable").tablesorter({
        //sortList: [[0, 0], [1, 0]],
        sortList: [[0, 0]],
        textExtraction: table_sort_extractor,
    });
    //.bind('sortEnd', function(sorter) {
    //  currentSort = sorter.target.config.sortList;
    //});
}
function setup_popovers(parent){

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    // We need the "click" for touch interfaces to be able to close
    // twitter popovers. Not needed for clickovers, though, which
    // work perfectly.
    // https://github.com/twitter/bootstrap/issues/3417
    // parent.find('[rel="popover"]').popover({
    //         placement: popover_placement }).click(function(e) {
    //     $(this).popover('toggle');
    // });

    // Bootstrap 2.3+
    parent.find('[data-toggle=popover]').popover();
}
function show_hover_muted() {
    // "this" is a DOM entity

    var $this = $(this);
    var myid = $this.attr('id');

    if ($this.hasClass('hover-muted-shown')) {

        try {
            clearTimeout(hover_muted_timers[myid])
            delete hover_muted_timers[myid];
        } catch (err) {}

        //console.log('showing: ' + myid + ' again (cleared timer)!')

        return;
    }

    // close all other open muters
    _.each(open_hover_muted, function(otherid) {
        try {
            clearTimeout(hover_muted_timers[otherid]);
            delete hover_muted_timers[otherid];
        } catch (err) {}

        hide_hover_muted.call(document.getElementById(otherid));
    });

    open_hover_muted = [];

    //console.log('showing: ' + myid)

    $this.find('.hover-muted').each(function(){
        var $this = $(this);

        if($this.hasClass('hide')){
            $this.show(function(){
                $this.animate({
                    opacity: 1
                }, 250);
            });

        } else {
            $this.animate({
                    opacity: 1
            }, 250);
        }
    });

    open_hover_muted.push(myid);

    $this.addClass('hover-muted-shown');
}
function hide_hover_muted() {
    // "this" is a DOM entity

    var $this = $(this);
    var myid = $this.attr('id');

    if (!$this.hasClass('hover-muted-shown')) {
        //console.log('hiding: ' + myid + ' not shown!')
        return;
    }

    $this.find('.hover-muted')
        .stop(true, true).animate({
            opacity: 0
        }, 250, function(){
            // WARNING: $(this) is the "new" one from .find(), not the parent…
            if($(this).hasClass('hide')){
               $(this).hide();
            }
        });

    $this.removeClass('hover-muted-shown');

    // useless: we were just called by the time, it already timed out.
    //clearTimeout(hover_muted_timers[this])

    // clear for next detection.
    delete hover_muted_timers[myid];
    open_hover_muted = _.without(open_hover_muted, myid);

    //console.log('hiding: cleared timer ' + myid)
}
function trigger_hide_over_muted() {

    var shown = this;
    var myid = $(this).attr('id');

    // console.log('HIDE');
    // console.log(this);
    // console.log($(this));
    // console.log(myid);

    if (!$(this).hasClass('hover-muted-shown')) {
        //console.log('trigger hide of ' + myid + ' not needed.')
        return;
    }

    if (typeof hover_muted_timers[myid] != 'undefined') {
        //console.log('trigger hide of ' + myid + ': timer restart.')
        clearTimeout(hover_muted_timers[myid])
    }

    //console.log('trigger hide of ' + myid + '.')

    hover_muted_timers[myid] = setTimeout(function() {
        hide_hover_muted.call(shown)
    }, 2000);
}
function setup_hover_muters(parent){

    // NOTE: we really want mouseover() (not mouseenter()), to not
    // trigger the "out" when mouse gets over a sub-dropdown or a
    // sub-tooltip.
    find_start(parent, 'hover-unmute-children')
        .mouseover(show_hover_muted).mouseleave(trigger_hide_over_muted);
}
function clicker_muter_toggle(ev, group_name) {

    // console.log('clicker_muter_toggle: ' + group_name);
    // console.log($(this));
    // console.log($(this).closest('.clicker-muter-constrainer'));
    // console.log($(this).closest('.clicker-muter-constrainer')
    //                 .find('.clicker-muted'));

    $(this).closest('.clicker-muter-constrainer')
        .find('.clicker-muted').each(function(thing) {
            //console.log('clicker-muter: ' + thing + this);

            var $this = $(this);
            if ($this.data('clicker-muter-group') == group_name) {
                $this.slideToggle();
            }
        });

    // stopPropagation & preventDefault
    return false;
}
function setup_clicker_muters(parent){

    // NOTE: we really want mouseover() (not mouseenter()), to not
    // trigger the "out" when mouse gets over a sub-dropdown or a
    // sub-tooltip.
    find_start(parent, 'clicker-muter-toggle')
        .on("click", function(ev) {
            var group_name = $(this).data('clicker-muter-group');
            return clicker_muter_toggle.call(this, ev, group_name);
        });
}

function setup_collapsibles(parent){

    // NOTE: we really want mouseover() (not mouseenter()), to not
    // trigger the "out" when mouse gets over a sub-dropdown or a
    // sub-tooltip.
    find_start(parent, 'collapse')
        .on('hidden', function(e){
      e.stopPropagation();
    });
}

function setup_tooltips(parent){

    //
    // NOTE: we chose popover-tooltip as the trigger class,
    //      because data-toggle is too slow to get on big
    //      pages, and .tooltip is already taken by the CSS
    //      and messes the visual. This is a tradeoff when
    //      using only classes: they can conflict with CSS.
    //

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    parent.find('[data-toggle="tooltip"]')
        .on("hidden", function (e) {
            // https://github.com/twbs/bootstrap/issues/6942
            // .on('hide'…) doesn't work, it's "hidden" now.
            e.stopPropagation();
        })
        .tooltip({
            placement: popover_placement,
            // Since Bootstrap 2.2 http://stackoverflow.com/q/14025438/654755
            container: 'body'
        })
        .click(function(e) {
            $(this).tooltip('toggle');
        });

    // We need the "click" for touch interfaces to be able to close
    // twitter popovers. Not needed for clickovers, though, which
    // work perfectly.
    // https://github.com/twitter/bootstrap/issues/3417
    parent.find('.popover-tooltip')
        .on("hidden", function (e) {
            // https://github.com/twbs/bootstrap/issues/6942
            // .on('hide'…) doesn't work, it's "hidden" now.
            e.stopPropagation();
        })
        .tooltip({
            placement: popover_placement,
            // Since Bootstrap 2.2 http://stackoverflow.com/q/14025438/654755
            container: 'body'
        })
        .click(function(e) {
            $(this).tooltip('toggle');
        });
}
function setup_clickovers(parent) {

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    parent.find('[data-toggle="clickover"]').each(function(){

        var $this  = $(this),
            params = {};

        if ($this.hasClass('clickover-large')) {
            $.extend(params, { width: 400 });
        }

        if ($this.hasClass('iframed')) {
            $.extend(params, { width: 800, height: 450 });
        }

        if ($this.hasClass('clickover-auto-close')) {
            $.extend(params, { auto_close: 5000 });
        }

        // WARNING: don't use "data-clickover", it will conflict
        // with rel="clickover" and the clickover will not work.

        data_ = $this.data('clickover-params');

        if (typeof data_ != 'undefined') {
            $.extend(params, eval(data_));
        }

        $.extend(params, { placement: popover_placement });

        $this.clickover(params);
    });
}
function setup_delayed_loaders(parent) {
    // https://github.com/twitter/bootstrap/issues/2380

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    parent.find('.delayed-loader').each(function() {
        $(this).click(function(){
            target = $('body').find($(this).attr('href')).find('.delayed-target');

            //console.log('(delayed until now) loading of ' + target.attr('delayed-src'));

            target.attr('src', target.attr('delayed-src'));
        });
    });
}
function flash_fade(objekt, bg_color, fg_color){

    var curfore = objekt.css('color');
    var curback = objekt.css('backgroundColor');

    if (typeof bg_color == 'undefined') {
        bg_color = "#ffff99";
    }

    if (typeof fg_color == 'undefined') {
        // by default we don't animate the foreground color.
        fg_color = curfore;
    }

    objekt.animate({ backgroundColor: bg_color,
                     color: fg_color }, 50,
       function() {
            //.delay(2500) in MyLicorn® (time to notice if we have a lot)
            //.delay(100) still seems too slow.
            objekt.animate({ backgroundColor: curback,
                             color: curfore }, 1000, 'easeOutCubic');

            // Fade is done, object is not "new" anymore.
            try {
                objekt.removeClass('new-fade');
            } catch (err) {
                // don't crash if the object doesn't have the class.
                // sometimes we call the function directly.
            }
        }
    );
}
function launch_faders(parent) {
    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    if (parent.hasClass('new-fade')) {
        flash_fade(parent);
    }

    parent.find('.new-fade').each(flash_fade);
}
function launch_async_gets(parent) {

    console.debug('async_gets');

    find_start(parent, 'async-get')
        .each(function(){

            var $this     = $(this);
            var get_name  = $this.data('async-get');
            var get_value = $this.data('async-get-value');
            var get_url   = $this.attr('href') + '?'
                            + get_name + "=" + get_value;

            console.log('Setup on ' + $this);

            if (get_value == 'undefined') {
                get_value = "1";
            }

            $.get(get_url,
                function(data){
                    how_much = parseInt(data);

                    console.log('Got ' + how_much + ' for ' + get_url);

                    if(how_much == 0) {
                        $this.fadeOut();
                    } else {
                        $this.find('.count').html('&nbsp;(' + how_much + ')');
                    }
                }
            );

        });
}

// bindable_hovered NOT USED YET
function setup_hover_notifiers(parent) {
    // cf. http://stackoverflow.com/questions/3479849/jquery-how-do-i-get-the-element-underneath-my-cursor

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    if (parent.hasClass('hover-notifier')) {
        parent.on('mouseenter', function() { bindable_hovered = this; });
    }

    parent.find('.hover-notifier').on('mouseenter',
        function() { bindable_hovered = this; });
}

// bindable_hovered NOT USED YET
function on_hovered(func_if_found, func_if_not_found){
    // last hovered element can be already closed.
    // Do not act if it's the case. But if it's not,
    // we've got it's reference, even if the mouse
    // cursor got ouside :-)
    if (bindable_hovered != null) {
        element = $(bindable_hovered);
        if (element.is(':visible')) {
            return func_if_found(element);
        }
    } else {
        if (typeof func_if_not_found == 'function') {
            func_if_not_found();
        }
    }
}

function handle_modal(e) {

    //console.debug("handle_modal");

    e.preventDefault();

    var url = $(this).attr('href');

    if (url.indexOf('#') == 0) {
        //console.debug("handle_modal simple");

        $("#" + $(this).data('target')).modal('show');

    } else {
        //console.debug("handle_modal with input auto-focus");

        $.get(url, function(data) {

            $(data).modal().on("shown.bs.modal", function () {

                var $first_input = null,
                    $first_textarea = null;

                $('body').addClass('modal-open');

                setup_everything($(this));

                $(this).focus();

                //console.debug("input auto-focus...");

                $first_input = $(this).find('input:visible:enabled').first();

                if ($first_input.length) {

                    $first_input.focus(function() {
                        // OMG. Thanks http://stackoverflow.com/a/10576409/654755
                        this.selectionStart = this.selectionEnd = this.value.length;
                    });

                    $first_input.focus();

                } else {
                    // If there is no input, try with textarea.
                    // For example in the web import form…

                    $first_textarea = $('textarea:visible:enabled').first();

                    if ($first_textarea.length) {
                        $first_textarea.focus();
                    }
                }


            }).on('hidden.bs.modal', function () {

                $('body').removeClass('modal-open');
                $(this).remove();
            });
        });
    }
}

function handle_ajax_form(event) {

    var $form   = $(this);
    var $target = $($form.data('target'));

    var $simple_notify = $($form.data('simple-notify'));

    $.ajax({
        type: $form.attr('method'),
        url:  $form.attr('action'),
        data: $form.serialize(),

        success: function(data, status) {

            // NOTE: if the result is a redirect,
            //      the current code will no run.

            if (data == 'DONE' || $simple_notify.length) {
                // If there is no other data than the text "DONE", just
                // try to close the current open modal. The server-side
                // will have filled notifications and everything else.

                try {
                    $target.modal('hide');

                } catch (err) {
                    // do not crash if the target is not a modal.
                    console.warning(err);
                }

                if ($simple_notify.length) {
                    notify(data);
                }

            } else {
                // replace the current element with the result of the form.
                $target.html(data);
            }
        }
    });

    event.preventDefault();
}

function setup_async_images(parent) {
    find_start(parent, 'img[data-toggle="async"]')
        .each(function() {
            var $this = $(this);
            var get_url = $this.data("src");
            $.get(
                get_url,
                function(data) {
                    //console.log($this);
                    //console.log(this);
                    //console.log('got '+ data + ' for ' + $img.attr('src'));
                    $this.attr("src", data);
                }
            );
        });
}

function setup_modals(parent) {

    // Support for AJAX loaded modal window.
    // Focuses on first input textbox after it loads the window.
    find_start(parent, '[data-toggle="modal"]').click(handle_modal);

    // Freely inspired from https://gist.github.com/havvg/3226804
    find_start(parent, 'form[data-async]').on('submit', handle_ajax_form);
}

function setup_post_processors(parent) {

    //console.log(find_start(parent, '[data-post-process]'));

    find_start(parent, '[data-post-process]').each(function(){
        var $this = $(this);
        var func_name = $this.data('post-process');

        try {
            //console.log(func_name);
            //console.log('ON');
            //console.log($this);
            window[func_name].call(this);

        } catch(err) {
            console.debug('Exception while trying to run '
                          + func_name + '.call(' + this + '): ' + err);
        }
    });
}

// ———————————————————————————————————————————————— reusable setup_everything()

function setup_everything(parent) {
    // It will be called by common_init() on <body> at page load.
    // You can call it safely on any ajax-incoming DOM fragment
    // to setup the same things on "new" parts of the page without
    // re-walking the whole page.

    console.debug('Setup everything...');

    try {

        if (!Modernizr.touch){
            setup_tooltips(parent);
            setup_hover_muters(parent);
        }

        setup_popovers(parent);
        setup_clicker_muters(parent);
        setup_collapsibles(parent);

        // bindable_hovered NOT USED YET
        //setup_hover_notifiers(parent);

        setup_clickovers(parent);
        setup_delayed_loaders(parent);
        launch_faders(parent);

        setup_modals(parent);

        setup_async_images(parent);

        setup_post_processors(parent);

        // not fully tested, and not needed yet.
        //launch_async_gets(parent);

    } catch (err) {
        console.warn('Something is not properly loaded/initialized: ' + err);
    }

    try {
        // Given we are in <body#home>, try to run home_setup(), and so on.
        // Don't use the nasty eval if it's not strictly required. Thanks
        // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/eval

        var func_name = $('body').attr('id') + '_setup';

        window[func_name](parent);

    } catch(err) {
        console.debug('Exception while trying to run '
                      + func_name + '(): ' + err);
    }
}

// ————————————————————————————————————————————————————————————— one-time setup

function setup_auto_cleaner() {
    // every 10 minutes, the page is cleaned from old and orphaned elements.

    page_cleaner_interval = setInterval(page_cleaner, 600000);
}

function setup_keyboard() {

    $(document).keydown(function(ev) {

        var goto_location = null;

        if(ev.which == 37) {
            goto_location = $('a#previous').attr('href');
        }

        if(ev.which == 39) {
            goto_location = $('a#next').attr('href');
        }

        if (!!goto_location) {
            document.location = goto_location.attr('href');
            return false; // don't execute the default action (scrolling or whatever)
        }
    });
}

function setup_ajax() {
    $.ajaxSetup({
        crossDomain: false,
        beforeSend: function(xhr, settings) {
            if (!csrfSafeMethod(settings.type)) {
                xhr.setRequestHeader("X-CSRFToken",
                    $("input[name='csrfmiddlewaretoken']").val());
            }
        }
    });
}

// ————————————————————————————————————————————————————————————— initialization
//                        (you have to cal this function in app-specific pages)

function common_init() {

    setup_everything();

    try {
        // if we are in body#home, try to run home_init(), and so on.
        // Don't use eval. Thanks
        // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/eval

        var func_name = $('body').attr('id') + '_init';

        window[func_name]();

    } catch(err) {
        console.debug('Exception while trying to run '
                      + func_name + '(): ' + err);
    }

    //setup_table_sorter();

    setup_auto_cleaner();

    setup_keyboard();

    setup_ajax();
}
