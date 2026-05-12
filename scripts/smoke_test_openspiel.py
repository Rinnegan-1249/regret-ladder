from __future__ import annotations

import pyspiel


def main() -> None:
    print("OpenSpiel imported successfully.")
    for game_name in ["kuhn_poker", "leduc_poker"]:
        game = pyspiel.load_game(game_name)
        print(
            f"Loaded {game_name}: "
            f"players={game.num_players()}, actions={game.num_distinct_actions()}"
        )


if __name__ == "__main__":
    main()
