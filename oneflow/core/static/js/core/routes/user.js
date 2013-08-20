
App.ProfileRoute = Ember.Route.extend({
  model: function() {
    test = App.User.find(window.DJANGO_JS_CONTEXT.user.id);
    //console.log(test.get('username'));
    return test;
  }
});
