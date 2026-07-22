import os
import subprocess
import sys

from src.config import PROJECT_ROOT, daemon_base_url
from src import daemon_manager
from src.manager import browser_installer, credentials_client, daemon_client
from src.manager.credentials_client import CredentialsError


def clear() -> None:
    os.system("clear" if os.name != "nt" else "cls")


def pause(msg: str = "Pressione Enter para continuar…") -> None:
    input(msg)


def prompt(msg: str, default: str = "") -> str:
    if default:
        value = input(f"{msg} [{default}]: ").strip()
        return value or default
    return input(f"{msg}: ").strip()


def status_line() -> str:
    online = daemon_client.is_daemon_online()
    try:
        svc = daemon_client.get_systemd_status()
        svc_ok = svc["active"]
    except Exception:
        svc_ok = False
    daemon = "online" if online else "offline"
    service = "ativo" if svc_ok else "inativo"
    return f"Daemon: {daemon} | Serviço: {service} | {daemon_base_url()}"


def install_service() -> None:
    venv_python = os.path.join(PROJECT_ROOT, ".venv", "bin", "python")
    if not os.path.isfile(venv_python):
        print("Criando ambiente virtual…")
        subprocess.run([sys.executable, "-m", "venv", os.path.join(PROJECT_ROOT, ".venv")], check=True)
        subprocess.run(
            [venv_python, "-m", "pip", "install", "-r", os.path.join(PROJECT_ROOT, "requirements.txt")],
            check=True,
        )
    try:
        result = daemon_manager.install(python_path=venv_python)
        print(f"\n✔ {result['message']}")
    except Exception as e:
        print(f"\n✘ {e}")


def service_menu() -> None:
    while True:
        clear()
        print("=== Gerenciar serviço ===\n")
        print(status_line(), "\n")
        print("1) Status")
        print("2) Iniciar")
        print("3) Parar")
        print("4) Reiniciar")
        print("5) Desinstalar")
        print("6) Ver logs (Ctrl+C para sair)")
        print("0) Voltar")
        choice = prompt("\nOpção", "0")

        try:
            if choice == "0":
                return
            if choice == "1":
                result = daemon_client.get_systemd_status()
                print("\n" + result["output"])
            elif choice == "2":
                print("\n✔ " + daemon_client.start_service()["message"])
            elif choice == "3":
                print("\n✔ " + daemon_client.stop_service()["message"])
            elif choice == "4":
                print("\n✔ " + daemon_client.restart_service()["message"])
            elif choice == "5":
                confirm = prompt("Confirmar desinstalação? (s/N)", "n").lower()
                if confirm == "s":
                    print("\n✔ " + daemon_client.uninstall_service()["message"])
            elif choice == "6":
                clear()
                daemon_manager.show_logs(follow=True)
                return
            else:
                print("\nOpção inválida.")
        except Exception as e:
            print(f"\n✘ {e}")

        pause()


def browser_menu() -> None:
    while True:
        clear()
        print("=== Instalar extensão ===\n")
        browsers = browser_installer.detect_browsers()
        if not browsers:
            print("Nenhum navegador detectado.")
            print(f"\nCarregue manualmente a extensão em:\n{PROJECT_ROOT}/src/browser_integration/extension")
            pause("\nEnter para voltar…")
            return

        for i, browser in enumerate(browsers, 1):
            print(f"{i}) {browser.name} — {browser.executable}")
        print("0) Voltar")

        choice = prompt("\nOpção", "0")
        if choice == "0":
            return
        if not choice.isdigit() or int(choice) < 1 or int(choice) > len(browsers):
            print("\nOpção inválida.")
            pause()
            continue

        browser = browsers[int(choice) - 1]
        result = browser_installer.install_extension(browser)
        print("\n" + result["message"])
        pause()


def open_web_panel() -> None:
    if not daemon_client.is_daemon_online():
        print("\n✘ Daemon offline. Instale ou inicie o serviço primeiro.")
        return
    result = browser_installer.open_web_panel()
    print(f"\n{'✔' if result['success'] else '✘'} {result['message']}")


def list_credentials() -> None:
    creds = credentials_client.list_credentials()
    mode = "API (daemon ativo)" if credentials_client.is_online() else "offline (reinicie o daemon após alterações)"
    print(f"\nModo: {mode}\n")
    if not creds:
        print("Nenhuma credencial cadastrada.")
        return
    for i, cred in enumerate(creds, 1):
        print(
            f"{i}) {cred.get('username', '?')} @ {cred.get('rpId', '?')} "
            f"[{cred.get('algorithm', '?')}, count={cred.get('signCount', 0)}]"
        )


