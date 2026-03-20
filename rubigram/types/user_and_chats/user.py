import rubigram
from rubigram import enums, utils
from datetime import datetime
from rubigram import types
from rubigram import raw

from ..object import Object


class User(Object):
    def __init__(
            self,
            *,
            client: rubigram.client,
            id: int,
            is_self: bool = None,
            is_contact: bool = None,
            is_deleted: bool = None,
            is_bot: bool = None,
            is_verified: bool = None,
            first_name: str = None,
            last_name: str = None,
            status: "enums.UserStatus" = None,
            last_online_date: datetime = None,
            username: str = None,
            language_code: str = None,
            phone_number: str = None,
            avatar: "types.ChatAvatar" = None,
            
    ) :
        super().__init__(client)

        self.id = id
        self.is_self = is_self
        self.is_contact = is_contact
        self.is_deleted = is_deleted
        self.is_bot = is_bot
        self.is_verified = is_verified
        self.first_name = first_name
        self.last_name = last_name
        self.status = status
        self.last_online_date = last_online_date
        self.username = username
        self.language_code = language_code
        self.phone_number = phone_number
        self.avatar = avatar
        
    
    @staticmethod
    def _parse(client, user: "raw.base.User") -> User | None:
        if user is None or isinstance(user, raw.types.UserEmpty):
            return None

        return User(
            id=user.id,
            is_self=user.is_self,
            is_contact=user.contact,
            is_deleted=user.deleted,
            is_bot=user.bot,
            is_verified=user.verified,
            first_name=user.first_name,
            last_name=user.last_name,
            **User._parse_status(user.status, user.bot),
            username=user.username,
            language_code=user.lang_code,
            phone_number=user.phone,
            avatar=types.ChatAvatar._parse(client, user.avatar, user.id, user.access_hash),
            client=client
        )

    @staticmethod
    def _parse_status(user_status: "raw.base.UserStatus", is_bot: bool = False):
        if isinstance(user_status, raw.types.UserStatusOnline):
            status, date = enums.UserStatus.ONLINE, user_status.expires
        elif isinstance(user_status, raw.types.UserStatusOffline):
            status, date = enums.UserStatus.OFFLINE, user_status.was_online
        elif isinstance(user_status, raw.types.UserStatusRecently):
            status, date = enums.UserStatus.RECENTLY, None
        elif isinstance(user_status, raw.types.UserStatusLastWeek):
            status, date = enums.UserStatus.LAST_WEEK, None
        elif isinstance(user_status, raw.types.UserStatusLastMonth):
            status, date = enums.UserStatus.LAST_MONTH, None
        else:
            status, date = enums.UserStatus.LONG_AGO, None

        last_online_date = None
        next_offline_date = None

        if is_bot:
            status = None

        if status == enums.UserStatus.OFFLINE:
            last_online_date = utils.timestamp_to_datetime(date)

        return {
            "status": status,
            "last_online_date": last_online_date,
            "next_offline_date": next_offline_date
        }
        
    def block(self):
        """Bound method *block* of :obj:`~pyrogram.types.User`.

        Use as a shortcut for:

        .. code-block:: python

            await client.block_user(123456789)

        Example:
            .. code-block:: python

                await user.block()

        Returns:
            True on success.

        Raises:
            RPCError: In case of a Telegram RPC error.
        """

        return self._client.block_user(self.id)