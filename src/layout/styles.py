from typing import Literal


def styling(
    text: str,
    tag: Literal["h1", "h2", "h3", "h4", "h5", "h6", "p"] = "h2",
    text_align: Literal["left", "right", "center", "justify"] = "center",
    font_size: int = 32,
) -> tuple[str, bool]:
    style = f"text-align: {text_align};" f"font-size: {font_size}px;"

    styled_text = f'<{tag} style="{style}">{text}</{tag}>'
    return styled_text, True
