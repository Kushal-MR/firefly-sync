"""Live pygame window: drones flashing on a floor plan, plus a sync graph.

Reads the session and draws it. Never changes the swarm and never advances
time - the session owns that.

Keys:  SPACE pause   R scramble the virtual drones   L show radio links   ESC quit
"""
import math

import pygame

BG = (10, 14, 28)
FLOOR = (18, 24, 44)
GRID = (28, 36, 62)
DIM = (70, 82, 120)
TEXT = (220, 226, 240)
MUTED = (130, 140, 170)
FLASH = (255, 214, 64)
GLOW = (255, 190, 40)
REAL = (64, 220, 160)
LINK = (40, 52, 90)
GOOD, OK, BAD = (64, 220, 140), (255, 190, 60), (240, 90, 90)

PANEL_W = 380


class View:
    def __init__(self, width=1280, height=720, title="firefly-sync"):
        pygame.init()
        pygame.display.set_caption(title)
        self.screen = pygame.display.set_mode((width, height))
        self.w, self.h = width, height
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas,dejavusansmono,monospace", 18)
        self.small = pygame.font.SysFont("consolas,dejavusansmono,monospace", 14)
        self.big = pygame.font.SysFont("consolas,dejavusansmono,monospace", 40, bold=True)
        self.show_links = False

    # ----- input -------------------------------------------------------------
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    return "quit"
                if e.key == pygame.K_SPACE:
                    return "pause"
                if e.key == pygame.K_r:
                    return "scramble"
                if e.key == pygame.K_l:
                    self.show_links = not self.show_links
        return None

    # ----- drawing -----------------------------------------------------------
    def _floor_rect(self):
        m = 30
        return pygame.Rect(m, m, self.w - PANEL_W - 2 * m, self.h - 2 * m)

    def _to_screen(self, pos, area, rect):
        x, y = pos
        return (rect.x + 20 + x / area[0] * (rect.w - 40),
                rect.y + 20 + y / area[1] * (rect.h - 40))

    def _drone(self, centre, colour, size=9):
        cx, cy = centre
        arm = size * 1.3
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            end = (cx + dx * arm, cy + dy * arm)
            pygame.draw.line(self.screen, colour, centre, end, 2)
            pygame.draw.circle(self.screen, colour, (int(end[0]), int(end[1])), max(3, size // 2), 1)
        pygame.draw.circle(self.screen, colour, (int(cx), int(cy)), max(3, size // 2))

    def draw(self, session):
        sw = session.swarm
        self.screen.fill(BG)
        rect = self._floor_rect()
        pygame.draw.rect(self.screen, FLOOR, rect, border_radius=12)
        for i in range(1, 10):
            x = rect.x + i * rect.w / 10
            pygame.draw.line(self.screen, GRID, (x, rect.y + 8), (x, rect.bottom - 8))
        for i in range(1, 6):
            y = rect.y + i * rect.h / 6
            pygame.draw.line(self.screen, GRID, (rect.x + 8, y), (rect.right - 8, y))

        pts = [self._to_screen(p, sw.area, rect) for p in sw.positions]

        if self.show_links:
            for i, near in enumerate(sw.neighbours):
                for j in near:
                    if j > i:
                        pygame.draw.line(self.screen, LINK, pts[i], pts[j], 1)

        for i, p in enumerate(pts):
            is_real = i in sw.external_names
            lit = session.is_flashing(i)
            if lit:
                glow = pygame.Surface((80, 80), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*GLOW, 70), (40, 40), 38)
                pygame.draw.circle(glow, (*GLOW, 120), (40, 40), 22)
                self.screen.blit(glow, (p[0] - 40, p[1] - 40))
            colour = FLASH if lit else (REAL if is_real else DIM)
            self._drone(p, colour, size=13 if is_real else 9)
            if is_real:
                pygame.draw.circle(self.screen, REAL, (int(p[0]), int(p[1])), 30, 2)
                label = self.small.render("ESP32 (real)", True, REAL)
                self.screen.blit(label, (p[0] - label.get_width() / 2, p[1] + 34))

        self._panel(session)
        pygame.display.flip()
        self.clock.tick(60)

    def _panel(self, session):
        x0 = self.w - PANEL_W
        pygame.draw.rect(self.screen, (14, 20, 38), (x0, 0, PANEL_W, self.h))
        x, y = x0 + 24, 28
        self.screen.blit(self.font.render("FIREFLY SYNC", True, MUTED), (x, y))
        y += 40

        lvl = session.sync_level()
        colour = GOOD if lvl > 0.95 else OK if lvl > 0.7 else BAD
        self.screen.blit(self.small.render("Swarm sync level", True, MUTED), (x, y))
        y += 20
        self.screen.blit(self.big.render(f"{100 * lvl:5.1f}%", True, colour), (x, y))
        y += 60

        sw = session.swarm
        rows = [("Time", f"{sw.time:6.1f} s"),
                ("Virtual drones", str(sw.n_virtual)),
                ("Coupling", f"{sw.oscillators[0].coupling:.2f}"),
                ("Radio range", "all" if sw.radio_range is None else f"{sw.radio_range:g} m")]
        if session.ext is not None:
            off = session.esp32_offset()
            heard = session.link and session.link.last_heard is not None
            if not heard:
                rows.append(("ESP32", "waiting..."))
            else:
                rows.append(("ESP32 off-beat", f"{off:+.0f} ms" if off is not None else "-"))
        for k, v in rows:
            self.screen.blit(self.small.render(k, True, MUTED), (x, y))
            vc = TEXT
            if k == "ESP32 off-beat" and session.esp32_offset() is not None:
                a = abs(session.esp32_offset())
                vc = GOOD if a < 30 else OK if a < 100 else BAD
            self.screen.blit(self.font.render(v, True, vc), (x + 170, y - 2))
            y += 28

        y += 16
        self._graph(session, pygame.Rect(x, y, PANEL_W - 48, 170))
        y += 190
        if session.paused:
            self.screen.blit(self.font.render("PAUSED", True, OK), (x, y))
            y += 28
        for line in ("SPACE pause   R scramble", "L radio links   ESC quit"):
            self.screen.blit(self.small.render(line, True, MUTED), (x, self.h - 60 + (20 if line[0] == "L" else 0)))

    def _graph(self, session, r):
        pygame.draw.rect(self.screen, (20, 28, 52), r, border_radius=6)
        self.screen.blit(self.small.render("sync level, last 30 s", True, MUTED), (r.x + 8, r.y + 6))
        hist = list(session.history)
        if len(hist) < 2:
            return
        t_end = hist[-1][0]
        t_start = t_end - 30
        top, bot = r.y + 28, r.bottom - 10
        pygame.draw.line(self.screen, GRID, (r.x + 8, top), (r.right - 8, top))
        pts = []
        for t, lvl in hist:
            if t < t_start:
                continue
            px = r.x + 8 + (t - t_start) / 30 * (r.w - 16)
            py = bot - lvl * (bot - top)
            pts.append((px, py))
        if len(pts) > 1:
            pygame.draw.lines(self.screen, FLASH, False, pts, 2)

    def save_screenshot(self, path):
        pygame.image.save(self.screen, path)

    def close(self):
        pygame.quit()
