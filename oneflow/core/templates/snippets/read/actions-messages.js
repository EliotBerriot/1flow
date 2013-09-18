{% comment %}
    No need for a "var", this variable is already declared in read-one.js
    The current included file is hack to avoid the full Django Javascript
    i18n workflow. This will change incrementally in the future.
{% endcomment %}

read_actions_messages = {
    open_first: "{% trans 'Opening first item…' %}",
    already_top_first: "{% trans 'No Previous, captain. You are at the top!' %}",
    already_top_more: "{% trans 'Already at the top!' %}",

    is_read: {
        done: "{% trans 'Marked read.' %}",
        undone: "{% trans 'Marked unread.' %}"
    },
    is_starred: {
        done: "{% trans 'Marked starred.' %}",
        undone: "{% trans 'Marked unstarred.' %}"
    },
    is_bookmarked: {
        done: "{% trans 'Added to your reading list.' %}",
        undone: "{% trans 'Removed from your reading list.' %}"
    }
}
