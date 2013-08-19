App.ReadRoute = Ember.Route.extend({
  model: function() {
  return  App.Read.all();
  }
});
