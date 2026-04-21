import pygame
from core.settings import SCREEN_W, SCREEN_H, FPS
from core.state_machine import StateManager, GameState
from core.save import load_save, write_save


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Zombie Maze")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()

        font       = pygame.font.Font(None, 22)
        big_font   = pygame.font.Font(None, 30)
        title_font = pygame.font.Font(None, 68)

        self.state_manager = StateManager()
        player_data = load_save()

        from ui.main_menu import MainMenuScreen
        from ui.playing import PlayingScreen
        from ui.shop import ShopScreen
        from ui.game_over import GameOverScreen
        from ui.level_complete import LevelCompleteScreen

        args = (self.state_manager, font, big_font, title_font)
        self.state_manager.register(GameState.MAIN_MENU,      MainMenuScreen(*args))
        self.state_manager.register(GameState.PLAYING,        PlayingScreen(*args))
        self.state_manager.register(GameState.SHOP,           ShopScreen(*args))
        self.state_manager.register(GameState.GAME_OVER,      GameOverScreen(*args))
        self.state_manager.register(GameState.LEVEL_COMPLETE, LevelCompleteScreen(*args))

        self.state_manager.switch_to(GameState.MAIN_MENU, player_data=player_data)

    async def run(self):
        import asyncio
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)  # cap delta time to avoid spiral of death

            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False

            self.state_manager.update(events, dt)
            self.state_manager.draw(self.screen)
            pygame.display.flip()

            await asyncio.sleep(0)

        pygame.quit()
