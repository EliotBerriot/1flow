
// NOTE: Django-pipeline will automatically "closurize" this file.
// Worth a read:
// http://www.rkblog.rk.edu.pl/w/p/creating-modern-web-applications-django-and-emberjs-javascript-framework/

var api_namespace = Django.url('api_v1_top_level', 'v1').replace(/^\//, '').replace(/\/$/, '');

App = Ember.Application.create({
    //LOG_TRANSITIONS: true,
    //LOG_BINDINGS: true //,
    //LOG_STACKSTRACE_ON_DEPRECIATION:true
});

App.Store = DS.Store.extend({
  // adapter: 'DS.FixtureAdapter'

  adapter: DS.DjangoTastypieAdapter.extend({

      // serverDomain: "http://dev1.1flow.io",
      // serverDomain: "http://dev2.1flow.io:8000",
      serverDomain: Django.context.ABSOLUTE_ROOT,

      // namespace: (url_root + '/api/v1').replace(/^\//g, ''),
      // namespace: 'api/v1'
      namespace: api_namespace
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
