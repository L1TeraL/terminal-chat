from datetime import datetime

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.panel import Panel
from rich.table import Table


console = Console()


class ChatUI:
    def __init__(self):
        self.session = PromptSession()
        self.username = ""
        self.online_users = []

    def set_username(self, username):
        self.username = username

    def _timestamp(self):
        return datetime.now().strftime("%H:%M:%S")

    def _print(self, *args, **kwargs):
        """
        Safe output while PromptSession is active.

        prompt_toolkit temporarily redraws the prompt after the output,
        so messages from the receiver thread don't corrupt the input line.
        """
        with patch_stdout(raw=True):
            console.print(*args, **kwargs)

    def show_welcome(self):
        self._print()
        self._print(
            Panel(
                "[bold cyan]Welcome to Terminal Chat![/bold cyan]\n\n"
                "A simple TCP terminal chat built with Python.\n\n"
                "[green]/help[/green]  show available commands\n"
                "[green]/online[/green] show online users\n"
                "[green]/quit[/green]  leave the chat",
                title="[bold cyan]TERMINAL CHAT[/bold cyan]",
                border_style="cyan",
                padding=(1, 3),
            )
        )
        self._print()

    def show_connected(self):
        self._print(
            "[bold green]✓[/bold green] "
            "[green]Connected to server.[/green]"
        )

    def show_info(self, message):
        self._print(
            f"[dim]{self._timestamp()}[/dim] "
            f"[bold cyan][SERVER][/bold cyan] "
            f"{message}"
        )

    def show_error(self, message):
        self._print(
            f"[dim]{self._timestamp()}[/dim] "
            f"[bold red][ERROR][/bold red] "
            f"{message}"
        )

    def show_success(self, message):
        self._print(
            f"[dim]{self._timestamp()}[/dim] "
            f"[bold green]✓[/bold green] "
            f"[green]{message}[/green]"
        )

    def show_chat_message(self, message):
        timestamp = self._timestamp()

        if ":" in message:
            username, text = message.split(":", 1)

            self._print(
                f"[dim]{timestamp}[/dim] "
                f"[bold green]{username}[/bold green]:"
                f" {text}"
            )
        else:
            self._print(
                f"[dim]{timestamp}[/dim] "
                f"[bold green]{message}[/bold green]"
            )

    def show_users(self, users):
        self.online_users = users

        table = Table(
            title=f"[bold cyan]Online Users ({len(users)})[/bold cyan]",
            border_style="cyan",
            header_style="bold cyan",
        )

        table.add_column(
            "#",
            justify="center",
            width=4,
        )

        table.add_column(
            "Username",
            style="green",
        )

        for index, user in enumerate(users, start=1):
            marker = "●"

            table.add_row(
                str(index),
                f"{marker} {user}",
            )

        self._print()
        self._print(table)
        self._print()

    def show_help(self):
        table = Table(
            title="[bold cyan]Available Commands[/bold cyan]",
            border_style="cyan",
            header_style="bold cyan",
        )

        table.add_column(
            "Command",
            style="green",
            width=12,
        )

        table.add_column(
            "Description",
        )

        table.add_row(
            "/online",
            "Show online users",
        )

        table.add_row(
            "/help",
            "Show available commands",
        )

        table.add_row(
            "/quit",
            "Leave the chat",
        )

        self._print()
        self._print(table)
        self._print()

    def show_login_success(self, username):
        self.set_username(username)

        self._print()
        self._print(
            Panel(
                f"[bold green]Welcome, {username}![/bold green]\n\n"
                "[dim]You are now connected to the chat.[/dim]",
                title="[bold green]LOGIN SUCCESS[/bold green]",
                border_style="green",
                padding=(1, 3),
            )
        )
        self._print()

    def show_login_failed(self, message):
        self.show_error(message)

    def ask_username(self):
        return self.session.prompt("Username ❯ ").strip()

    def prompt_message(self, stop_event):
        with patch_stdout():
            while not stop_event.is_set():
                try:
                    return self.session.prompt(
                        [
                            ("class:prompt", "You ❯ "),
                        ]
                    ).strip()

                except EOFError:
                    return "/quit"

                except KeyboardInterrupt:
                    return "/quit"

        return None

    def show_goodbye(self):
        self._print()
        self._print(
            Panel(
                "[bold cyan]Thanks for using Terminal Chat![/bold cyan]\n"
                "[dim]Connection closed.[/dim]",
                border_style="cyan",
                padding=(1, 3),
            )
        )
        self._print()

    def show_chat_history(self, history):
        if not history:
            return

        console.print()

        console.print(
            Panel(
                "[bold cyan]Recent messages[/bold cyan]",
                border_style="cyan",
            )
        )

        for message_id, username, message, created_at in history:
            try:
                time = created_at.split(" ")[1]
            except (IndexError, AttributeError):
                time = created_at

            console.print(
                f"[dim]{time}[/dim] "
                f"[bold green]{username}[/bold green]: "
                f"{message}"
            )

        console.print()


ui = ChatUI()