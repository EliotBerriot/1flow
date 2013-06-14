
App.SubscriptionsRoute = Ember.Route.extend({
  model: function() {
    return App.subscription.find();
  }
});
