// warning: don't "use strict"; here, it will break things.
// I need to learn to write good JS first. Sorry for that.

var page_cleaner_interval;

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
            //console.debug('page_cleaner: ' + err);

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
}
function setup_hover_muters(parent){

    find_start(parent, 'hover-unmute-children')
        .hover(function() {
            $(this).find('.hover-muted').animate({
                opacity: 1
            });
        }, function() {
            $(this).find('.hover-muted').stop(true, true).animate({
                opacity: 0
            });
    });
}
function setup_tooltips(parent){

    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    // We need the "click" for touch interfaces to be able to close
    // twitter popovers. Not needed for clickovers, though, which
    // work perfectly.
    // https://github.com/twitter/bootstrap/issues/3417
    parent.find('[rel="tooltip"]').tooltip({
            placement: popover_placement }).click(function(e) {
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
function launch_faders(parent) {
    if (typeof parent == 'undefined') {
        parent = $('body');
    }

    function flash_fade(objekt){
        curback = objekt.css('backgroundColor');

        objekt.animate({ backgroundColor: "#ffff99" }, 250, function() {
            objekt.delay(2500).animate({ backgroundColor: curback }, 1000);

            // Fade is done, object is not "new" anymore.
            objekt.removeClass('new-fade');
        });
    }

    if (parent.hasClass('new-fade')) {
        flash_fade(parent);
    }

    parent.find('.new-fade').each(flash_fade);
}
function setup_everything(parent) {

    setup_tooltips(parent);
    setup_hover_muters(parent);
    setup_popovers(parent);
    setup_clickovers(parent);
    setup_delayed_loaders(parent);

    try {
        setup_preferences_actions(parent);

    } catch (err) {
        // nothing. the preferences thing exists only
        //when user is authenticated, else it will fail.
    }

    launch_faders(parent);
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

    //setup_table_sorter();
    setup_auto_cleaner();

    setup_keyboard();

}
