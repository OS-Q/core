import click
from tabulate import tabulate

from core import app
from core.compat import string_types


def format_value(raw):
    if isinstance(raw, bool):
        return "Yes" if raw else "No"
    if isinstance(raw, string_types):
        return raw
    return str(raw)


@click.group(short_help="Manage system settings")
def cli():
    pass


@cli.command("get", short_help="Get existing setting/-s")
@click.argument("name", required=False)
def settings_get(name):
    tabular_data = []
    for key, options in sorted(app.DEFAULT_SETTINGS.items()):
        if name and name != key:
            continue
        raw_value = app.get_setting(key)
        formatted_value = format_value(raw_value)

        if raw_value != options["value"]:
            default_formatted_value = format_value(options["value"])
            formatted_value += "%s" % (
                "\n" if len(default_formatted_value) > 10 else " "
            )
            formatted_value += "[%s]" % click.style(
                default_formatted_value, fg="yellow"
            )

        tabular_data.append(
            (click.style(key, fg="cyan"), formatted_value, options["description"])
        )

    click.echo(
        tabulate(
            tabular_data, headers=["Name", "Current value [Default]", "Description"]
        )
    )


@cli.command("set", short_help="Set new value for the setting")
@click.argument("name")
@click.argument("value")
@click.pass_context
def settings_set(ctx, name, value):
    app.set_setting(name, value)
    click.secho("The new value for the setting has been set!", fg="green")
    ctx.invoke(settings_get, name=name)


@cli.command("reset", short_help="Reset settings to default")
@click.pass_context
def settings_reset(ctx):
    app.reset_settings()
    click.secho("The settings have been reseted!", fg="green")
    ctx.invoke(settings_get)
