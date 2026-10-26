"""Optional user-defined display names for AVR inputs.

The integration identifies inputs by their default names (SOURCE_MENU_MAP
values such as "Game" or "Sat / Cable"). Users can give any input a custom
display name; commands and feedback are unaffected because they are matched
by input code.
"""


def display_name(source: str, names: dict[str, str] | None) -> str:
    """Return the custom name for a default input name, or the default."""
    if not names:
        return source
    return names.get(source) or source


def default_name(source: str, names: dict[str, str] | None) -> str:
    """Map a custom display name back to its default input name.

    Default names are passed through unchanged, so automations written with
    the default names keep working after inputs are renamed.
    """
    if names:
        for default, custom in names.items():
            if custom == source:
                return default
    return source


def display_list(
    sources: tuple[str, ...] | list[str],
    visible: list[str] | None,
    names: dict[str, str] | None,
) -> tuple[str, ...]:
    """Return the source list to show: visible inputs, using custom names."""
    shown = [s for s in sources if not visible or s in visible]
    return tuple(display_name(s, names) for s in shown)


def clean_names(user_input: dict[str, str] | None) -> dict[str, str]:
    """Keep only non-empty custom names, trimmed."""
    return {k: v.strip() for k, v in (user_input or {}).items() if v and v.strip()}
