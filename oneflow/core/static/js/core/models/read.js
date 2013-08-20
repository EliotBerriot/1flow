
App.Read = DS.Model.extend({
    article: DS.belongsTo('App.Article'),
    user: DS.belongsTo('App.User'),
    date_auto_read: DS.attr('string'),
    date_created: DS.attr('string'),
    date_read: DS.attr('string'),
    is_auto_read: DS.attr('boolean'),
    is_read: DS.attr('boolean'),
    rating: DS.attr('string'),
    resource_uri: DS.attr('string'),
    tags: DS.attr('string')
});
