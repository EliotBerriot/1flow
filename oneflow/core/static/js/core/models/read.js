

App.Author  = DS.Model.extend({
    name: DS.attr('string')
});

App.Article = DS.Model.extend({
    title: DS.attr('string'),
    authors: DS.hasMany('App.Author'),
    date_published: DS.attr('date'),
    public_url: DS.attr('string'),
    content: DS.attr('string'),
    content_type: DS.attr('string'),
    tags: DS.attr('string')
    //feeds: DS.hasMany('App.Feed'),
    //reads: DS.hasMany('App.Read')
});

App.Read = DS.Model.extend({
    article: DS.belongsTo('App.Article'),
    user: DS.belongsTo('App.User'),
    date_auto_read: DS.attr('date'),
    date_created: DS.attr('date'),
    date_read: DS.attr('date'),
    is_auto_read: DS.attr('boolean'),
    is_read: DS.attr('boolean'),
    rating: DS.attr('string'),
    resource_uri: DS.attr('string'),
    tags: DS.attr('string')
});
