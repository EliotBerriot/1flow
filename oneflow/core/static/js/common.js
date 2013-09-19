// warning: don't "use strict"; here, it will break things.
// I need to learn to write good JS first. Sorry for that.

var page_cleaner_interval;
var scroll_speed = 500;
var debug_touch = false;
$.pnotify.defaults.delay = 5000;

// bindable_hovered NOT USED YET
//var bindable_hovered = null;

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
        start = parent.find('.' + klass);
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
    parent.find('[rel="popover"]').popover({
            placement: popover_placement }).click(function(e) {
        $(this).popover('toggle');
    });

    // Bootstrap 2.3+
    parent.find('[data-toggle=popover]').popover();
}
function show_hover_muted() {

    $(this).find('.hover-muted').each(function(){
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
}
function hide_hover_muted() {
    $(this).find('.hover-muted')
        .stop(true, true).animate({
            opacity: 0
        }, 250, function(){
            if($(this).hasClass('hide')){
               $(this).hide();
            }
        });
}
function setup_hover_muters(parent){

    find_start(parent, 'hover-unmute-children')
        .hover(show_hover_muted, hide_hover_muted);
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

    // We need the "click" for touch interfaces to be able to close
    // twitter popovers. Not needed for clickovers, though, which
    // work perfectly.
    // https://github.com/twitter/bootstrap/issues/3417
    parent.find('.popover-tooltip')
        .tooltip({
            placement: popover_placement,
            // Since Bootstrap 2.2 http://stackoverflow.com/q/14025438/654755
            container: 'body'
        }).click(function(e) {
            $(this).tooltip('toggle');
        });
}
function setup_clickovers(parent) {

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    parent.find('[rel="clickover"]').each(function(){

        params = {};

        if ($(this).hasClass('clickover-large')) {
            $.extend(params, { width: 400 });
        }

        if ($(this).hasClass('iframed')) {
            $.extend(params, { width: 800, height: 450 });
        }

        if ($(this).hasClass('clickover-auto-close')) {
            $.extend(params, { auto_close: 5000 });
        }

        // WARNING: don't use "data-clickover", it will conflict
        // with rel="clickover" and the clickover will not work.

        data_ = $(this).data('clickover-params');

        if (typeof data_ != 'undefined') {
            $.extend(params, eval(data_));
        }

        $.extend(params, { placement: popover_placement });

        $(this).clickover(params);
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
function setup_everything(parent) {

    if (!Modernizr.touch){
        setup_tooltips(parent);
        setup_hover_muters(parent);
    }
    setup_popovers(parent);

    // bindable_hovered NOT USED YET
    //setup_hover_notifiers(parent);

    setup_clickovers(parent);
    setup_delayed_loaders(parent);
    launch_faders(parent);

    try {
        // if we are in body#home, try to run home_setup(), and so on.
        // Don't use eval. Thanks
        // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/eval

        var func_name = $('body').attr('id') + '_setup';

        window[func_name](parent);

    } catch(err) {
        console.debug('Exception while trying to run '
                      + func_name + '(): ' + err);
    }
}
function setup_auto_cleaner() {
    // every 10 minutes, the page is cleaned from old and orphaned elements.

    page_cleaner_interval = setInterval(page_cleaner, 600000);
}
function setup_keyboard() {

    $(document).keydown(function(ev) {

        var goto_location = null;

        if(ev.which == 37) {
            goto_location = $('a#previous');
        }

        if(ev.which == 39) {
            goto_location = $('a#next');
        }

        if (!!goto_location) {
            document.location = goto_location.attr('href');
            return false; // don't execute the default action (scrolling or whatever)
        }
    });
}
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

}
