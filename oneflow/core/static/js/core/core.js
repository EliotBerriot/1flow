
// NOTE: Django-pipeline will automatically "closurize" this file.

console.log('PENSER A ACTIVER LES NOUVEAUX PARAMETRES !');

App = Ember.Application.create({
    LOG_TRANSITIONS: true //,
    //LOG_BINDINGS: true,
    //LOG_STACKSTRACE_ON_DEPRECIATION:true
});

App.Store = DS.Store.extend({
  adapter: DS.DjangoTastypieAdapter.extend({
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
})

/*
App.ProfileRoute = Ember.Route.extend({
  enter: function() {

    //App.user_profile = App.UserProfile.find(DJANGO_JS_CONTEXT['user']['id']);
    // NOTE: App.user is reserved…
    //App.current_user = App.user_profile.get('user');

    Ember.set(App, 'myprofile', App.UserProfile.find(DJANGO_JS_CONTEXT['user']['id']));

    Ember.set(App, 'myuser', App.myprofile.get('user'));
    //Ember.set(App, 'current_user', App.User.find(DJANGO_JS_CONTEXT['user']['id']));

    console.log('LOADED.');
    //console.log(App.current_user.get('username'));
  }

  //   //console.log('LOADED PROFILE & USER');
  //   // console.log(user_profile);

  //   Ember.set(App, 'ApplicationController', Ember.Controller.extend({
  //     username:  current_user.username,
  //     date_joined:  current_user.date_joined,
  //     first_name: current_user.first_name,
  //     last_name: current_user.last_name,
  //   }))

  // }
  // events: {
  //   loadProfile: function() {
  //     user_profile = App.UserProfile.find(DJANGO_JS_CONTEXT['user']['id']);
  //     console.log('LOADED PROFILE');
  //     console.log(user_profile);
  //   }
  // }
});

// App.IndexRoute = Ember.Route.extend({
//     redirect: function() {
//         this.transitionTo('subscriptions');
//         this.replaceWith('subscriptions');
//     }
// });
*/
