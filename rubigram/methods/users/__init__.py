from .profile import UserProfile
from .moderation import UserModeration


class Users(UserProfile, UserModeration):
    pass
