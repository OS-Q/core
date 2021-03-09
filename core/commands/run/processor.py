
from core.commands.platform import platform_install as cmd_platform_install
from core.commands.test.processor import CTX_META_TEST_RUNNING_NAME
from core.platform.exception import UnknownPlatform
from core.platform.factory import PlatformFactory
from core.project.exception import UndefinedEnvPlatformError

# pylint: disable=too-many-instance-attributes


class EnvironmentProcessor(object):
    def __init__(  # pylint: disable=too-many-arguments
        self, cmd_ctx, name, config, targets, upload_port, silent, verbose, jobs
    ):
        self.cmd_ctx = cmd_ctx
        self.name = name
        self.config = config
        self.targets = [str(t) for t in targets]
        self.upload_port = upload_port
        self.silent = silent
        self.verbose = verbose
        self.jobs = jobs
        self.options = config.items(env=name, as_dict=True)

    def get_build_variables(self):
        variables = {"pioenv": self.name, "project_config": self.config.path}

        if CTX_META_TEST_RUNNING_NAME in self.cmd_ctx.meta:
            variables["piotest_running_name"] = self.cmd_ctx.meta[
                CTX_META_TEST_RUNNING_NAME
            ]

        if self.upload_port:
            # override upload port with a custom from CLI
            variables["upload_port"] = self.upload_port
        return variables

    def get_build_targets(self):
        return (
            self.targets
            if self.targets
            else self.config.get("env:" + self.name, "targets", [])
        )

    def process(self):
        if "platform" not in self.options:
            raise UndefinedEnvPlatformError(self.name)

        build_vars = self.get_build_variables()
        build_targets = list(self.get_build_targets())

        # skip monitor target, we call it above
        if "monitor" in build_targets:
            build_targets.remove("monitor")

        try:
            p = PlatformFactory.new(self.options["platform"])
        except UnknownPlatform:
            self.cmd_ctx.invoke(
                cmd_platform_install,
                platforms=[self.options["platform"]],
                skip_default_package=True,
            )
            p = PlatformFactory.new(self.options["platform"])

        result = p.run(build_vars, build_targets, self.silent, self.verbose, self.jobs)
        return result["returncode"] == 0
