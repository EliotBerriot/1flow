
'use strict';

common_init();


function read_setup() {
    // this function is run after each ajax call, via setup_everything().



}

// for now, this one does nothing.
// It's not mandatory to create it,
// but I keep it here as an example.
function read_init(){};


// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.
