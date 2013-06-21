
App.User = DS.Model.extend({
    username: DS.attr('string'),
    first_name: DS.attr('string'),
    last_name: DS.attr('string'),

    // not modifiable
    email: DS.attr('string'),

    old_password: DS.attr('string'),
    password1: DS.attr('string'),
    password2: DS.attr('string'),

    // just for display:
    date_joined: DS.attr('date'),
    last_login: DS.attr('date'),

    profile: DS.belongsTo('App.UserProfile')
});

App.UserProfile = DS.Model.extend({
    user: DS.belongsTo('App.User'),

    email_announcements: DS.attr('boolean')

});

//App.UserController = Ember.Controller.extend({});
//App.UserProfileController = Ember.Controller.extend({});


// App.Adapter.map('App.UserProfile', {
//   user: {embedded: 'always'}
// });
// App.Adapter.map('App.User', {
//   profile: {embedded: 'always'}
// });
