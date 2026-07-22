from textual.app import ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Select, Static

from src.manager import browser_installer, credentials_client
from src.manager.credentials_client import CredentialsError


class ConfirmDeleteScreen(ModalScreen[bool]):
    def __init__(self, credential_id: str, username: str) -> None:
        super().__init__()
        self.credential_id = credential_id
        self.username = username

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"Excluir credencial de [bold]{self.username}[/bold]?"),
            Static(f"ID: {self.credential_id[:24]}…", classes="muted"),
            Horizontal(
                Button("Sim, excluir", id="yes", variant="error"),
                Button("Cancelar", id="no"),
            ),
            id="confirm-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class ImportCredentialScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Importar credencial[/bold]"),
            Label("Credential ID"),
            Input(placeholder="Base64url ou hex", id="cred-id"),
            Label("RP ID"),
            Input(placeholder="github.com", id="rp-id"),
            Label("User Handle"),
            Input(id="user-handle"),
            Label("Username"),
            Input(id="username"),
            Label("Caminho do arquivo PEM"),
            Input(placeholder="/caminho/chave.pem", id="key-file"),
            Label("Algoritmo"),
            Select(
                [( "ES256", "ES256"), ("RS256", "RS256"), ("EdDSA", "EdDSA")],
                value="ES256",
                id="algorithm",
            ),
            Static("", id="form-error"),
            Horizontal(
                Button("Importar", id="submit", variant="success"),
                Button("Cancelar", id="cancel"),
            ),
            id="import-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
            return

        error = self.query_one("#form-error", Static)
        try:
            pem = credentials_client.read_pem_file(self.query_one("#key-file", Input).value.strip())
            credentials_client.import_credential(
                credential_id=self.query_one("#cred-id", Input).value.strip(),
                rp_id=self.query_one("#rp-id", Input).value.strip(),
                user_handle=self.query_one("#user-handle", Input).value.strip(),
                username=self.query_one("#username", Input).value.strip(),
                private_key_pem=pem,
                algorithm=str(self.query_one("#algorithm", Select).value),
            )
            self.dismiss(True)
        except (CredentialsError, Exception) as e:
            error.update(f"[red]{e}[/red]")


