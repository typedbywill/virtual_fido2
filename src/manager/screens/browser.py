from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, Static

from src.config import EXTENSION_DIR
from src.manager.browser_installer import BrowserInfo, detect_browsers, install_extension


class BrowserScreen(Screen):
    BINDINGS = [("escape", "back", "Voltar")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]Instalar extensão no navegador[/bold]\n", id="title"),
            Static("Selecione um navegador detectado:", id="hint"),
            ListView(id="browser-list"),
            VerticalScroll(Static("", id="output"), id="output-scroll"),
            Button("Voltar", id="back"),
            id="browser-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        browser_list = self.query_one("#browser-list", ListView)
        self._browsers: list[BrowserInfo] = []
        browsers = detect_browsers()

        if not browsers:
            self.query_one("#hint", Static).update(
                "[yellow]Nenhum navegador detectado.[/yellow]\n"
                f"Carregue manualmente a extensão em:\n{EXTENSION_DIR}"
            )
            return

        for browser in browsers:
            self._browsers.append(browser)
            browser_list.append(
                ListItem(Label(f"{browser.name} ({browser.executable})"))
            )

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self._browsers:
            return
        index = event.list_view.index
        if index is None or index >= len(self._browsers):
            return

        browser = self._browsers[index]
        result = install_extension(browser)
        output = self.query_one("#output", Static)
        if result["success"]:
            output.update(f"[green]{result['message']}[/green]")
        else:
            output.update(f"[red]{result['message']}[/red]")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.action_back()

    def action_back(self) -> None:
        self.app.pop_screen()
