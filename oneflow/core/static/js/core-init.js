
// This is the basic JS for all oneflow::core pages.
// If you need to tune it, duplicate it, create a pipeline entry
// in settings/snippets/common.py, and use this file or feed-selector.js
// as a starting point.

'use strict';

// We assume this JS is sourced at the end of any HTML, avoiding the
// need for a $(document).ready(…) call. But it really needs the
// document fully loaded to operated properly.

// TODO: put this in our own namespace, not in the window…

common_init();
