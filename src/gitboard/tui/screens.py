from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class AuthScreen(ModalScreen[str]):
    CSS = """
    AuthScreen {
        align: center middle;
    }

    #auth-dialog {
        width: 50;
        height: auto;
        padding: 2 3;
        border: thick $primary;
        background: $surface;
    }

    #auth-title {
        text-style: bold;
        width: 1fr;
        height: 1;
        content-align: center middle;
        margin-bottom: 1;
    }

    #auth-description {
        width: 1fr;
        height: auto;
        margin-bottom: 1;
    }

    #pat-input {
        width: 1fr;
        margin-bottom: 1;
    }

    #auth-buttons {
        layout: horizontal;
        height: auto;
        align: center middle;
    }

    Button {
        margin: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="auth-dialog"):
            yield Label("Authenticate gitboard", id="auth-title")
            yield Label(
                "Enter your GitHub Personal Access Token with repo scope.",
                id="auth-description",
            )
            yield Input(placeholder="ghp_...", password=True, id="pat-input")
            with Horizontal(id="auth-buttons"):
                yield Button("Submit", variant="primary", id="auth-submit")
                yield Button("Cancel", id="auth-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "auth-submit":
            token = self.query_one("#pat-input", Input).value.strip()
            if token:
                self.dismiss(token)
        elif event.button.id == "auth-cancel":
            self.dismiss(None)  # type: ignore[arg-type]

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "pat-input":
            token = event.value.strip()
            if token:
                self.dismiss(token)
