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
            print("\n=========== 玩家主選單（未登入） ===========")
            print("1. 註冊帳號")
            print("2. 登入")
            print("0. 離開程式")
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
                print("無效選項。")

    def after_login_menu(self):
        username = self.auth.username
        assert username is not None
        store = GameStoreClient(self.sock, username)
        library = GameLibrary(username)
        lobby = LobbyClient(self.sock, username)
        review = ReviewClient(self.sock, username)

        while True:
            print("\n=========== 玩家主選單（已登入） ===========")
            print(f"目前帳號：{username}")
            print("1. 瀏覽遊戲商城（下載遊戲）")
            print("2. 我的遊戲庫")
            print("3. 進入遊戲大廳")
            print("4. 對遊戲評分與留言")
            print("0. 登出")
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
                print("已登出。")
                self.logged_in = False
                return
            else:
                print("無效選項。")
