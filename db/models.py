from peewee import *


db = SqliteDatabase('test.db')


class BaseModel(Model):
    class Meta:
        database = db


class YTVideo(BaseModel):
    uid = CharField()

    title = CharField()
    url = CharField()
    time_posted = DateTimeField()

    views = IntegerField()
    likes = IntegerField()
    comments = IntegerField()
    favorite_count = IntegerField()


class YTChannel(BaseModel):
    name = CharField()
    vanity_id = CharField()
    external_id = CharField()
    # time_created = DateTimeField()