class GenerateCredentialScreen(ModalScreen[bool]):
    def compose(self) -> ComposeResult:
        yield Container(
            Static("[bold]Gerar nova credencial[/bold]"),
            Label("RP ID"),
            Input(placeholder="github.com", id="rp-id"),
            Label("User Handle"),
            Input(id="user-handle"),
            Label("Username"),
            Input(id="username"),
            Label("Algoritmo"),
            Select(
                [("ES256", "ES256"), ("RS256", "RS256"), ("EdDSA", "EdDSA")],
                value="ES256",
                id="algorithm",
            ),
            Static("", id="form-error"),
            Static("", id="form-result"),
            Horizontal(
                Button("Gerar", id="submit", variant="success"),
                Button("Cancelar", id="cancel"),
            ),
            id="generate-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
            return

        error = self.query_one("#form-error", Static)
        result_box = self.query_one("#form-result", Static)
        try:
            result = credentials_client.generate_credential(
                rp_id=self.query_one("#rp-id", Input).value.strip(),
                user_handle=self.query_one("#user-handle", Input).value.strip(),
                username=self.query_one("#username", Input).value.strip(),
                algorithm=str(self.query_one("#algorithm", Select).value),
            )
            result_box.update(
                f"[green]Credencial gerada![/green]\n"
                f"ID: {result.get('credentialId', '')}\n"
                f"Guarde o PEM exibido no painel web se o daemon estiver ativo."
            )
            self.dismiss(True)
        except (CredentialsError, Exception) as e:
            error.update(f"[red]{e}[/red]")


class EditCredentialScreen(ModalScreen[bool]):
    def __init__(self, cred: dict) -> None:
        super().__init__()
        self.cred = cred

    def compose(self) -> ComposeResult:
        yield Container(
            Static(f"[bold]Editar {self.cred.get('username', '')}[/bold]"),
            Label("RP ID"),
            Input(value=self.cred.get("rpId", ""), id="rp-id"),
            Label("Username"),
            Input(value=self.cred.get("username", ""), id="username"),
            Label("User Handle"),
            Input(value=self.cred.get("userHandle", ""), id="user-handle"),
            Label("Sign Count"),
            Input(value=str(self.cred.get("signCount", 0)), id="sign-count"),
            Static("", id="form-error"),
            Horizontal(
                Button("Salvar", id="submit", variant="success"),
                Button("Cancelar", id="cancel"),
            ),
            id="edit-dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(False)
            return

        error = self.query_one("#form-error", Static)
        try:
            credentials_client.update_credential(
                self.cred["credentialId"],
                {
                    "rpId": self.query_one("#rp-id", Input).value.strip(),
                    "username": self.query_one("#username", Input).value.strip(),
                    "userHandle": self.query_one("#user-handle", Input).value.strip(),
                    "signCount": int(self.query_one("#sign-count", Input).value.strip() or "0"),
                    "backupEligible": self.cred.get("backupEligible", True),
                    "backupState": self.cred.get("backupState", True),
                    "isSynced": self.cred.get("isSynced", True),
                },
            )
            self.dismiss(True)
        except (CredentialsError, ValueError, Exception) as e:
            error.update(f"[red]{e}[/red]")


class CredentialsScreen(Screen):
    BINDINGS = [("escape", "back", "Voltar"), ("r", "refresh", "Atualizar")]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold]Gerenciar chaves FIDO2[/bold]\n", id="title"),
            Static("", id="mode-hint"),
            ListView(id="cred-list"),
            Horizontal(
                Button("Importar", id="import", variant="success"),
                Button("Gerar nova", id="generate"),
                Button("Editar", id="edit"),
                Button("Excluir", id="delete", variant="error"),
                Button("Painel web", id="web"),
            ),
            Static("", id="output"),
            Button("Voltar", id="back"),
            id="credentials-container",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_list()

    def refresh_list(self) -> None:
        online = credentials_client.is_online()
        hint = self.query_one("#mode-hint", Static)
        hint.update(
            "[green]Daemon ativo — alterações via API[/green]"
            if online
            else "[yellow]Daemon inativo — modo offline (reinicie o serviço após alterações)[/yellow]"
        )

        cred_list = self.query_one("#cred-list", ListView)
        cred_list.clear()
        self._credentials = credentials_client.list_credentials()

        if not self._credentials:
            cred_list.append(ListItem(Label("Nenhuma credencial cadastrada.")))
            return

        for cred in self._credentials:
            label = (
                f"{cred.get('username', '?')} @ {cred.get('rpId', '?')} "
                f"({cred.get('algorithm', '?')}, count={cred.get('signCount', 0)})"
            )
            cred_list.append(ListItem(Label(label)))

    def _selected_credential(self) -> dict | None:
        cred_list = self.query_one("#cred-list", ListView)
        if cred_list.index is None or not hasattr(self, "_credentials"):
            return None
        if cred_list.index >= len(self._credentials):
            return None
        return self._credentials[cred_list.index]

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        output = self.query_one("#output", Static)
        bid = event.button.id or ""

        if bid == "back":
            self.action_back()
            return

        if bid == "web":
            result = browser_installer.open_web_panel()
            color = "green" if result["success"] else "red"
            output.update(f"[{color}]{result['message']}[/{color}]")
            return

        if bid == "import":
            if await self.app.push_screen_wait(ImportCredentialScreen()):
                self.refresh_list()
                output.update("[green]Credencial importada.[/green]")
            return

        if bid == "generate":
            if await self.app.push_screen_wait(GenerateCredentialScreen()):
                self.refresh_list()
                output.update("[green]Credencial gerada.[/green]")
            return

        cred = self._selected_credential()
        if not cred:
            output.update("[yellow]Selecione uma credencial na lista.[/yellow]")
            return

        if bid == "edit":
            if await self.app.push_screen_wait(EditCredentialScreen(cred)):
                self.refresh_list()
                output.update("[green]Credencial atualizada.[/green]")
            return

        if bid == "delete":
            confirmed = await self.app.push_screen_wait(
                ConfirmDeleteScreen(cred["credentialId"], cred.get("username", ""))
            )
            if confirmed:
                try:
                    credentials_client.delete_credential(cred["credentialId"])
                    self.refresh_list()
                    output.update("[green]Credencial excluída.[/green]")
                except CredentialsError as e:
                    output.update(f"[red]{e}[/red]")

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_refresh(self) -> None:
        self.refresh_list()
