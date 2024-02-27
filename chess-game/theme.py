class Color:
    def __init__(self, light, dark):
        self.light = light
        self.dark = dark


class Theme:
    def __init__(self, light_sq, dark_sq, light_hl, dark_hl, light_moves, dark_moves):

        self.squares = Color(light_sq, dark_sq)
        self.highlights = Color(light_hl, dark_hl)
        self.moves = Color(light_moves, dark_moves)
