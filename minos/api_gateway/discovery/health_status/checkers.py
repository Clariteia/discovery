# Copyright (C) 2020 Clariteia SL
#
# This file is part of minos framework.
#
# Minos framework can not be copied and/or distributed without the express
# permission of Clariteia SL.
import logging
from asyncio import (
    gather,
)
from typing import (
    Any,
    NoReturn,
)

from aiohttp import (
    ClientConnectorError,
    ClientSession,
)
from yarl import (
    URL,
)

from minos.api_gateway.common import (
    MinosConfig,
)

from ..database import (
    MinosRedisClient,
)

logger = logging.getLogger(__name__)


class HealthStatusChecker:
    """TODO"""

    def __init__(self, config: MinosConfig):
        self.redis_cli = MinosRedisClient(config=config)
        self.redis_conn = self.redis_cli.get_redis_connection()

    async def check(self):
        """TODO

        :return: TODO
        """
        coroutines = (self._check_one(key) for key in self.redis_conn.scan_iter())
        await gather(*coroutines)

    async def _check_one(self, key: str):
        logger.info(f"Checking {key!r} health status...")
        try:
            # noinspection PyTypeChecker
            data: dict[str, Any] = self.redis_cli.get_data(key)
            alive = await self._query_health_status(**data)
            self._update_one(alive, key, data)
        except Exception as exc:
            self.redis_cli.delete_data(key)
            logger.warning(f"An exception was raised while checking {key!r}: {exc!r}")

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    async def _query_health_status(self, ip: str, port: int, **kwargs) -> bool:
        url = URL.build(scheme="http", host=ip, port=port, path="/system/health")

        try:
            async with ClientSession() as session:
                async with session.get(url=url) as response:
                    return response.ok
        except ClientConnectorError:
            return False

    def _update_one(self, alive: bool, key: str, data: dict[str, Any]) -> NoReturn:
        if alive == data["status"]:
            return

        data["status"] = alive
        self.redis_cli.set_data(key, data)
