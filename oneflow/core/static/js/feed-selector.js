
'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.

// TODO: put this in our own namespace, not in the window…

common_init();


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
                $('input:visible:enabled:first').focus();
                //$(this).val($(this).val());

                //$first_input = $('input:visible:enabled').first();
                // $first_input = $('input:visible:enabled:first');
                // $first_input.select();
                // console.debug($first_input);
                // $first_input.focus();
                // tmpStr = $first_input.val();
                // $first_input.val('');
                // $first_input.val(tmpStr);

            }).on('hidden', function () {
                $(this).remove();
            });
        });
    }
});
