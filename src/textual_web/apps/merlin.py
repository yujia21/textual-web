from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual import events
from textual.color import Color
from textual.containers import Grid
from textual.renderables.gradient import LinearGradient
from textual.widget import Widget
from textual.widgets import Label, Switch

COLORS = [
    "#881177",
    "#aa3355",
    "#cc6666",
    "#ee9944",
    "#eedd00",
    "#99dd55",
    "#44dd88",
    "#22ccbb",
    "#00bbcc",
    "#0099cc",
    "#3366bb",
    "#663399",
]


TOGGLES: dict[int, tuple[int, ...]] = {
    1: (2, 4, 5),
    2: (1, 3),
    3: (2, 5, 6),
    4: (1, 7),
    5: (2, 4, 6, 8),
    6: (3, 9),
    7: (4, 5, 8),
    8: (7, 9),
    9: (5, 6, 8),
}


class LabelSwitch(Widget):
    DEFAULT_CSS = """
    LabelSwitch Label {
        text-align: center;
        width: 1fr;       
        text-style: bold; 
        color: $text-muted;
    }
    """

    def __init__(self, switch_no: int) -> None:
        self.switch_no = switch_no
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Label(str(self.switch_no))
        yield Switch(id=f"switch-{self.switch_no}", name=str(self.switch_no))


class MerlinApp(App):
    CSS = """

    Screen {
        align: center middle;
        background: transparent;
    }

    Screen.-win {
        background: $success;
    }
    
    Grid {
        width: auto;
        height: auto;
        border: thick $primary;
        padding: 1 2;
        grid-size: 3 3;
        grid-rows: auto;
        grid-columns: auto;
        grid-gutter: 1 1;
        background: $surface;
    }

    """

    def render(self) -> LinearGradient:
        stops = [(i / (len(COLORS) - 1), Color.parse(c)) for i, c in enumerate(COLORS)]
        return LinearGradient(30.0, stops)

    def compose(self) -> ComposeResult:
        with Grid():
            for switch in (7, 8, 9, 4, 5, 6, 1, 2, 3):
                yield LabelSwitch(switch)

    def on_mount(self) -> ComposeResult:
        for switch_no in range(1, 10):
            if random.randint(0, 1):
                self.query_one(f"#switch-{switch_no}").toggle()

    def check_win(self) -> bool:
        on_switches = {switch.name for switch in self.query(Switch) if switch.value}
        return on_switches == {1, 2, 3, 4, 6, 7, 8, 9}

    def on_switch_changed(self, event: Switch.Changed) -> None:
        switch_no = int(event.switch.name or "0")
        with self.prevent(Switch.Changed):
            for toggle_no in TOGGLES[switch_no]:
                self.query_one(f"#switch-{toggle_no}", Switch).toggle()
        if self.check_win():
            self.query_one("Screen").add_class("-win")

    def on_key(self, event: events.Key) -> None:
        if event.character and event.character.isdigit():
            self.query_one(f"#switch-{event.character}", Switch).toggle()


if __name__ == "__main__":
    MerlinApp().run()