
import os
from urllib.parse import urlparse

import click
import uvicorn
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.status import HTTP_403_FORBIDDEN

from core.commands.home.rpc.handlers.account import AccountRPC
from core.commands.home.rpc.handlers.app import AppRPC
from core.commands.home.rpc.handlers.ide import IDERPC
from core.commands.home.rpc.handlers.misc import MiscRPC
from core.commands.home.rpc.handlers.os import OSRPC
from core.commands.home.rpc.handlers.piocore import PIOCoreRPC
from core.commands.home.rpc.handlers.project import ProjectRPC
from core.commands.home.rpc.server import WebSocketJSONRPCServerFactory
from core.compat import get_running_loop
from core.exception import PlatformioException
from core.package.manager.core import get_core_package_dir
from core.proc import force_exit


class ShutdownMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and b"__shutdown__" in scope.get("query_string", {}):
            await shutdown_server()
        await self.app(scope, receive, send)


async def shutdown_server(_=None):
    get_running_loop().call_later(0.5, force_exit)
    return PlainTextResponse("Server has been shutdown!")


async def protected_page(_):
    return PlainTextResponse(
        "Protected PlatformIO Home session", status_code=HTTP_403_FORBIDDEN
    )


def run_server(host, port, no_open, shutdown_timeout, home_url):
    contrib_dir = get_core_package_dir("contrib-piohome")
    if not os.path.isdir(contrib_dir):
        raise PlatformioException("Invalid path to PIO Home Contrib")

    ws_rpc_factory = WebSocketJSONRPCServerFactory(shutdown_timeout)
    ws_rpc_factory.addHandler(AccountRPC(), namespace="account")
    ws_rpc_factory.addHandler(AppRPC(), namespace="app")
    ws_rpc_factory.addHandler(IDERPC(), namespace="ide")
    ws_rpc_factory.addHandler(MiscRPC(), namespace="misc")
    ws_rpc_factory.addHandler(OSRPC(), namespace="os")
    ws_rpc_factory.addHandler(PIOCoreRPC(), namespace="core")
    ws_rpc_factory.addHandler(ProjectRPC(), namespace="project")

    path = urlparse(home_url).path
    routes = [
        WebSocketRoute(path + "wsrpc", ws_rpc_factory, name="wsrpc"),
        Route(path + "__shutdown__", shutdown_server, methods=["POST"]),
        Mount(path, StaticFiles(directory=contrib_dir, html=True), name="static"),
    ]
    if path != "/":
        routes.append(Route("/", protected_page))

    uvicorn.run(
        Starlette(
            middleware=[Middleware(ShutdownMiddleware)],
            routes=routes,
            on_startup=[
                lambda: click.echo(
                    "PIO Home has been started. Press Ctrl+C to shutdown."
                ),
                lambda: None if no_open else click.launch(home_url),
            ],
        ),
        host=host,
        port=port,
        log_level="warning",
    )
