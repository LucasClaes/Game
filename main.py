import asyncio
import traceback
import pygame


async def main():
    try:
        from core.game import Game
        game = Game()
        await game.run()
    except Exception:
        # Show the traceback on screen instead of going grey
        tb = traceback.format_exc()
        print(tb)
        try:
            screen = pygame.display.get_surface()
            if not screen:
                pygame.init()
                screen = pygame.display.set_mode((960, 640))
            screen.fill((30, 0, 0))
            font = pygame.font.Font(None, 20)
            lines = tb.replace("\t", "  ").split("\n")
            for i, line in enumerate(lines[:28]):
                surf = font.render(line[:100], True, (255, 200, 200))
                screen.blit(surf, (8, 8 + i * 21))
            pygame.display.flip()
        except Exception:
            pass
        # Keep alive so the error stays visible
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
            await asyncio.sleep(0.1)


asyncio.run(main())
