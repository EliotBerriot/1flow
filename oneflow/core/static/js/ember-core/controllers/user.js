'use strict';

App.ProfileController = Ember.ArrayController.extend({

  save: function(profile) {
    profile.set('is_read',  true);
    profile.get('store').commit();

    var notification = "Profile saved successfully.";
    this.controllerFor('application').notify(notification);
  },

});
