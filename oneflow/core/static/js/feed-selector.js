
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

// Support for AJAX loaded modal window.
// Focuses on first input textbox after it loads the window.
$('[data-toggle="modal"]').click(function(e) {

    e.preventDefault();

    var url = $(this).attr('href');

    if (url.indexOf('#') == 0) {
        $(url).modal('open');

    } else {

        $.get(url, function(data) {
            $(data).modal().on("shown", function () {

                //$('input:visible:enabled:first').focus();
                //$first_input.select();

                var $first_input = $('input:visible:enabled').first();

                $first_input.focus(function() {
                    // OMG. Thanks http://stackoverflow.com/a/10576409/654755
                    this.selectionStart = this.selectionEnd = this.value.length;
                });

                $first_input.focus();

            }).on('hidden', function () {
                $(this).remove();
            });
        });
    }
});
