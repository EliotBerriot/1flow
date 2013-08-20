
App.ReadRoute = Ember.Route.extend({
  model: function() {
    reads = App.Read.find();
    //console.log(reads);
    return reads;
  }
});
