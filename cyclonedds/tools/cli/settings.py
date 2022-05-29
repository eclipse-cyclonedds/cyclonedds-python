import rich_click as click


click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.COMMAND_GROUPS = {
    "cyclonedds": [
        {
            "name": "DDS entities",
            "commands": ["ls", "watch"],
        },
        {
            "name": "DDS applications",
            "commands": ["ps"],
        },
        {
            "name": "Data",
            "commands": ["subscribe"],
        },
        {
            "name": "Utilities",
            "commands": ["typeof", "performance"],
        },
    ]
}

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
