
App.Article = DS.Model.extend({
    title: DS.attr('string'),
    authors: DS.hasMany('App.Author'),
    date_published: DS.attr('string'),
    public_url: DS.attr('string'),
    content: DS.attr('string'),
    content_type: DS.attr('string'),
    tags: DS.attr('string')
    //feeds: DS.hasMany('App.Feed'),
    //reads: DS.hasMany('App.Read')
});
