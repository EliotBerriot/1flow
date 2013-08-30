

// notification thanks to Yehuda Katz http://stackoverflow.com/a/14301065/654755
App.NotificationView = Ember.View.extend({
  notificationDidChange: function() {
    if (this.get('notification') !== null) {
      this.$().slideDown();
    }
  }.observes('notification'),

  close: function() {
    this.$().slideUp().then(function() {
      self.set('notification', null);
    });
  },

  template: Ember.Handlebars.compile(
    "<button {{action 'close' target='view'}}>&times;</button>" +
    "{{view.notification}}"
  )
});

App.ApplicationView = Ember.View.extend({
    classNames: ['application']
});

App.IndexView = Ember.View.extend();
App.HelpView = Ember.View.extend();
