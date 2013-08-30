'use strict';

App.ReadsController = Ember.ArrayController.extend({

  unreadCount: function() {
    return this.filterProperty('is_read', false).get('length');
  }.property('@each.is_read'),

  readCount: function() {
    return this.filterProperty('is_read', false).get('length');
  }.property('@each.is_read'),

  mark_read: function(read) {
    read.set('is_read',  true);
    read.get('store').commit();
  },

  mark_unread: function(read) {
    read.set('is_read',  false);
    read.get('store').commit();
  },

});
