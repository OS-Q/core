
# pylint: disable=too-many-arguments, too-many-statements
# pylint: disable=too-many-locals, too-many-branches

import os
import signal
from os.path import isfile

import click

from core import app, exception, fs, proc
from core.commands.debug import helpers
from core.commands.debug.exception import DebugInvalidOptionsError
from core.commands.platform import platform_install as cmd_platform_install
from core.package.manager.core import inject_contrib_pysite
from core.platform.exception import UnknownPlatform
from core.platform.factory import PlatformFactory
from core.project.config import ProjectConfig
from core.project.exception import ProjectEnvsNotAvailableError
from core.project.helpers import is_platformio_project, load_project_ide_data


@click.command(
    "debug",
    context_settings=dict(ignore_unknown_options=True),
    short_help="Unified debugger",
)
@click.option(
    "-d",
    "--project-dir",
    default=os.getcwd,
    type=click.Path(
        exists=True, file_okay=False, dir_okay=True, writable=True, resolve_path=True
    ),
)
@click.option(
    "-c",
    "--project-conf",
    type=click.Path(
        exists=True, file_okay=True, dir_okay=False, readable=True, resolve_path=True
    ),
)
@click.option("--environment", "-e", metavar="<environment>")
@click.option("--verbose", "-v", is_flag=True)
@click.option("--interface", type=click.Choice(["gdb"]))
@click.argument("__unprocessed", nargs=-1, type=click.UNPROCESSED)
@click.pass_context
def cli(ctx, project_dir, project_conf, environment, verbose, interface, __unprocessed):
    app.set_session_var("custom_project_conf", project_conf)

    # use env variables from Eclipse or CLion
    for sysenv in ("CWD", "PWD", "PLATFORMIO_PROJECT_DIR"):
        if is_platformio_project(project_dir):
            break
        if os.getenv(sysenv):
            project_dir = os.getenv(sysenv)

    with fs.cd(project_dir):
        config = ProjectConfig.get_instance(project_conf)
        config.validate(envs=[environment] if environment else None)

        env_name = environment or helpers.get_default_debug_env(config)
        env_options = config.items(env=env_name, as_dict=True)
        if not set(env_options.keys()) >= set(["platform", "board"]):
            raise ProjectEnvsNotAvailableError()

        try:
            platform = PlatformFactory.new(env_options["platform"])
        except UnknownPlatform:
            ctx.invoke(
                cmd_platform_install,
                platforms=[env_options["platform"]],
                skip_default_package=True,
            )
            platform = PlatformFactory.new(env_options["platform"])

        debug_options = helpers.configure_initial_debug_options(platform, env_options)
        assert debug_options

    if not interface:
        return helpers.predebug_project(ctx, project_dir, env_name, False, verbose)

    ide_data = load_project_ide_data(project_dir, env_name)
    if not ide_data:
        raise DebugInvalidOptionsError("Could not load a build configuration")

    if "--version" in __unprocessed:
        result = proc.exec_command([ide_data["gdb_path"], "--version"])
        if result["returncode"] == 0:
            return click.echo(result["out"])
        raise exception.PlatformioException("\n".join([result["out"], result["err"]]))

    try:
        fs.ensure_udev_rules()
    except exception.InvalidUdevRules as e:
        click.echo(
            helpers.escape_gdbmi_stream("~", str(e) + "\n")
            if helpers.is_gdbmi_mode()
            else str(e) + "\n",
            nl=False,
        )

    try:
        debug_options = platform.configure_debug_options(debug_options, ide_data)
    except NotImplementedError:
        # legacy for ESP32 dev-platform <=2.0.0
        debug_options["load_cmds"] = helpers.configure_esp32_load_cmds(
            debug_options, ide_data
        )

    rebuild_prog = False
    preload = debug_options["load_cmds"] == ["preload"]
    load_mode = debug_options["load_mode"]
    if load_mode == "always":
        rebuild_prog = preload or not helpers.has_debug_symbols(ide_data["prog_path"])
    elif load_mode == "modified":
        rebuild_prog = helpers.is_prog_obsolete(
            ide_data["prog_path"]
        ) or not helpers.has_debug_symbols(ide_data["prog_path"])
    else:
        rebuild_prog = not isfile(ide_data["prog_path"])

    if preload or (not rebuild_prog and load_mode != "always"):
        # don't load firmware through debug server
        debug_options["load_cmds"] = []

    if rebuild_prog:
        if helpers.is_gdbmi_mode():
            click.echo(
                helpers.escape_gdbmi_stream(
                    "~", "Preparing firmware for debugging...\n"
                ),
                nl=False,
            )
            stream = helpers.GDBMIConsoleStream()
            with proc.capture_std_streams(stream):
                helpers.predebug_project(ctx, project_dir, env_name, preload, verbose)
            stream.close()
        else:
            click.echo("Preparing firmware for debugging...")
            helpers.predebug_project(ctx, project_dir, env_name, preload, verbose)

        # save SHA sum of newly created prog
        if load_mode == "modified":
            helpers.is_prog_obsolete(ide_data["prog_path"])

    if not isfile(ide_data["prog_path"]):
        raise DebugInvalidOptionsError("Program/firmware is missed")

    # run debugging client
    inject_contrib_pysite()

    # pylint: disable=import-outside-toplevel
    from core.commands.debug.process.client import GDBClient, reactor

    client = GDBClient(project_dir, __unprocessed, debug_options, env_options)
    client.spawn(ide_data["gdb_path"], ide_data["prog_path"])

    signal.signal(signal.SIGINT, lambda *args, **kwargs: None)
    reactor.run()

    return True
