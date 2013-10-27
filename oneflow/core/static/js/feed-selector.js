
'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.

// TODO: put this in our own namespace, not in the window…

common_init();

start_checking_for_needed_updates();

function update_needed() {
    console.log('update needed…')
}

// —————————————————————————————————————————— Keyboard shortcuts & touch events


// “Add Item”, “Import Item”
Mousetrap.bind(['a i', 'i i'], function() {
    $("#import-web-item-trigger").click();
    return false;
});

// “Add Folder”
Mousetrap.bind(['a f'], function() {
    $("#add-folder-trigger").click();
    return false;
});

// Add Subscription
Mousetrap.bind(['a s'], function() {
    $("#add-subscription-trigger").click();

    // Do NOT return false, we need the link to be really
    // clicked in this case because it's not a JS modal box.
    //return false;
});
