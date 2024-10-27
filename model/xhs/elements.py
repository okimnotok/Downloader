from db.handler import DBBase
from model.base import BaseModel, BooleanField, DictField, ModelField, IntegerField, StringField


class User(BaseModel, DBBase):
    nick_name = StringField(name="nick_name")
    avatar = StringField(name="avatar")
    user_id = StringField(name="user_id")
    nickname = StringField(name="nickname")
    image = StringField(name="image")

    class Meta:
        table_name = "xhs_user"
        pk = "user_id"


class InteractInfo(BaseModel):
    liked = BooleanField(name="liked")
    liked_count = StringField(name="liked_count")
    collected = BooleanField(name="collected")
    collected_count = StringField(name="collected_count")
    comment_count = StringField(name="comment_count")
    share_count = StringField(name="share_count")
    followed = BooleanField(name="followed")
    relation = StringField(name="relation")


class Tag(BaseModel):
    id = StringField(name="id")
    name = StringField(name="name")
    type = StringField(name="type")


class ImageScene(BaseModel):
    image_scene = StringField(name="image_scene", choice=["WB_DFT", "WB_PRV"])
    url = StringField(name="url")


class Cover(BaseModel):
    stream = DictField(name="stream")
    live_photo = BooleanField(name="live_photo")
    file_id = StringField(name="file_id")
    height = IntegerField(name="height")
    width = IntegerField(name="width")
    url = StringField(name="url")
    info_list = ModelField(name="info_list", model=ImageScene, multi=True)
    url_pre = StringField(name="url_pre")
    url_default = StringField(name="url_default")


class NoteCard(BaseModel):
    note_id = StringField(name="note_id")
    display_title = StringField(name="display_title")
    title = StringField(name="title")
    desc = StringField(name="desc")
    user = ModelField(name="user", model=User)
    cover = ModelField(name="cover", model=Cover)
    type = StringField(name="type", choice=["video", "normal"])
    interact_info = ModelField(name="interact_info", model=InteractInfo)
    image_list = ModelField(name="image_list", model=Cover, multi=True)
    tag_list = ModelField(name="tag_list", model=Tag, multi=True)


class TargetComment(BaseModel):
    id = StringField(name="id")
    user_info = ModelField(name="user_info", model=User)


class SubComment(BaseModel):
    id = StringField(name="id")
    note_id = StringField(name="note_id")
    shown_tags = ModelField(name="shown_tags", model=Tag, multi=True)
    pictures = ModelField(name="pictures", model=Cover, multi=True)
    content = StringField(name="content")
    status = InteractInfo(name="status")
    liked = BooleanField(name="liked")
    liked_count = StringField(name="liked_count")
    user_info = ModelField(name="user", model=User)
    ip_location = StringField(name="ip_location")
    at_users = ModelField(name="at_users", model=User, multi=True)
    target_comment = ModelField(name="target_comment", model=TargetComment)


class Comment(BaseModel):
    id = StringField(name="id")
    note_id = StringField(name="note_id")
    shown_tags = ModelField(name="shown_tags", model=Tag, multi=True)
    pictures = ModelField(name="pictures", model=Cover, multi=True)
    content = StringField(name="content")
    status = InteractInfo(name="status")
    liked = BooleanField(name="liked")
    liked_count = StringField(name="liked_count")
    user_info = ModelField(name="user", model=User)
    ip_location = StringField(name="ip_location")
    at_users = ModelField(name="at_users", model=User, multi=True)
    sub_comments = ModelField(name="sub_comments", model=SubComment, multi=True)
