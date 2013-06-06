
// ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••

(function($, undefined ) {

    App.Subscription = DS.Model.extend({
        name: DS.attr('string'),
        email: DS.attr('string'),
    });

    // App.Router.map(function() {
    //     this.resource('subscriptions', function() {
    //         this.route('add');
    //         this.route('show', { path: '/:subscription_id' });
    //         this.route('edit', { path: '/:subscription_id/edit' });
    //     });
    //     this.route('about');
    // });


    App.SubscriptionsRoute = Ember.Route.extend({
        model: function() {
            return App.Subscription.find();
        },
    });
    App.SubscriptionsController = Ember.ArrayController.extend({
        sortProperties: ['name'],
        sortAscending: true,
    });


    /*
     * Add a new subscription
     */
    App.SubscriptionsAddRoute = Ember.Route.extend({
        model: function() {
            return null;
        },
        setupController: function(controller, model) {
            controller.startEditing();
        },
        deactivate: function() {
            this.controllerFor('subscriptions.add').stopEditing();
        },
    });
    App.SubscriptionsAddController = Ember.ObjectController.extend({
        headerTitle: 'Create',
        buttonTitle: 'Create',
        canDelete: false,
        startEditing: function() {
            this.transaction = this.get('store').transaction();
            this.set('content', this.transaction.createRecord(App.Subscription, {}));
        },
        stopEditing: function() {
            if(this.transaction) {
                this.transaction.rollback();
                this.transaction = undefined;
            }
        },
        save: function() {
            this.transaction.commit();
            this.transaction = undefined;
            this.get('content').on('didCreate', this, function() {
                // TODO: broken in the current Ember release
                // https://github.com/emberjs/data/issues/405
                this.transitionToRoute('subscriptions.show', this.get('content'));
            });
        },
        cancel: function() {
            this.stopEditing();
            this.transitionToRoute('subscriptions.index');
        },
    });

    /*
     * Show an existing Subscription.
     */
    App.SubscriptionsShowRoute = Ember.Route.extend({
        model: function(params) {
            return App.Subscription.find(params.subscription_id);
        },
        setupController: function(controller, model) {
            controller.set('content', model);
        },
    });
    App.SubscriptionsShowController = Ember.ObjectController.extend({
        destroy: function() {
            this.content.deleteRecord();
            this.store.commit();
            this.get('content').on('didDelete', this, function() {
                this.transitionToRoute('subscriptions');
            });
        },
    });

    /*
     * Edit an existing Subscription.
     */
    App.SubscriptionsEditRoute = Ember.Route.extend({
        model: function(params) {
            return App.Subscription.find(params.subscription_id);
        },
        setupController: function(controller, model) {
            controller.set('content', model);
        },
        deactivate: function() {
            this.controllerFor('subscriptions.edit').stopEditing();
        },
    });
    App.SubscriptionsEditController = Ember.ObjectController.extend({
        headerTitle: 'Edit',
        buttonTitle: 'Update',
        canDelete: true,
        save: function() {
            this.store.commit();
            this.get('content').on('didUpdate', this, function() {
                this.transitionToRoute('subscriptions.show', this.get('content'));
            });
            this.get('content').on('becameInvalid', this, function(subscription) {
                // TODO
                // Server-side validation throw some errors, I don't know how
                // to handle them in Emberjs.
            });
        },
        cancel: function() {
            this.stopEditing();
            this.transitionToRoute('subscriptions.show', this.get('content'));
        },
        stopEditing: function() {
            if(this.content.get('isDirty')) {
                this.content.rollback();
            }
        },
        destroy: function() {
            this.content.deleteRecord();
            this.store.commit();
            this.get('content').on('didDelete', this, function() {
                this.transitionToRoute('subscriptions');
            });
        },
    });

    /*
     * Some helpers
     */
    Handlebars.registerHelper('mailto', function(field) {
        var address = this.get(field);
        if (address) {
            return new Handlebars.SafeString('<a href="mailto:' + address + '" />' + address + '</a>');
        }
    });
}(jQuery));
