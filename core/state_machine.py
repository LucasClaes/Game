from enum import Enum, auto


class GameState(Enum):
    MAIN_MENU = auto()
    PLAYING = auto()
    SHOP = auto()
    GAME_OVER = auto()
    LEVEL_COMPLETE = auto()
    SETTINGS = auto()
    ACHIEVEMENTS = auto()
    CODEX = auto()
    CLASS_SELECT  = "class_select"
    UNLOCK_TREE   = "unlock_tree"


class StateManager:
    def __init__(self):
        self._screens = {}
        self._current = None
        self._state = None

    def register(self, state: GameState, screen):
        self._screens[state] = screen

    def switch_to(self, state: GameState, **kwargs):
        self._state = state
        self._current = self._screens[state]
        self._current.on_enter(**kwargs)

    @property
    def current_state(self):
        return self._state

    def update(self, events, dt):
        if self._current:
            self._current.update(events, dt)

    def draw(self, surface):
        if self._current:
            self._current.draw(surface)

    def dev_reload(self, player_data: dict):
        if self._current and hasattr(self._current, '_player_data'):
            self._current._player_data = player_data
        if self._current and hasattr(self._current, '_dev_reload'):
            self._current._dev_reload(player_data)
