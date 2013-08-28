
App.ApplicationController = Ember.Controller.extend({
  closeNotification: function() {
    this.set('notification', null);
  },

  notify: function(notification) {
    this.set('notification', notification);
  }
});
