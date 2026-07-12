from contextvars import ContextVar

_actor_user_id_ctx: ContextVar[int | None] = ContextVar("actor_user_id", default=None)
_ip_address_ctx: ContextVar[str | None] = ContextVar("ip_address", default=None)


def set_actor(actor_user_id: int | None) -> None:
    _actor_user_id_ctx.set(actor_user_id)


def set_ip(ip_address: str | None) -> None:
    _ip_address_ctx.set(ip_address)


def get_actor_user_id() -> int | None:
    return _actor_user_id_ctx.get()


def get_ip_address() -> str | None:
    return _ip_address_ctx.get()