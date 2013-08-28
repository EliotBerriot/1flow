
// Server side, this is the Django User Model

App.User = DS.Model.extend({
  username: DS.attr('string'),
  first_name: DS.attr('string'),
  last_name: DS.attr('string'),
  email: DS.attr('string'),
  email_announcements: DS.attr('string'),

  date_joined: DS.attr('string'),
  last_login: DS.attr('string'),
  last_modified: DS.attr('string'),
  password: DS.attr('string'),

  is_active: DS.attr('string'),
  is_staff: DS.attr('string'),
  is_superuser: DS.attr('string')

  //hash_codes: DS.attr('string'),
  //data: DS.attr('string'),
  //register_data: DS.attr('string'),
  //resource_uri: DS.attr('string'),
  //sent_emails: DS.attr('string'),
});
