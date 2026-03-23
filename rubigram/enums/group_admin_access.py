from enum import Enum


class GroupAdminAccess(str, Enum):
    CHANGE_INFO = "ChangeInfo"
    PIN_MESSAGES = "PinMessages"
    DELETE_GLOBAL_ALL_MESSAGES = "DeleteGlobalAllMessages"
    BAN_MEMBER = "BanMember"
    SET_JOIN_LINK = "SetJoinLink"
    SET_ADMIN = "SetAdmin"
    SET_MEMBER_ACCESS = "SetMemberAccess"
