
// App.ReadRoute = Ember.Route.extend({
//   model: function() {
//     reads = App.Read.find();
//     //console.log(reads);
//     return reads;
//   }
// });

App.ReadsRoute = Ember.Route.extend({
  model: function() {
    return App.Read.find();
  },

  events: {
    more: function() {
      // NOTE: in the default configuration where the server API sends
      // results paginated, this will automatically load next page.
      return App.Read.find();
    }
  }
});
