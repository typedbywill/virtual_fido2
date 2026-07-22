from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label, Static

from src import daemon_manager
from src.manager import daemon_client


class ServiceScreen(Screen):
    BINDINGS = [("escape", "back", "Voltar")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]Gerenciar serviço[/bold]\n", id="title"),
            Button("Instalar serviço (systemd)", id="install", variant="success"),
            Button("Status", id="status"),
            Button("Iniciar", id="start"),
            Button("Parar", id="stop"),
            Button("Reiniciar", id="restart"),
            Button("Desinstalar serviço", id="uninstall", variant="error"),
            Button("Ver logs (sair com Ctrl+C)", id="logs"),
            VerticalScroll(Static("", id="output"), id="output-scroll"),
            id="service-container",
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        output = self.query_one("#output", Static)
        bid = event.button.id or ""

        try:
            if bid == "install":
                result = daemon_client.install_service()
                output.update(f"[green]{result['message']}[/green]")
            elif bid == "uninstall":
                result = daemon_client.uninstall_service()
                output.update(f"[green]{result['message']}[/green]")
            elif bid == "status":
                result = daemon_client.get_systemd_status()
                color = "green" if result["active"] else "red"
                output.update(f"[{color}]{result['output']}[/{color}]")
            elif bid == "start":
                result = daemon_client.start_service()
                output.update(f"[green]{result['message']}[/green]")
            elif bid == "stop":
                result = daemon_client.stop_service()
                output.update(f"[green]{result['message']}[/green]")
            elif bid == "restart":
                result = daemon_client.restart_service()
                output.update(f"[green]{result['message']}[/green]")
            elif bid == "logs":
                self.app.exit()
                try:
                    daemon_manager.show_logs(follow=True)
                except daemon_manager.SystemdNotAvailableError as e:
                    print(e)
                return
        except daemon_manager.SystemdNotAvailableError as e:
            output.update(f"[red]{e}[/red]")
        except daemon_manager.DaemonError as e:
            output.update(f"[red]{e}[/red]")

    def action_back(self) -> None:
        self.app.pop_screen()
