
'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.


function endless_new_page_load_completed(context, fragment) {
    // console.log('Label:', $(this).text());
    //console.log('URL:', context.url);
    //console.log('Querystring key:', context.key);
    // console.log('Fragment:', fragment);

    $('body').find('.endless_container').remove();

    var new_items   = $(fragment);
    var new_endless = new_items.find('.endless_container');

    // NOTE: .after() moved the new_endless.
    // No need to remove it from the fragment.

    reads_container
        .after(new_endless)
        .append(new_items)
        .isotope('appended', new_items);

    setup_everything(new_items);

    // We return false to avoid
    // endless normal processing.
    return false;
}

var reads_container = $('#reads-container');

reads_container.isotope({
  itemSelector: '.read-list-item'
});

$.endlessPaginate({
    paginateOnScroll: true,
    paginateOnScrollMargin: 100,
    onCompleted: endless_new_page_load_completed
});
