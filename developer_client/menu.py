# path: developer_client/menu.py
from .auth import DeveloperAuth
from .game_upload import GameUploader
from .game_manage import GameManagerClient


class DeveloperMenu:
    def __init__(self, sock):
        self.sock = sock
        self.auth = DeveloperAuth(sock)
        self.logged_in = False

    def run(self):
        while True:
            print("\n=========== Developer Menu ===========")
            print("1. Register")
            print("2. Login")
            print("0. Exit")
            choice = input("> ")

            if choice == "1":
                self.auth.register()
            elif choice == "2":
                if self.auth.login():
                    self.logged_in = True
                    self.after_login_menu()
            elif choice == "0":
                print("Bye!")
                return

    def after_login_menu(self):
        manager = GameManagerClient(self.sock, self.auth.username)
        uploader = GameUploader(self.sock, self.auth.username)

        while True:
            print("\n========== Developer Dashboard ==========")
            print("1. Upload new game")
            print("2. Update existing game")
            print("3. List my games")
            print("0. Logout")
            choice = input("> ")

            if choice == "1":
                uploader.upload_game()
            elif choice == "2":
                manager.update_game()
            elif choice == "3":
                manager.list_my_games()
            elif choice == "0":
                print("Logged out.")
                return
