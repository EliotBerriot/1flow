
App.SubcriptionController = Ember.ObjectController.extend({
  // initial value
  isExpanded: false,

  expand: function() {
    this.set('isExpanded', true);
  },

  collapse: function() {
    this.set('isExpanded', false);
    //this.get('store').commit();
  }
});
