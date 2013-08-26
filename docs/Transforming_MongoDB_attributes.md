
# Example on `Article.feed` -> `Article.feeds`

## In `nonrel.py`

### Before

    class Article(…):
        feed = ReferenceField(…)
        feeds = ListField(ReferenceField(…))

## Then the script

    from mongoengine.queryset import Q
    from oneflow.core.models import *
    from oneflow.base.utils.dateutils import *

    articles = Article.objects(Q(feeds__exists=False) | Q(feeds__size=0))

    changed = unchanged = crashed = 0

    with benchmark():
        for article in articles.no_cache():
            if article.feed:
                try:
                    article.update(add_to_set__feeds=article.feed)
                except:
                    crashed += 1
                else:
                    article.update(set__feed=None)
                    changed += 1
            else:
                unchanged += 1
    print ">> %s processed, %s changed, %s unchanged, %s crashed" % (changed + unchanged + crashed, changed, unchanged, crashed)

    # development:
    # Generic benchmark started 2013-08-26 12:36, ran in 47 seconds.
    # >> 22837 processed, 21315 changed, 1522 unchanged, 0 crashed

    # production:
    # Generic benchmark started 2013-08-26 13:40, ran in an hour.
    # >> 2145334 processed, 2145086 changed, 248 unchanged, 0 crashed

## Then get the latest missing

    articles = Article.objects(Q(feeds__exists=False) | Q(feeds__size=0))
    articles.count()

    gr = fp = gr2 = fp2 = nothing = 0

    for article in articles:
        if article.original_data.feedparser:
            fp += 1
        elif article.feedparser_original_data:
            fp2 +=  1
        elif article.original_data.google_reader:
            gr += 1
        elif article.google_reader_original_data:
            gr2 += 1
        else:
            nothing += 1

    print '>> GR %s / %s, FP %s / %s, nothing %s' % (gr, gr2, fp, fp2, nothing)

    # >> GR 2 / 0, FP 0 / 0, nothing 246

    # (then I migrate the last google-reader-original-data; cf. Migration_OriginalData.md)


### After

    class Article(…):

        …

        @property
        def feed(…):
            …
            return self.feeds[0]
            …

- deploy code, etc.

## Cleaning the underlying database

    db.article.update({ "feed": { $exists: true }}, { $unset: { "feed": 1 }}, false, true);
    db.article.find({ "feed": { $exists: true }}).count(true);
