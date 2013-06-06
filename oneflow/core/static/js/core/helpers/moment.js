
Ember.Handlebars.registerBoundHelper('fromNow', function(date){
    //console.log(date + " " + moment(date, "YYYYMMDD").fromNow());
    return moment(date, "YYYYMMDD").fromNow();
});
