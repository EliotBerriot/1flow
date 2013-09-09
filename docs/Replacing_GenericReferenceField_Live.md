
# Replacing a GenericReferenceField by a ReferenceField, live

## Explanations

`Article.tags` was a `ListField(GenericReferenceField())`. For efficiency and `reverse_delete_rule` reasons, it's now a `ListField(ReferenceField('Tag'))`. We cannot instanciate articles anymore because of:

    Article.objects.get(id='5207cadab49d881b7ea2fe04')

    ---------------------------------------------------------------------------
    TypeError                                 Traceback (most recent call last)
    <ipython-input-20-4f0212911515> in <module>()
    ----> 1 Article.objects.get(id='5207cadab49d881b7ea2fe04')

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/queryset/base.pyc in get(self, *q_objs, **query)
        180
        181         try:
    --> 182             result = queryset.next()
        183         except StopIteration:
        184             msg = ("%s matching query does not exist."

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/queryset/base.pyc in next(self)
       1129             return self._get_as_pymongo(raw_doc)
       1130         doc = self._document._from_son(raw_doc,
    -> 1131                                        _auto_dereference=self._auto_dereference)
       1132         if self._scalar:
       1133             return self._get_scalar(doc)

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/document.pyc in _from_son(cls, son, _auto_dereference)
        559                 try:
        560                     data[field_name] = (value if value is None
    --> 561                                         else field.to_python(value))
        562                     if field_name != field.db_field:
        563                         del data[field.db_field]

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/fields.pyc in to_python(self, value)
        253         if self.field:
        254             value_dict = dict([(key, self.field.to_python(item))
    --> 255                                for key, item in value.items()])
        256         else:
        257             value_dict = {}

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/fields.pyc in to_python(self, value)
        916            not isinstance(value, (DBRef, Document, EmbeddedDocument))):
        917             collection = self.document_type._get_collection_name()
    --> 918             value = DBRef(collection, self.document_type.id.to_python(value))
        919         return value
        920

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/mongoengine/base/fields.pyc in to_python(self, value)
        391     def to_python(self, value):
        392         if not isinstance(value, ObjectId):
    --> 393             value = ObjectId(value)
        394         return value
        395

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/bson/objectid.pyc in __init__(self, oid)
         88             self.__generate()
         89         else:
    ---> 90             self.__validate(oid)
         91
         92     @classmethod

    /Users/olive/.virtualenvs/1flow/lib/python2.7/site-packages/bson/objectid.pyc in __validate(self, oid)
        196             raise TypeError("id must be an instance of (%s, %s, ObjectId), "
        197                             "not %s" % (binary_type.__name__,
    --> 198                                         text_type.__name__, type(oid)))
        199
        200     @property

    TypeError: id must be an instance of (str, unicode, ObjectId), not <type 'dict'>

## Migrating

### Stopping everything

At the time of this writing, we just need to activate `config.FEED_FETCHING_DISABLED`. In the future, there could be more to do. When reading this again in the future, you should probably think about the twitter fetchers and others.

Stopping all workers and letting the queues grow is another option, but I think it's non-doable as of 20130909: we should have a queue for each of the tasks, and stop the consumers for `articles` related tasks without stopping the other consumers. This is a good idea but would require a lot of re-configuration, and some sparks development.


    # create a temporary class on the same collection that can handle
    # the "old way" and will be used to migrate to a temporary field.
    class ArticlesOldTags(Document):
        tags = ListField(GenericReferenceField())
        new_tags = ListField(ReferenceField('Tag'))
        meta = {
            'collection': 'article'
        }

    # Find all articles with the "old" GenericReferenceField, via JS because
    # we cannot search via standard queries: either the new or the old classes
    # will fail when they encounter the old/new field values.
    aotids = ArticlesOldTags.objects(__raw__={
            "tags": {
                "$elemMatch" : {
                    "_cls": "Tag"
                }
            },
            "$isolated" : True
        })
    aotids.count()

    # Do the replacement, live. Try to avoid hitting the database, but
    # this *will* hit it a lot, whatever you do. In developement, 50k
    # articles total, 11k to migrate: ~40 seconds for each operation.
    with benchmark():
        for old_article in aotids:
            old_article.update(set__new_tags=old_article.tags, set__tags=[])
            Article.objects.get(id=old_article.id).update(set__tags=old_article.new_tags)
            old_article.update(unset__new_tags=True)

    # Check everything is really done.
    ArticlesOldTags.objects(new_tags__exists=True).count()
