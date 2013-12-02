
//'use strict';

var read_actions_messages = {};

function mark_something(article_id, mark_what, mark_inverse, send_notify, message, callback) {

    var run_callback = function() {
        //console.debug('trying to run callback ' + callback + '(' + oid + ')');
        typeof callback === 'function' && callback(article_id, mark_what, mark_inverse, send_notify, message);
    };

    var $article = $("#" + article_id);

    // console.debug('mark_something(' + article_id + ', ' + mark_what + ', ' + mark_inverse + ');');

    //
    // CSS classes are defined in a template-tag.
    //

    if(typeof message == 'undefined') {
        var message = null;
    }

    if(typeof mark_inverse == 'undefined') {
        var mark_inverse = false;
    }

    if (mark_inverse) {
        var klass    = 'not_' + mark_what;
        var inverse  = mark_what;
        var notifmsg = message || read_actions_messages[mark_what]['undone']

    } else {
        var klass   = mark_what;
        var inverse = 'not_' + mark_what;
        var notifmsg = message || read_actions_messages[mark_what]['done']
    }

    if(typeof send_notify == 'undefined') {
        var send_notify = false;
    }

    //
    // HEADS UP: the *row* uses article.id to ease its caching.
    //           But the `url-action-toggle` is *really* the URL
    //           of the User's **Read**.
    //
    $.get($article.data('url-action-toggle').replace('@@KEY@@', mark_what),
        function(){
            //console.debug($article.find(".action-mark-" + klass));
            //console.debug($article.find(".action-mark-" + inverse));

            // This is done automatically via CSS now.
            // $article.find(".action-mark-" + klass).fadeOut('fast', function(){
            //     $article.find(".action-mark-" + inverse).fadeIn('fast');
            // });

            $article.removeClass(inverse).addClass(klass);

            // in case the sidebars are not yet loaded while toggle_read()
            // occurs, we need to delay this a little. This problem happens
            // only when the user sets "mark read immediately" in his
            // preferences, this is a corner case.
            setTimeout(function() {
                $("#meta-" + article_id).removeClass(inverse).addClass(klass);
            }, 250);

            if (send_notify) {
                notify({
                    text: notifmsg,
                    type: 'success',
                    icon: false,
                    sticker: false,
                    nonblock: true,
                    nonblock_opacity: .2
                });
            }

            run_callback();
        }
    );

    // avoid any click event to propagate?
    return false;
}

function post_mark_triggers(article_id, attr_name, send_notify) {

    var $article = $("#" + article_id);

    if (attr_name == 'is_bookmarked') {

        if (preferences.bookmarked_marks_unread) {

            //console.debug('item ' + article_id + ' bookmarked.');
            //console.debug($article.hasClass('is_bookmarked'));
            //console.debug($article.hasClass('is_read'));

            if($article.hasClass('is_bookmarked')
                    && $article.hasClass('is_read')) {

                // 'true' means mark 'inverse' of is_read.
                mark_something(article_id, 'is_read', true, send_notify);

                // console.log('item ' + article_id + ' bookmarked; marked as unread too.');
            }
        }

    } else if (attr_name == 'is_starred') {

        // console.debug('item ' + article_id + ' starred.');

        if (preferences.starred_marks_read) {

            if($article.hasClass('is_starred')
                    && $article.hasClass('not_is_read')) {

                mark_something(article_id, 'is_read', false, send_notify);

                // console.log('item ' + article_id + ' starred; marked as read too.');
            }
        }

        if (preferences.starred_removes_bookmarked) {

            if($article.hasClass('is_starred')
                    && $article.hasClass('is_bookmarked')) {

                mark_something(article_id, 'is_bookmarked', true, send_notify);

                // console.log('item ' + article_id + ' starred; unbookmarked too.');
            }
        }
    }
}

function toggle_status(article_id, attr_name, send_notify) {

    var $article = $("#" + article_id);

    mark_something(article_id, attr_name,
                   !!$article.hasClass(attr_name),
                   send_notify, null,
                   function() {
                        post_mark_triggers(article_id, attr_name, send_notify);
                   }
                );

    // if (ev) {
    //     ev.stopPropagation();
    // }
    return false;
}

function momentFromNow() {
    //return moment(string_date, "YYYYMMDD").fromNow();
    // Django's ISO produces: 2013-11-29T18:33:40+01:00
    // This is "YYYY-MM-DDTHH:mm:ssZZ" but Moment parses
    // ISO dates corectly without specifying them.

    $(this).html(moment($(this).html()).fromNow(true));
}
