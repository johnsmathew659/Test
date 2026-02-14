"""Classic Snake game with GUI and optional headless mode.

Run GUI (default):
    python snake_game.py

Run headless simulation:
    python snake_game.py --headless --steps 200
"""

from __future__ import annotations

import argparse
import json
import random
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path


SCORES_FILE = Path(__file__).with_name("snake_scores.json")


@dataclass(frozen=True)
class Point:
    x: int
    y: int


class ScoreBoard:
    def __init__(self, path: Path, keep: int = 10) -> None:
        self.path = path
        self.keep = keep
        self.scores = self._load()

    def _load(self) -> list[int]:
        if not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            values = [int(v) for v in data if isinstance(v, int) or (isinstance(v, str) and v.isdigit())]
            values.sort(reverse=True)
            return values[: self.keep]
        except (OSError, json.JSONDecodeError, ValueError):
            return []

    def _save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.scores, indent=2), encoding="utf-8")
        except OSError:
            pass

    def add(self, score: int) -> None:
        if score < 0:
            return
        self.scores.append(score)
        self.scores.sort(reverse=True)
        self.scores = self.scores[: self.keep]
        self._save()

    def clear(self) -> None:
        self.scores = []
        self._save()

    def best(self) -> int:
        return self.scores[0] if self.scores else 0


class SnakeEngine:
    """Game rules/state that can run with or without a GUI."""

    GRID_WIDTH = 28
    GRID_HEIGHT = 20
    START_DELAY_MS = 140
    MIN_DELAY_MS = 65
    SPEEDUP_EVERY = 4
    SPEED_STEP_MS = 7

    def __init__(self, wrap_walls: bool = True, speed_factor: float = 1.0) -> None:
        self.wrap_walls = wrap_walls
        self.speed_factor = max(0.25, min(speed_factor, 3.0))
        self.reset_state()

    def reset_state(self) -> None:
        cx, cy = self.GRID_WIDTH // 2, self.GRID_HEIGHT // 2
        self.snake = [Point(cx, cy), Point(cx - 1, cy), Point(cx - 2, cy)]
        self.direction = (1, 0)
        self.pending_direction = self.direction
        self.food = self.spawn_food()
        self.score = 0
        self.running = False
        self.game_over = False
        self._base_tick_delay = int(self.START_DELAY_MS / self.speed_factor)
        self.tick_delay = self._base_tick_delay

    def start(self) -> None:
        if not self.game_over:
            self.running = True

    def stop(self) -> None:
        self.running = False

    def set_speed_factor(self, factor: float) -> None:
        self.speed_factor = max(0.25, min(factor, 3.0))
        score_steps = self.score // self.SPEEDUP_EVERY
        self._base_tick_delay = int(self.START_DELAY_MS / self.speed_factor)
        self.tick_delay = max(
            int(self.MIN_DELAY_MS / self.speed_factor),
            self._base_tick_delay - score_steps * self.SPEED_STEP_MS,
        )

    def set_direction(self, dx: int, dy: int) -> None:
        if self.game_over:
            return
        curr_dx, curr_dy = self.direction
        if (dx, dy) == (-curr_dx, -curr_dy):
            return
        self.pending_direction = (dx, dy)

    def spawn_food(self) -> Point:
        occupied = set(self.snake)
        while True:
            p = Point(
                random.randint(0, self.GRID_WIDTH - 1),
                random.randint(0, self.GRID_HEIGHT - 1),
            )
            if p not in occupied:
                return p

    def _wrap(self, p: Point) -> Point:
        return Point(p.x % self.GRID_WIDTH, p.y % self.GRID_HEIGHT)

    def step(self) -> bool:
        if not self.running:
            return not self.game_over

        self.direction = self.pending_direction
        head = self.snake[0]
        candidate = Point(head.x + self.direction[0], head.y + self.direction[1])
        new_head = self._wrap(candidate) if self.wrap_walls else candidate

        if (not self.wrap_walls and (new_head.x < 0 or new_head.x >= self.GRID_WIDTH or new_head.y < 0 or new_head.y >= self.GRID_HEIGHT)) or new_head in self.snake:
            self.running = False
            self.game_over = True
            return False

        self.snake.insert(0, new_head)

        if new_head == self.food:
            self.score += 1
            self.food = self.spawn_food()
            if self.score % self.SPEEDUP_EVERY == 0:
                self.tick_delay = max(
                    int(self.MIN_DELAY_MS / self.speed_factor),
                    self.tick_delay - self.SPEED_STEP_MS,
                )
        else:
            self.snake.pop()

        return True


