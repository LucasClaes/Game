import os
import pygame
from core.settings import SCREEN_W, SCREEN_H, FPS
from core.state_machine import StateManager, GameState
from core.save import load_save, write_save

_RELOAD_FLAG = os.path.join(os.path.dirname(__file__), "..", "data", ".dev_reload")


class Game:
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        try:
            pygame.mixer.init()
            from systems.audio import audio
            audio.load()
        except Exception:
            pass
        pygame.display.set_caption("Zombie Maze")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN | pygame.SCALED)
        self.clock = pygame.time.Clock()

        font       = pygame.font.Font(None, 22)
        big_font   = pygame.font.Font(None, 30)
        title_font = pygame.font.Font(None, 68)

        self.state_manager = StateManager()
        player_data = load_save()

        # Apply saved volume preferences
        try:
            from systems.audio import audio
            audio.set_music_volume(player_data.get("music_vol", 0.4))
            audio.set_sfx_volume(player_data.get("sfx_vol", 1.0))
        except Exception:
            pass

        from ui.main_menu import MainMenuScreen
        from ui.playing import PlayingScreen
        from ui.shop import ShopScreen
        from ui.game_over import GameOverScreen
        from ui.level_complete import LevelCompleteScreen
        from ui.settings import SettingsScreen
        from ui.achievements import AchievementsScreen
        from ui.codex import CodexScreen

        args = (self.state_manager, font, big_font, title_font)
        self.state_manager.register(GameState.MAIN_MENU,      MainMenuScreen(*args))
        self.state_manager.register(GameState.PLAYING,        PlayingScreen(*args))
        self.state_manager.register(GameState.SHOP,           ShopScreen(*args))
        self.state_manager.register(GameState.GAME_OVER,      GameOverScreen(*args))
        self.state_manager.register(GameState.LEVEL_COMPLETE, LevelCompleteScreen(*args))
        self.state_manager.register(GameState.SETTINGS,       SettingsScreen(*args))
        self.state_manager.register(GameState.ACHIEVEMENTS,   AchievementsScreen(*args))
        self.state_manager.register(GameState.CODEX,          CodexScreen(*args))

        self.state_manager.switch_to(GameState.MAIN_MENU, player_data=player_data)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False

            try:
                from systems.audio import audio
                audio.update(dt)
            except Exception:
                pass

            if os.path.exists(_RELOAD_FLAG):
                try:
                    os.remove(_RELOAD_FLAG)
                    new_data = load_save()
                    self.state_manager.dev_reload(new_data)
                except Exception:
                    pass

            self.state_manager.update(events, dt)
            self.state_manager.draw(self.screen)
            pygame.display.flip()

        pygame.quit()
