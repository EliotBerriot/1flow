function preference_data(objekt, data_name, value) {

    val = objekt.data(data_name);

    if (typeof val === 'undefined'){
        val = value;
    }

    return val;
}
function preference_from_checkbox_group(event) {

    objekt = $(event.delegateTarget);
    parent = objekt.parent();

    pref_convert    = preference_data(parent, 'preference-convert', 'False');
    pref_reload     = parseBool(preference_data(parent, 'preference-reload', 'true'));
    pref_reload_url = preference_data(parent, 'preference-reload-url', null);

    active_children = parent.children('.btn.active');

    if (active_children.length == 0) {
        // no button is active, make all of them be.

        active_children = parent.children('.btn');
    }

    active_children.each(function(index, child) {

        vals = String($(child).data('preference-value')).split('-');

        if (index == 0) {
            // we take the outer minimum value
            pref_value = vals[0] + '-';
        }

        if (index == active_children.length - 1){
            // and the outer maximum value
            pref_value += '-' + vals[1];
        }
    });

    pref_value = pref_value.replace("--", "-");

    $.get('/preferences/'
            + parent.data('preference') + '/'
            + pref_value + '/'
            + pref_convert, function(data) {
                if (pref_reload) {
                    if (pref_reload_url){
                        document.location = pref_reload_url;

                    } else {
                        location.reload();
                    }
                }
    });
}
function preference_from_radio_group(event){

    objekt = $(event.delegateTarget);
    parent = objekt.parent();

    pref_url        = preference_data(objekt, 'preference-url', null);
    pref_value      = preference_data(objekt, 'preference', null);
    pref_convert    = preference_data(parent, 'preference-convert', 'False');
    pref_reload     = parseBool(preference_data(parent, 'preference-reload', 'true'));
    pref_reload_url = preference_data(parent, 'preference-reload-url', null);

    //assert(pref_url, objekt + " HAS NO preference URL!");

    $.get(pref_url,
        function(data) {
            if (pref_reload) {
                if (pref_reload_url){
                    document.location = pref_reload_url;

                } else {
                    location.reload();
                }
            }
        }
    );
}
function preference_toggle(event) {

    objekt = $(event.delegateTarget);

    pref_value      = preference_data(objekt, 'preference', null);
    pref_url        = preference_data(objekt, 'preference-url', null);
    pref_reload     = parseBool(preference_data(objekt, 'preference-reload', 'true'));
    pref_reload_url = preference_data(objekt, 'preference-reload-url', null);

    //assert(pref_url, objekt + " HAS NO preference URL!");

    $.get(pref_url,
        function(data) {
            if (pref_reload) {
                if (pref_reload_url){
                    document.location = pref_reload_url;

                } else {
                    location.reload();
                }
            }
        }
    );
}
function setup_preferences_actions(parent) {

    function setup_preference(index, objekt) {

        objekt = $(objekt);
        //console.log(objekt);

        if (objekt.data('toggle') == 'button') {
            // This is a bootstrap "single toggle" button, go straight!

            objekt.click(preference_toggle);

        } else if (objekt.parent().data('toggle') == 'buttons-checkbox') {
            // in a bootstrap "checkbox group", we work from the parent to
            // gather info of all checked children. WARNING: we assume
            // preference values are ordered from min. to max. in the DOM.

            // Why a setTimeout? We have to wait until bootstrap
            // has updated the 'active' CSS classes of the group.
            // http://stackoverflow.com/a/5685292
            objekt.click(function(event) {
                setTimeout(function() {
                    preference_from_checkbox_group(event);
                }, 500);
            });

        } else  if (objekt.parent().data('toggle') == 'buttons-radio'){
            // idem, the main informations are in the parent and children
            // buttons just toggle a different value of the same preference.

            objekt.click(preference_from_radio_group);
        }
    }

    find_start(parent, 'preference').each(setup_preference);

    //console.debug('setup_preferences_actions() finished.');
}