class SnakeGUI:
    CELL_SIZE = 28
    BACKGROUND = "#111827"
    GRID_COLOR = "#1F2937"
    SNAKE_HEAD = "#34D399"
    SNAKE_BODY = "#10B981"
    SNAKE_TAIL = "#059669"
    FOOD_COLOR = "#F87171"
    PANEL_BG = "#0B1220"
    TEXT_COLOR = "#E5E7EB"
    ACCENT = "#60A5FA"

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.engine = SnakeEngine(wrap_walls=True)
        self.scores = ScoreBoard(SCORES_FILE)

        self.root.title("Snake")
        self.root.configure(bg=self.PANEL_BG)
        self.root.resizable(False, False)

        self.canvas_width = self.engine.GRID_WIDTH * self.CELL_SIZE
        self.canvas_height = self.engine.GRID_HEIGHT * self.CELL_SIZE

        frame = tk.Frame(root, bg=self.PANEL_BG, padx=18, pady=18)
        frame.pack()

        title = tk.Label(
            frame,
            text="🐍 Classic Snake",
            font=("Segoe UI", 22, "bold"),
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
            pady=8,
        )
        title.grid(row=0, column=0, columnspan=2, sticky="w")

        self.canvas = tk.Canvas(
            frame,
            width=self.canvas_width,
            height=self.canvas_height,
            bg=self.BACKGROUND,
            highlightthickness=0,
        )
        self.canvas.grid(row=1, column=0, rowspan=6, padx=(0, 16))

        sidebar = tk.Frame(frame, bg=self.PANEL_BG)
        sidebar.grid(row=1, column=1, sticky="n")

        self.score_var = tk.StringVar(value="Score: 0")
        self.best_var = tk.StringVar(value=f"Best: {self.scores.best()}")
        self.state_var = tk.StringVar(value="Press SPACE or Start")
        self.speed_var = tk.DoubleVar(value=1.0)

        self._info_label(sidebar, self.score_var, 0)
        self._info_label(sidebar, self.best_var, 1)
        self._info_label(sidebar, self.state_var, 2, wrap=210)

        controls = tk.Label(
            sidebar,
            text="Controls\n↑ ↓ ← → or WASD\nSPACE = start/pause",
            font=("Segoe UI", 11),
            justify="left",
            bg=self.PANEL_BG,
            fg="#9CA3AF",
            pady=14,
        )
        controls.grid(row=3, column=0, sticky="w")

        speed_label = tk.Label(
            sidebar,
            text="Speed",
            font=("Segoe UI", 11, "bold"),
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
        )
        speed_label.grid(row=4, column=0, sticky="w", pady=(2, 0))

        speed_scale = tk.Scale(
            sidebar,
            from_=0.5,
            to=2.5,
            resolution=0.1,
            orient="horizontal",
            length=190,
            variable=self.speed_var,
            command=self.on_speed_change,
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
            troughcolor="#374151",
            highlightthickness=0,
        )
        speed_scale.grid(row=5, column=0, sticky="w")

        self.start_stop_btn = self._btn(sidebar, "Start", self.toggle_running, row=6, col=0)
        self.restart_btn = self._btn(sidebar, "Restart", self.restart, row=7, col=0)
        self.clear_scores_btn = self._btn(sidebar, "Clear Top Scores", self.clear_scores, row=8, col=0)

        top_title = tk.Label(
            sidebar,
            text="Top Scores",
            font=("Segoe UI", 11, "bold"),
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
            pady=8,
        )
        top_title.grid(row=9, column=0, sticky="w")

        self.top_scores_text = tk.Text(
            sidebar,
            width=24,
            height=8,
            bg="#111827",
            fg="#D1D5DB",
            relief="flat",
            font=("Consolas", 10),
        )
        self.top_scores_text.grid(row=10, column=0, sticky="w")
        self.top_scores_text.configure(state="disabled")

        self.after_id: str | None = None
        self.refresh_top_scores()
        self.bind_keys()
        self.draw()

    def _btn(self, parent: tk.Widget, text: str, command, row: int, col: int) -> tk.Button:
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10, "bold"),
            bg=self.ACCENT,
            fg="#0B1220",
            activebackground="#93C5FD",
            activeforeground="#0B1220",
            relief="flat",
            padx=12,
            pady=7,
            cursor="hand2",
        )
        btn.grid(row=row, column=col, sticky="w", pady=3)
        return btn

    def _info_label(self, parent: tk.Widget, var: tk.StringVar, row: int, wrap: int = 0) -> None:
        label = tk.Label(
            parent,
            textvariable=var,
            font=("Segoe UI", 13, "bold") if row < 2 else ("Segoe UI", 12),
            bg=self.PANEL_BG,
            fg=self.TEXT_COLOR,
            pady=5,
            wraplength=wrap,
            justify="left",
        )
        label.grid(row=row, column=0, sticky="w")

    def bind_keys(self) -> None:
        self.root.bind("<Up>", lambda _: self.set_direction(0, -1))
        self.root.bind("<Down>", lambda _: self.set_direction(0, 1))
        self.root.bind("<Left>", lambda _: self.set_direction(-1, 0))
        self.root.bind("<Right>", lambda _: self.set_direction(1, 0))
        self.root.bind("w", lambda _: self.set_direction(0, -1))
        self.root.bind("s", lambda _: self.set_direction(0, 1))
        self.root.bind("a", lambda _: self.set_direction(-1, 0))
        self.root.bind("d", lambda _: self.set_direction(1, 0))
        self.root.bind("<space>", lambda _: self.toggle_running())

    def on_speed_change(self, _: str) -> None:
        self.engine.set_speed_factor(self.speed_var.get())

    def set_direction(self, dx: int, dy: int) -> None:
        self.engine.set_direction(dx, dy)
        if not self.engine.running and not self.engine.game_over:
            self.start_game()

    def start_game(self) -> None:
        self.engine.start()
        self.start_stop_btn.configure(text="Pause")
        self.state_var.set("Running...")
        if self.after_id is None:
            self.tick()

    def pause_game(self) -> None:
        self.engine.stop()
        self.start_stop_btn.configure(text="Start")
        self.state_var.set("Paused")
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def toggle_running(self) -> None:
        if self.engine.game_over:
            self.restart()
        if self.engine.running:
            self.pause_game()
        else:
            self.start_game()

    def restart(self) -> None:
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        self.engine.reset_state()
        self.engine.set_speed_factor(self.speed_var.get())
        self.score_var.set("Score: 0")
        self.best_var.set(f"Best: {self.scores.best()}")
        self.state_var.set("Press SPACE or Start")
        self.start_stop_btn.configure(text="Start")
        self.draw()

    def clear_scores(self) -> None:
        self.scores.clear()
        self.best_var.set("Best: 0")
        self.refresh_top_scores()

    def refresh_top_scores(self) -> None:
        lines = [f"{i+1:>2}. {s}" for i, s in enumerate(self.scores.scores)]
        if not lines:
            lines = ["No scores yet."]

        self.top_scores_text.configure(state="normal")
        self.top_scores_text.delete("1.0", "end")
        self.top_scores_text.insert("end", "\n".join(lines))
        self.top_scores_text.configure(state="disabled")

    def tick(self) -> None:
        self.after_id = None
        ongoing = self.engine.step()
        self.score_var.set(f"Score: {self.engine.score}")

        if not ongoing:
            self.scores.add(self.engine.score)
            self.best_var.set(f"Best: {self.scores.best()}")
            self.refresh_top_scores()
            self.state_var.set("Game over — press Start/SPACE")
            self.start_stop_btn.configure(text="Start")
            self.draw()
            return

        self.draw()
        if self.engine.running:
            self.after_id = self.root.after(self.engine.tick_delay, self.tick)

    def draw(self) -> None:
        self.canvas.delete("all")

        for x in range(0, self.canvas_width + 1, self.CELL_SIZE):
            self.canvas.create_line(x, 0, x, self.canvas_height, fill=self.GRID_COLOR)
        for y in range(0, self.canvas_height + 1, self.CELL_SIZE):
            self.canvas.create_line(0, y, self.canvas_width, y, fill=self.GRID_COLOR)

        fx, fy = self.engine.food.x * self.CELL_SIZE, self.engine.food.y * self.CELL_SIZE
        self.canvas.create_oval(
            fx + 5,
            fy + 5,
            fx + self.CELL_SIZE - 5,
            fy + self.CELL_SIZE - 5,
            fill=self.FOOD_COLOR,
            outline="",
        )

        snake = self.engine.snake
        for i, part in enumerate(snake):
            x1 = part.x * self.CELL_SIZE + 3
            y1 = part.y * self.CELL_SIZE + 3
            x2 = x1 + self.CELL_SIZE - 6
            y2 = y1 + self.CELL_SIZE - 6

            if i == 0:
                self.canvas.create_oval(x1, y1, x2, y2, fill=self.SNAKE_HEAD, outline="")
                self._draw_eyes(part)
            elif i == len(snake) - 1:
                self.canvas.create_oval(x1 + 4, y1 + 4, x2 - 4, y2 - 4, fill=self.SNAKE_TAIL, outline="")
            else:
                self.canvas.create_oval(x1, y1, x2, y2, fill=self.SNAKE_BODY, outline="")

        if self.engine.game_over:
            self.canvas.create_rectangle(
                0,
                self.canvas_height // 2 - 46,
                self.canvas_width,
                self.canvas_height // 2 + 46,
                fill="#000000",
                stipple="gray50",
                outline="",
            )
            self.canvas.create_text(
                self.canvas_width // 2,
                self.canvas_height // 2 - 10,
                text="Game Over",
                font=("Segoe UI", 28, "bold"),
                fill="#F9FAFB",
            )
            self.canvas.create_text(
                self.canvas_width // 2,
                self.canvas_height // 2 + 24,
                text="Start or SPACE to restart",
                font=("Segoe UI", 14),
                fill="#D1D5DB",
            )

    def _draw_eyes(self, head: Point) -> None:
        dx, dy = self.engine.direction
        base_x = head.x * self.CELL_SIZE
        base_y = head.y * self.CELL_SIZE

        if dx == 1:
            eyes = [(20, 9), (20, 18)]
        elif dx == -1:
            eyes = [(8, 9), (8, 18)]
        elif dy == 1:
            eyes = [(9, 20), (18, 20)]
        else:
            eyes = [(9, 8), (18, 8)]

        for ex, ey in eyes:
            self.canvas.create_oval(
                base_x + ex,
                base_y + ey,
                base_x + ex + 4,
                base_y + ey + 4,
                fill="#111827",
                outline="",
            )


