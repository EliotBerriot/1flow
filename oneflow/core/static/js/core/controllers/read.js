'use strict';

App.ReadController = Ember.ArrayController.extend({


  mark_read: function(read) {
    read.set('is_read',  true);
    read.get('store').commit();
  },

  mark_unread: function(read) {

    read.set('is_read',  false);
    read.get('store').commit();
  },

});
