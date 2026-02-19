
def make_exe():
    dist = default_python_distribution()
    policy = dist.make_python_packaging_policy()
    policy.resources_location_fallback = "filesystem-relative:prefix"
    python_config = dist.make_python_interpreter_config()
    python_config.run_command = "from cyclonedds.tools.cli.main import cli; cli()"
    exe = dist.to_python_executable(
        name="cyclonedds",
        packaging_policy=policy,
        config=python_config,
    )

    exe.add_python_resources(exe.pip_install(["wheel==0.29.0"]))
    exe.add_python_resources(exe.pip_install(["setuptools==42.0.2"]))
    exe.add_python_resources(exe.pip_install([CWD]))
    return exe

def make_embedded_resources(exe):
    return exe.to_embedded_resources()

def make_install(exe):
    files = FileManifest()
    files.add_python_resource(".", exe)
    return files

def make_msi(exe):
    return exe.to_wix_msi_builder(
        "cyclonedds",
        "Cyclone DDS CLI",
        "11.0.0",
        "Thijs Miedema"
    )


def register_code_signers():
    if not VARS.get("ENABLE_CODE_SIGNING"):
        return

# Call our function to set up automatic code signers.
register_code_signers()

# Tell PyOxidizer about the build targets defined above.
register_target("exe", make_exe)
register_target("resources", make_embedded_resources, depends=["exe"], default_build_script=True)
register_target("install", make_install, depends=["exe"], default=True)
register_target("msi_installer", make_msi, depends=["exe"])

# Resolve whatever targets the invoker of this configuration file is requesting
# be resolved.
resolve_targets()