def import_credential() -> None:
    print("\n--- Importar credencial ---")
    try:
        pem = credentials_client.read_pem_file(prompt("Caminho do arquivo PEM"))
        credentials_client.import_credential(
            credential_id=prompt("Credential ID"),
            rp_id=prompt("RP ID", "github.com"),
            user_handle=prompt("User Handle"),
            username=prompt("Username"),
            private_key_pem=pem,
            algorithm=prompt("Algoritmo (ES256/RS256/EdDSA)", "ES256"),
        )
        print("\n✔ Credencial importada.")
    except CredentialsError as e:
        print(f"\n✘ {e}")


def generate_credential() -> None:
    print("\n--- Gerar nova credencial ---")
    try:
        result = credentials_client.generate_credential(
            rp_id=prompt("RP ID", "github.com"),
            user_handle=prompt("User Handle"),
            username=prompt("Username"),
            algorithm=prompt("Algoritmo (ES256/RS256/EdDSA)", "ES256"),
        )
        print("\n✔ Credencial gerada.")
        print(f"ID: {result.get('credentialId', '')}")
        if result.get("privateKeyPem"):
            print("\nGuarde a chave privada (PEM) em local seguro.")
    except CredentialsError as e:
        print(f"\n✘ {e}")


def edit_credential() -> None:
    creds = credentials_client.list_credentials()
    if not creds:
        print("\nNenhuma credencial para editar.")
        return
    list_credentials()
    choice = prompt("\nNúmero da credencial (0 = cancelar)", "0")
    if choice == "0" or not choice.isdigit():
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(creds):
        print("\nOpção inválida.")
        return

    cred = creds[idx]
    print(f"\nEditando: {cred.get('username', '?')}")
    try:
        credentials_client.update_credential(
            cred["credentialId"],
            {
                "rpId": prompt("RP ID", cred.get("rpId", "")),
                "username": prompt("Username", cred.get("username", "")),
                "userHandle": prompt("User Handle", cred.get("userHandle", "")),
                "signCount": int(prompt("Sign Count", str(cred.get("signCount", 0)))),
                "backupEligible": cred.get("backupEligible", True),
                "backupState": cred.get("backupState", True),
                "isSynced": cred.get("isSynced", True),
            },
        )
        print("\n✔ Credencial atualizada.")
    except (CredentialsError, ValueError) as e:
        print(f"\n✘ {e}")


def delete_credential() -> None:
    creds = credentials_client.list_credentials()
    if not creds:
        print("\nNenhuma credencial para excluir.")
        return
    list_credentials()
    choice = prompt("\nNúmero da credencial (0 = cancelar)", "0")
    if choice == "0" or not choice.isdigit():
        return
    idx = int(choice) - 1
    if idx < 0 or idx >= len(creds):
        print("\nOpção inválida.")
        return

    cred = creds[idx]
    if prompt(f"Excluir {cred.get('username', '?')}? (s/N)", "n").lower() != "s":
        return
    try:
        credentials_client.delete_credential(cred["credentialId"])
        print("\n✔ Credencial excluída.")
    except CredentialsError as e:
        print(f"\n✘ {e}")


def credentials_menu() -> None:
    while True:
        clear()
        print("=== Gerenciar chaves FIDO2 ===\n")
        print(status_line(), "\n")
        print("1) Listar")
        print("2) Importar")
        print("3) Gerar nova")
        print("4) Editar")
        print("5) Excluir")
        print("6) Abrir painel web")
        print("0) Voltar")
        choice = prompt("\nOpção", "0")

        if choice == "0":
            return
        if choice == "1":
            list_credentials()
        elif choice == "2":
            import_credential()
        elif choice == "3":
            generate_credential()
        elif choice == "4":
            edit_credential()
        elif choice == "5":
            delete_credential()
        elif choice == "6":
            open_web_panel()
        else:
            print("\nOpção inválida.")

        pause()


def main_menu() -> None:
    while True:
        clear()
        print("=== Virtual FIDO2 — Gerenciador ===\n")
        print(status_line(), "\n")
        print("1) Instalar serviço")
        print("2) Gerenciar serviço")
        print("3) Instalar extensão no navegador")
        print("4) Abrir painel web")
        print("5) Gerenciar chaves FIDO2")
        print("0) Sair")
        choice = prompt("\nOpção", "0")

        if choice == "0":
            clear()
            print("Até logo!")
            return
        if choice == "1":
            install_service()
            pause()
        elif choice == "2":
            service_menu()
        elif choice == "3":
            browser_menu()
        elif choice == "4":
            open_web_panel()
            pause()
        elif choice == "5":
            credentials_menu()
        else:
            print("\nOpção inválida.")
            pause()


def run() -> None:
    try:
        main_menu()
    except KeyboardInterrupt:
        clear()
        print("\nEncerrado.")
