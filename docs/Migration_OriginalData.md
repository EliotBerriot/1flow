
# Rationale

Move `orni.oneflow.article.{google_reader,feedparser}_original_data` to `harvest.oneflow_archive.original_data.{google_reader,feedparser}`.


# Expected gains

Database size reduction by a factor of 2, perhaps a little more. Database size expansion should slow down a lot, with the current code which creates `*_original_data` directly in the archive database, located on `harvest.licorn.org`.

## Side-effects gains

Seems like the global size of the collection (or the size of each document) directly affects MongoDB on `count()` or `filter()`:

    synchronize_statsd_articles_gauges(True)
    synchronize statsd gauges for Article.* started 2013-08-13 13:11, ran in 14 seconds.
    synchronize statsd gauges for Article.* started 2013-08-14 09:50, ran in 9 seconds.

OMG. This one lasted for 25 minutes before the shrink, and 45 minutes even before (without indexes).


# Code

Needs 1flow v0.20.11

## Python

    feedp = Article.objects(feedparser_original_data__exists=True).no_cache()

    with benchmark('Moving %s feedparser data' % feedp.count()):
        for article in feedp:
            article.add_original_data('feedparser', article.feedparser_original_data)
            del article.feedparser_original_data
            try:
                article.save()
            except:
                pass

    grp = Article.objects(google_reader_original_data__exists=True).no_cache()

    with benchmark('Moving %s Google Reader data' % grp.count()):
        for article in grp:
            article.add_original_data('google_reader', unicode(article.google_reader_original_data))
            del article.google_reader_original_data
            try:
                article.save()
            except:
                pass

## MongoDB

    time mongo oneflow --quiet --eval \
        'printjson(db.runCommand({compact: "article", paddingFactor: 1.25}));'

    # on Orni (production):
    real    9m57.929s
    user    0m0.024s
    sys     0m0.012s

NOTE: this command is *mandatory* for the gain to take effect.


# Size reduction

## Development machine: `chani`

`article` collection:
    - 35900 articles
    - runtime: negligible (~10min for all operations)
    - before run:
        - avg object size: 22529
        - storage size: 5885845504
    - after run:
        - avg object size: 5459 (-75%)
        - storage size: 270311424 (-95%)

## Production machine: orni

`article` collection:
    - 2592k articles
        - 541301 feedparser (1 hour)
        - 2051267 google_reader (3 hours)
    - before run:
        - avg obj size: 18579
        - storage size: 59624951424
        - padding factor: 1.996
    - after run:
        - avg obj size: 6106 (-67%)
        - storage size: 16731656112 (-71%)
        - size: 15888348000
        - padding factor: 1.99
        - failed to migrate:
            - GR: 554
            - FP: 0

# Disk Space reclaim

