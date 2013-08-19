
// NOTE: Django-pipeline will automatically "closurize" this file.

console.log('PENSER A ACTIVER LES NOUVEAUX PARAMETRES !');

App = Ember.Application.create({
    LOG_TRANSITIONS: true //,
    //LOG_BINDINGS: true,
    //LOG_STACKSTRACE_ON_DEPRECIATION:true
});

App.Store = DS.Store.extend({
  //adapter: 'DS.FixtureAdapter'
  adapter: DS.DjangoTastypieAdapter.extend({
      //NO NEED: serverDomain: "http://dev1.1flow.io",
      //serverDomain: "http://dev2.1flow.io:8000",
      namespace: 'api/v1'
      // namespace: (url_root + '/api/v1').replace(/^\//g, ''),

    })
});

App.Router.map(function(){
    this.resource('teams');
    this.resource('discovery');
    this.resource('subscriptions', function() {
        this.route('edit', { path: ':subscription_id' });
    });
    this.resource('help');
    this.resource('profile');
	  this.resource('read');
});

//console.log(DJANGO_JS_CONTEXT['user']['id']);
