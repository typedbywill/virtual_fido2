import subprocess
import sys

from textual.app import App, ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Button, Footer, Header, Static

from src.config import PROJECT_ROOT, daemon_base_url
from src.manager import browser_installer, daemon_client
from src.manager.screens.browser import BrowserScreen
from src.manager.screens.credentials import CredentialsScreen
from src.manager.screens.service import ServiceScreen


class VirtualFido2App(App):
    CSS = """
    Screen {
        background: $surface;
    }

    #main-container {
        padding: 1 2;
        height: 100%;
    }

    #title {
        margin-bottom: 1;
    }

    #status-bar {
        margin-bottom: 1;
        padding: 1;
        background: $panel;
    }

    Button {
        margin: 0 0 1 0;
        width: 100%;
    }

    #output-scroll {
        height: 1fr;
        margin-top: 1;
    }

    #service-container, #browser-container, #credentials-container {
        padding: 1 2;
    }

    #confirm-dialog, #import-dialog, #generate-dialog, #edit-dialog {
        padding: 1 2;
        width: 80;
        height: auto;
        background: $panel;
        border: tall $primary;
    }

    .muted {
        color: $text-muted;
    }
    """

    BINDINGS = [("q", "quit", "Sair")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Container(
            Static(
                "[bold cyan]Virtual FIDO2[/bold cyan] — Gerenciador\n",
                id="title",
            ),
            Static("", id="status-bar"),
            Button("1. Instalar serviço", id="install-service", variant="success"),
            Button("2. Gerenciar serviço", id="manage-service"),
            Button("3. Instalar extensão no navegador", id="install-extension"),
            Button("4. Abrir painel web", id="open-web"),
            Button("5. Gerenciar chaves FIDO2", id="manage-credentials"),
            VerticalScroll(Static("", id="output"), id="output-scroll"),
            id="main-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        daemon_online = daemon_client.is_daemon_online()
        try:
            systemd = daemon_client.get_systemd_status()
            systemd_ok = systemd["active"]
        except Exception:
            systemd_ok = False

        status_bar = self.query_one("#status-bar", Static)
        daemon_text = "[green]online[/green]" if daemon_online else "[red]offline[/red]"
        service_text = "[green]ativo[/green]" if systemd_ok else "[red]inativo[/red]"
        status_bar.update(
            f"Daemon: {daemon_text}  |  Serviço systemd: {service_text}  |  URL: {daemon_base_url()}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        output = self.query_one("#output", Static)
        bid = event.button.id or ""

        if bid == "install-service":
            self._run_install(output)
        elif bid == "manage-service":
            self.push_screen(ServiceScreen())
        elif bid == "install-extension":
            self.push_screen(BrowserScreen())
        elif bid == "open-web":
            self._open_web(output)
        elif bid == "manage-credentials":
            self.push_screen(CredentialsScreen())

    def _run_install(self, output: Static) -> None:
        venv_python = f"{PROJECT_ROOT}/.venv/bin/python"
        if not __import__("os").path.isfile(venv_python):
            output.update("[yellow]Criando ambiente virtual…[/yellow]")
            subprocess.run([sys.executable, "-m", "venv", f"{PROJECT_ROOT}/.venv"], check=True)
            subprocess.run(
                [venv_python, "-m", "pip", "install", "-r", f"{PROJECT_ROOT}/requirements.txt"],
                check=True,
            )

        try:
            from src import daemon_manager

            result = daemon_manager.install(python_path=venv_python)
            output.update(f"[green]{result['message']}[/green]")
        except Exception as e:
            output.update(f"[red]{e}[/red]")
        self.refresh_status()

    def _open_web(self, output: Static) -> None:
        if not daemon_client.is_daemon_online():
            output.update(
                "[red]Daemon offline. Instale/inicie o serviço antes de abrir o painel.[/red]"
            )
            return
        result = browser_installer.open_web_panel()
        color = "green" if result["success"] else "red"
        output.update(f"[{color}]{result['message']}[/{color}]")

    def action_quit(self) -> None:
        self.exit()