Needs a repair (currently impossible because of too-low disk space to hold 2 copies of the database) or a dump/restore. `db.repairDatabase()` is a one-liner and doesn't need anything to be stopped (though it is still better to avoid system overload during the repair).

    fab prod maint
    fab prod workers stop
        [… wait a little for all jobs to terminate …]

    # To be sure randomized tasks and retried jobs are purged.
    ssh w01
        cd www/src
        ./manage.py celery purge

    mongodump --db oneflow --out /home/backup/mongodb/
        connected to: 127.0.0.1
        Tue Aug 13 08:10:46.814 DATABASE: oneflow        to     /home/backup/mongodb/oneflow
        Tue Aug 13 08:10:46.816         oneflow.system.indexes to /home/backup/mongodb/oneflow/system.indexes.bson
        Tue Aug 13 08:10:46.816                  16 objects
        Tue Aug 13 08:10:46.816         oneflow.user to /home/backup/mongodb/oneflow/user.bson
        Tue Aug 13 08:10:46.817                  28 objects
        Tue Aug 13 08:10:46.817         Metadata for oneflow.user to /home/backup/mongodb/oneflow/user.metadata.json
        Tue Aug 13 08:10:46.817         oneflow.subscription to /home/backup/mongodb/oneflow/subscription.bson
        Tue Aug 13 08:10:46.825                  4416 objects
        Tue Aug 13 08:10:46.825         Metadata for oneflow.subscription to /home/backup/mongodb/oneflow/subscription.metadata.json
        Tue Aug 13 08:10:46.825         oneflow.feed to /home/backup/mongodb/oneflow/feed.bson
        Tue Aug 13 08:10:46.841                  4154 objects
        Tue Aug 13 08:10:46.841         Metadata for oneflow.feed to /home/backup/mongodb/oneflow/feed.metadata.json
        Tue Aug 13 08:10:46.841         oneflow.article to /home/backup/mongodb/oneflow/article.bson
        Tue Aug 13 08:10:49.007                 Collection File Writing Progress: 92700/2602654 3%      (objects)
        Tue Aug 13 08:10:52.024                 Collection File Writing Progress: 233800/2602654        8%      (objects)
        Tue Aug 13 08:10:55.163                 Collection File Writing Progress: 305200/2602654        11%     (objects)
        Tue Aug 13 08:10:58.008                 Collection File Writing Progress: 459100/2602654        17%     (objects)
        Tue Aug 13 08:11:01.019                 Collection File Writing Progress: 550400/2602654        21%     (objects)
        Tue Aug 13 08:11:04.009                 Collection File Writing Progress: 641700/2602654        24%     (objects)
        Tue Aug 13 08:11:07.016                 Collection File Writing Progress: 721500/2602654        27%     (objects)
        Tue Aug 13 08:11:10.009                 Collection File Writing Progress: 808600/2602654        31%     (objects)
        Tue Aug 13 08:11:13.189                 Collection File Writing Progress: 906400/2602654        34%     (objects)
        Tue Aug 13 08:11:20.478                 Collection File Writing Progress: 970600/2602654        37%     (objects)
        Tue Aug 13 08:11:27.116                 Collection File Writing Progress: 1072600/2602654       41%     (objects)
        Tue Aug 13 08:11:30.026                 Collection File Writing Progress: 1113600/2602654       42%     (objects)
        Tue Aug 13 08:11:33.032                 Collection File Writing Progress: 1159500/2602654       44%     (objects)
        Tue Aug 13 08:11:36.066                 Collection File Writing Progress: 1204900/2602654       46%     (objects)
        Tue Aug 13 08:11:39.025                 Collection File Writing Progress: 1265100/2602654       48%     (objects)
        Tue Aug 13 08:11:42.033                 Collection File Writing Progress: 1349500/2602654       51%     (objects)
        Tue Aug 13 08:11:46.461                 Collection File Writing Progress: 1386400/2602654       53%     (objects)
        Tue Aug 13 08:11:49.009                 Collection File Writing Progress: 1421800/2602654       54%     (objects)
        Tue Aug 13 08:11:52.016                 Collection File Writing Progress: 1526500/2602654       58%     (objects)
        Tue Aug 13 08:11:56.544                 Collection File Writing Progress: 1539300/2602654       59%     (objects)
        Tue Aug 13 08:11:59.029                 Collection File Writing Progress: 1589300/2602654       61%     (objects)
        Tue Aug 13 08:12:02.018                 Collection File Writing Progress: 1680000/2602654       64%     (objects)
        Tue Aug 13 08:12:05.036                 Collection File Writing Progress: 1755200/2602654       67%     (objects)
        Tue Aug 13 08:12:08.044                 Collection File Writing Progress: 1856500/2602654       71%     (objects)
        Tue Aug 13 08:12:11.013                 Collection File Writing Progress: 1943500/2602654       74%     (objects)
        Tue Aug 13 08:12:14.010                 Collection File Writing Progress: 2030700/2602654       78%     (objects)
        Tue Aug 13 08:12:17.015                 Collection File Writing Progress: 2111100/2602654       81%     (objects)
        Tue Aug 13 08:12:20.049                 Collection File Writing Progress: 2168400/2602654       83%     (objects)
        Tue Aug 13 08:12:23.006                 Collection File Writing Progress: 2239500/2602654       86%     (objects)
        Tue Aug 13 08:12:26.013                 Collection File Writing Progress: 2316800/2602654       89%     (objects)
        Tue Aug 13 08:12:29.020                 Collection File Writing Progress: 2397900/2602654       92%     (objects)
        Tue Aug 13 08:12:32.205                 Collection File Writing Progress: 2461500/2602654       94%     (objects)
        Tue Aug 13 08:12:35.032                 Collection File Writing Progress: 2539600/2602654       97%     (objects)
        Tue Aug 13 08:12:37.085                  2602692 objects
        Tue Aug 13 08:12:37.085         Metadata for oneflow.article to /home/backup/mongodb/oneflow/article.metadata.json
        Tue Aug 13 08:12:37.085         oneflow.read to /home/backup/mongodb/oneflow/read.bson
        Tue Aug 13 08:12:40.003                 Collection File Writing Progress: 1971700/3144586       62%     (objects)
        Tue Aug 13 08:12:42.102                  3144586 objects
        Tue Aug 13 08:12:42.102         Metadata for oneflow.read to /home/backup/mongodb/oneflow/read.metadata.json
        Tue Aug 13 08:12:48.992         oneflow.tag to /home/backup/mongodb/oneflow/tag.bson
        Tue Aug 13 08:12:49.272                  136740 objects
        Tue Aug 13 08:12:49.272         Metadata for oneflow.tag to /home/backup/mongodb/oneflow/tag.metadata.json

    du -hs /home/backup/mongodb/
        12G     /home/backup/mongodb

    mongo oneflow
        db.dropDatabase()
        exit()

    mongorestore /home/backup/mongodb/oneflow/
        [… took 5 to 10 minutes …]

    fab prod workers start
    fab prod op

# Second run, the in-error articles

    agr = Article.objects(google_reader_original_data__ne=None)
    agr.count()

    # 554

    failed_add = []
    failed_del = []

    with benchmark('Moving %s Google Reader data' % agr.count()):
        for article in agr:
            try:
                article.add_original_data('google_reader', unicode(article.google_reader_original_data))
            except:
                failed_add.append(article)
                LOGGER.exception("%s AOD failed", article)
            else:
                try:
                    article.update(set__google_reader_original_data=None)
                except:
                    failed_del.append(article)
                    LOGGER.exception('%s GRD failed')

    # Moving 554 Google Reader data started 2013-08-26 17:14, ran in 4 seconds.

    agr = Article.objects(google_reader_original_data__ne=None)
    agr.count()

    # 0

# Clean the database

    db.article.update({ "feedparser_original_data": { $exists: true }},
                      { $unset: { "feedparser_original_data": 1 }}, false, true);
    db.article.find({ "feedparser_original_data": { $exists: true }}).count(true);

    db.article.update({ "google_reader_original_data": { $exists: true }},
                      { $unset: { "google_reader_original_data": 1 }}, false, true);
    db.article.find({ "google_reader_original_data": { $exists: true }}).count(true);

    db.repairDatabase()

And global database size shrank from 20680309816 to 15421747988 (-25%) :-D
