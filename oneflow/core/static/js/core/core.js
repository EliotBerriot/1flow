
// NOTE: Django-pipeline will automatically "closurize" this file.

App = Ember.Application.create({
    //LOG_TRANSITIONS: true,
    //LOG_BINDINGS: true //,
    //LOG_STACKSTRACE_ON_DEPRECIATION:true
});

App.Store = DS.Store.extend({
  // adapter: 'DS.FixtureAdapter'
  adapter: DS.DjangoTastypieAdapter.extend({
      // NO NEED: serverDomain: "http://dev1.1flow.io",
      // serverDomain: "http://dev2.1flow.io:8000",
      // namespace: (url_root + '/api/v1').replace(/^\//g, ''),
      namespace: 'api/v1'
    })
});

App.Router.map(function(){
    this.resource('read');

    this.resource('teams');
    this.resource('discovery');
    this.resource('subscriptions', function() {
        this.route('edit', { path: ':subscription_id' });
    });
    this.resource('help');
    this.resource('profile');
});





// App.ShowSpinnerWhileRendering = Ember.Mixin.create({
//   layout: Ember.Handlebars.compile('<div class="loading">loading --{{ yield }}--</div>'),

//   classNameBindings: ['isLoaded'],

//   isLoaded: function() {
//     return this.get('isInserted') && this.get('controller.isLoaded');
//   }.property('isInserted', 'controller.isLoaded'),

//   didInsertElement: function() {
//     this.set('inserted', true);
//     this._super();
//   }
// });
