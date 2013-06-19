
Ember.Handlebars.registerBoundHelper('momentFromNow', function(string_date){
    //console.log(string_date + " " + moment(string_date, "YYYYMMDD").fromNow());
    return moment(string_date, "YYYYMMDD").fromNow();
});
