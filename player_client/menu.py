# path: player_client/menu.py
import socket

from .auth import PlayerAuth
from .store import GameStoreClient
from .library import GameLibrary
from .lobby import LobbyClient
from .review import ReviewClient


class PlayerMenu:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.auth = PlayerAuth(sock)
        self.logged_in = False

    def run(self):
        while True:
            try:
                print("\n=========== Player Menu (Not Logged In) ===========")
                print("1. Register")
                print("2. Login")
                print("0. Exit")
                choice = input("> ").strip()

                if choice == "1":
                    self.auth.register()
                elif choice == "2":
                    if self.auth.login():
                        self.logged_in = True
                        self.after_login_menu()
                elif choice == "0":
                    print("Bye!")
                    return
                else:
                    print("Invalid option.")
            except EOFError:
                print("\nBye!")
                return

    def after_login_menu(self):
        username = self.auth.username
        assert username is not None
        store = GameStoreClient(self.sock, username)
        library = GameLibrary(username)
        lobby = LobbyClient(self.sock, username)
        review = ReviewClient(self.sock, username)

        while True:
            try:
                print("\n=========== Player Menu (Logged In) ===========")
                print(f"Current user: {username}")
                print("1. Browse Game Store")
                print("2. My Game Library")
                print("3. Enter Game Lobby")
                print("4. Rate & Review Games")
                print("0. Logout")
                choice = input("> ").strip()

                if choice == "1":
                    store.view_store()
                elif choice == "2":
                    library.show_library()
                elif choice == "3":
                    lobby.lobby_menu()
                elif choice == "4":
                    review.list_games_and_review()
                elif choice == "0":
                    print("Logged out.")
                    self.logged_in = False
                    return
                else:
                    print("Invalid option.")
            except EOFError:
                print("\nLogged out.")
                self.logged_in = False
                return
