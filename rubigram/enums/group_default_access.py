from enum import Enum


class GroupDefaultAccessPermission(str, Enum):
    VIEW_MEMBERS = "ViewMembers"
    ADD_MEMBER = "AddMember"
    SEND_MESSAGES = "SendMessages"
    VIEW_ADMINS = "ViewAdmins"