def run_headless(steps: int, seed: int | None = None, speed: float = 1.0) -> None:
    if seed is not None:
        random.seed(seed)

    engine = SnakeEngine(wrap_walls=True, speed_factor=speed)
    engine.start()

    directions = [(1, 0), (0, 1), (-1, 0), (0, -1)]
    for _ in range(steps):
        if engine.game_over:
            break

        head = engine.snake[0]
        preferred: list[tuple[int, int]] = []
        if engine.food.x > head.x:
            preferred.append((1, 0))
        elif engine.food.x < head.x:
            preferred.append((-1, 0))
        if engine.food.y > head.y:
            preferred.append((0, 1))
        elif engine.food.y < head.y:
            preferred.append((0, -1))

        for d in directions:
            if d not in preferred:
                preferred.append(d)

        for dx, dy in preferred:
            nx = (head.x + dx) % engine.GRID_WIDTH
            ny = (head.y + dy) % engine.GRID_HEIGHT
            if Point(nx, ny) not in engine.snake:
                engine.set_direction(dx, dy)
                break

        engine.step()

    status = "GAME_OVER" if engine.game_over else "RUNNING"
    print(f"headless_status={status} score={engine.score} length={len(engine.snake)} steps={steps}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classic Snake game (GUI or headless mode).")
    parser.add_argument("--headless", action="store_true", help="Run without GUI using an auto-player.")
    parser.add_argument("--steps", type=int, default=200, help="Steps to run in headless mode.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for headless reproducibility.")
    parser.add_argument("--speed", type=float, default=1.0, help="Speed multiplier (0.5 to 2.5+).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.headless:
        run_headless(steps=args.steps, seed=args.seed, speed=args.speed)
        return

    root = tk.Tk()
    SnakeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
