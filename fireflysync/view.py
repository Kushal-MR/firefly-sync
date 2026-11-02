"""Live pygame window for the firefly swarm.

Reads the session and draws it. Never changes the swarm and never advances
time - the session owns that.

Every size is designed for a 1280x720 window and multiplied by a scale
factor, so the layout looks the same on any screen: a laptop, a 4K monitor,
or a projector. Resize the window, or press F, and everything rescales.

Keys:  R scramble   SPACE pause   L radio links   F fullscreen
       S save screenshot   ESC quit
"""
import datetime
import math
import os
import sys

import pygame
import pygame.gfxdraw

from fireflysync import metrics

# ---- palette ---------------------------------------------------------------
BG = (10, 14, 24)
CARD = (18, 24, 39)
CARD_2 = (25, 33, 52)
BORDER = (36, 46, 72)
GRID = (26, 34, 54)
GRID_MAJOR = (34, 44, 68)
TEXT = (233, 237, 246)
MUTED = (140, 150, 178)
FAINT = (84, 95, 126)
AMBER = (255, 196, 61)
TEAL = (45, 212, 191)
TEAL_DIM = (34, 110, 104)
GOOD = (52, 211, 153)
WARN = (251, 191, 36)
BAD = (248, 113, 113)
DRONE = (118, 130, 168)

DESIGN_W, DESIGN_H = 1280, 720          # every size below is for this window
SANS = "segoeui,helveticaneue,dejavusans,arial"
MONO = "consolas,menlo,dejavusansmono,monospace"
FONT_SIZES = {                          # name: (family, size at scale 1, bold)
    "title": (SANS, 22, True), "head": (SANS, 15, True), "body": (SANS, 15, False),
    "small": (SANS, 13, False), "tiny": (SANS, 11, True),
    "num": (MONO, 30, True), "big": (MONO, 34, True),
}


def _lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _level_colour(lvl):
    return GOOD if lvl >= 0.95 else WARN if lvl >= 0.7 else BAD


class View:
    def __init__(self, width=None, height=None, title="FireSync"):
        if sys.platform == "win32":                 # sharp text on high-DPI screens
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                pass
        pygame.init()
        pygame.display.set_caption(title)
        if width is None or height is None:
            width, height = self._default_size()
        self.windowed_size = (width, height)
        self.fullscreen = False
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        self.clock = pygame.time.Clock()
        self.show_links = False
        self._scale = None
        self._toasts = []                           # (text, colour, until_wall_time)
        self._seen_sync = None
        self._seen_esp32 = False
        self._shot_request = False
        self._rescale()

    @staticmethod
    def _default_size():
        """About 85% of the screen, keeping a 16:9 shape."""
        info = pygame.display.Info()
        sw, sh = info.current_w, info.current_h
        if not sw or not sh or sw < 800:
            return DESIGN_W, DESIGN_H
        w = int(min(sw * 0.85, sh * 0.85 * 16 / 9))
        return w, int(w * 9 / 16)

    # ----- scaling ------------------------------------------------------------
    def _rescale(self):
        W, H = self.screen.get_size()
        s = round(min(W / DESIGN_W, H / DESIGN_H) * 20) / 20     # steps of 0.05
        s = max(0.75, s)
        if s == self._scale:
            return
        self._scale = s
        self.fonts = {k: pygame.font.SysFont(fam, max(8, round(size * s)), bold=b)
                      for k, (fam, size, b) in FONT_SIZES.items()}
        self._glow_r = self.u(48)
        self._glow = [self._make_glow(self._glow_r, a) for a in range(0, 256, 16)]

    def u(self, x):
        """A design-size length (at 1280x720) in real pixels for this window."""
        return max(1, int(round(x * self._scale)))

    def f(self, name):
        return self.fonts[name]

    # ======================================================================
    # input
    # ======================================================================
    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return "quit"
            if e.type == pygame.VIDEORESIZE and not self.fullscreen:
                self.windowed_size = (max(900, e.w), max(520, e.h))
                self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                self._rescale()
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.fullscreen:
                        self._toggle_fullscreen()
                    else:
                        return "quit"
                if e.key == pygame.K_SPACE:
                    return "pause"
                if e.key == pygame.K_r:
                    self.toast("Scrambled - watch them re-sync", AMBER)
                    return "scramble"
                if e.key == pygame.K_l:
                    self.show_links = not self.show_links
                if e.key == pygame.K_f:
                    self._toggle_fullscreen()
                if e.key == pygame.K_s:
                    self._shot_request = True
        return None

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
        self._rescale()

    def toast(self, text, colour=TEXT, seconds=2.8):
        self._toasts.append((text, colour, pygame.time.get_ticks() / 1000 + seconds))

    # ======================================================================
    # small drawing helpers
    # ======================================================================
    @staticmethod
    def _make_glow(radius, alpha):
        size = radius * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        step = max(1, radius // 24)
        for r in range(radius, 0, -step):
            a = int(alpha * (1 - r / radius) ** 1.8)
            pygame.draw.circle(surf, (*AMBER, a), (radius, radius), r)
        return surf

    def _card(self, rect, title=None, right=None):
        rad = self.u(12)
        pygame.draw.rect(self.screen, CARD, rect, border_radius=rad)
        pygame.draw.rect(self.screen, BORDER, rect, 1, border_radius=rad)
        pad = self.u(16)
        if title:
            self._text(title.upper(), "tiny", MUTED, (rect.x + pad, rect.y + self.u(14)))
        if right:
            self._text(right, "tiny", FAINT, (rect.right - pad, rect.y + self.u(14)), "topright")

    def _text(self, s, font, colour, pos, anchor="topleft"):
        surf = self.f(font).render(s, True, colour)
        r = surf.get_rect(**{anchor: (int(pos[0]), int(pos[1]))})
        self.screen.blit(surf, r)
        return r

    def _aa_circle(self, centre, r, colour, filled=True):
        x, y, r = int(centre[0]), int(centre[1]), max(1, int(r))
        if filled:
            pygame.gfxdraw.filled_circle(self.screen, x, y, r, colour)
        pygame.gfxdraw.aacircle(self.screen, x, y, r, colour)

    @staticmethod
    def _arc_points(centre, r, frac, steps=48):
        """Clockwise from 12 o'clock, `frac` of a full turn."""
        n = max(2, int(steps * frac) + 1)
        return [(centre[0] + r * math.cos(-math.pi / 2 + 2 * math.pi * frac * i / (n - 1)),
                 centre[1] + r * math.sin(-math.pi / 2 + 2 * math.pi * frac * i / (n - 1)))
                for i in range(n)]

    def _thick_arc(self, centre, r, width, frac, colour):
        if frac <= 0.002:
            return
        outer = self._arc_points(centre, r + width / 2, frac, 120)
        inner = self._arc_points(centre, r - width / 2, frac, 120)
        poly = outer + inner[::-1]
        pygame.draw.polygon(self.screen, colour, poly)
        pygame.gfxdraw.aapolygon(self.screen, poly, colour)

    def _ring(self, centre, r, width, colour):
        c = (int(centre[0]), int(centre[1]))
        pygame.draw.circle(self.screen, colour, c, int(r + width / 2), int(width))
        pygame.gfxdraw.aacircle(self.screen, c[0], c[1], int(r + width / 2), colour)
        pygame.gfxdraw.aacircle(self.screen, c[0], c[1], int(r - width / 2), colour)

    def _alpha_line(self, a, b, colour, alpha, width=1):
        if alpha <= 0:
            return
        pad = width + 2
        x0, y0 = int(min(a[0], b[0])) - pad, int(min(a[1], b[1])) - pad
        w, h = int(abs(a[0] - b[0])) + 2 * pad + 1, int(abs(a[1] - b[1])) + 2 * pad + 1
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.line(surf, (*colour, int(alpha)), (a[0] - x0, a[1] - y0), (b[0] - x0, b[1] - y0), width)
        self.screen.blit(surf, (x0, y0))

    def _dashed_circle(self, centre, r, colour, dashes=None):
        if dashes is None:                          # ~7 px dashes at any size
            dashes = max(12, int(2 * math.pi * r / self.u(7)) // 2 * 2)
        w = self.u(1.3)
        for k in range(0, dashes, 2):
            a0, a1 = 2 * math.pi * k / dashes, 2 * math.pi * (k + 1) / dashes
            p0 = (centre[0] + r * math.cos(a0), centre[1] + r * math.sin(a0))
            p1 = (centre[0] + r * math.cos(a1), centre[1] + r * math.sin(a1))
            if w > 1:
                pygame.draw.line(self.screen, colour, p0, p1, w)
            else:
                pygame.draw.aaline(self.screen, colour, p0, p1)

    def _pill(self, text, colour, midright, dot=None):
        t = self.f("tiny").render(text, True, colour)
        left_pad = self.u(24) if dot else self.u(10)
        box = pygame.Rect(0, 0, t.get_width() + left_pad + self.u(10), self.u(26))
        box.midright = midright
        pygame.draw.rect(self.screen, CARD, box, border_radius=box.h // 2)
        pygame.draw.rect(self.screen, colour, box, 1, border_radius=box.h // 2)
        if dot:
            self._aa_circle((box.x + self.u(14), box.centery), self.u(4), dot)
        self.screen.blit(t, (box.x + left_pad, box.centery - t.get_height() // 2))
        return box

    def _keycap(self, x, y, key, label):
        k = self.f("tiny").render(key, True, TEXT)
        box = pygame.Rect(x, y, k.get_width() + self.u(14), self.u(22))
        pygame.draw.rect(self.screen, CARD_2, box, border_radius=self.u(5))
        pygame.draw.rect(self.screen, BORDER, box, 1, border_radius=self.u(5))
        self.screen.blit(k, k.get_rect(center=box.center))
        r = self._text(label, "small", MUTED, (box.right + self.u(7), box.centery), "midleft")
        return r.right + self.u(18)

    # ======================================================================
    # frame
    # ======================================================================
    def draw(self, session):
        self._rescale()
        W, H = self.screen.get_size()
        u = self.u
        header_h, footer_h, gap = u(64), u(44), u(14)
        self.screen.fill(BG)
        side_w = int(min(u(440), max(u(380), W * 0.31)))
        body = pygame.Rect(gap, header_h, W - 2 * gap, H - header_h - footer_h)
        floor = pygame.Rect(body.x, body.y, body.w - side_w - gap, body.h)
        side = pygame.Rect(floor.right + gap, body.y, side_w, body.h)

        self._events(session)
        self._header(session, W, header_h, gap)
        self._floor(session, floor)
        self._sidebar(session, side, gap)
        self._footer(H, footer_h, gap)
        self._draw_toasts(floor)

        if self._shot_request:
            self._shot_request = False
            self._save_shot()
        pygame.display.flip()
        self.clock.tick(60)

    def _events(self, session):
        if session.synced_after is not None and self._seen_sync != session.epoch_start:
            self._seen_sync = session.epoch_start
            self.toast(f"Swarm synchronized in {session.synced_after:.1f} s", GOOD)
        heard = session.link is not None and session.link.last_heard is not None
        if heard and not self._seen_esp32:
            self._seen_esp32 = True
            self.toast("ESP32 joined the swarm", TEAL)

    def _blink(self):
        return (pygame.time.get_ticks() // 500) % 2 == 0

    # ----- header -----------------------------------------------------------
    def _header(self, session, W, header_h, gap):
        u = self.u
        pygame.draw.line(self.screen, BORDER, (0, header_h - 1), (W, header_h - 1))
        cy = header_h // 2
        x = gap + u(4)
        g = pygame.transform.smoothscale(self._glow[6], (u(44), u(44)))
        self.screen.blit(g, (x + u(8) - u(22), cy - u(22)))
        self._aa_circle((x + u(8), cy), u(7), AMBER)
        t = self._text("FireSync", "title", TEXT, (x + u(26), cy), "midleft")
        self._text("Firefly-inspired timing sync for drone swarms", "body", MUTED,
                   (t.right + u(14), cy), "midleft")

        live = session.link is not None
        colour = TEAL if live else AMBER
        dot = colour
        if live and session.link.last_heard is None:
            dot = WARN if self._blink() else FAINT
        box = self._pill("LIVE  ·  ESP32" if live else "SIMULATION", colour,
                         (W - gap - u(4), cy), dot=dot)
        if session.paused:
            self._pill("PAUSED", WARN, (box.x - u(10), cy))

    # ----- floor plan -------------------------------------------------------
    def _floor(self, session, rect):
        u = self.u
        sw = session.swarm
        aw, ah = sw.area
        self._card(rect, f"Floor plan  ·  {aw:g} × {ah:g} m",
                   f"{sw.n_virtual} virtual drones" + ("  +  1 real" if session.ext is not None else ""))
        inner = pygame.Rect(rect.x + u(32), rect.y + u(50), rect.w - u(64), rect.h - u(96))
        scale = min(inner.w / aw, inner.h / ah)
        ox = inner.x + (inner.w - aw * scale) / 2
        oy = inner.y + (inner.h - ah * scale) / 2
        plan = pygame.Rect(int(ox), int(oy), int(aw * scale), int(ah * scale))

        def P(pos):
            return (ox + pos[0] * scale, oy + pos[1] * scale)

        for m in range(0, int(aw) + 1):
            x = ox + m * scale
            pygame.draw.line(self.screen, GRID_MAJOR if m % 5 == 0 else GRID, (x, plan.y), (x, plan.bottom))
        for m in range(0, int(ah) + 1):
            y = oy + m * scale
            pygame.draw.line(self.screen, GRID_MAJOR if m % 5 == 0 else GRID, (plan.x, y), (plan.right, y))
        pygame.draw.rect(self.screen, BORDER, plan, 1)

        pts = [P(p) for p in sw.positions]

        # links and radio range stay inside the plan
        self.screen.set_clip(plan.inflate(2, 2))
        if self.show_links:
            for i, near in enumerate(sw.neighbours):
                for j in near:
                    if j > i:
                        pygame.draw.aaline(self.screen, (40, 52, 84), pts[i], pts[j])
        if session.ext is not None:
            e = session.ext
            if sw.radio_range:
                self._dashed_circle(pts[e], sw.radio_range * scale, TEAL_DIM)
            e_int = session.flash_intensity(e)
            lw = u(1.4)
            for j in sw.neighbours[e]:
                a = max(session.flash_intensity(j), e_int) * 160
                self._alpha_line(pts[e], pts[j], TEAL, a, lw)

        # drones may overhang the plan edge, but never leave the card
        self.screen.set_clip(rect.inflate(-4, -4))
        gr = self._glow_r
        for i, p in enumerate(pts):
            real = i in sw.external_names
            inten = session.flash_intensity(i)
            if inten > 0:
                self.screen.blit(self._glow[min(15, int(inten * 15))], (p[0] - gr, p[1] - gr))
            self._drone(p, inten, real, sw.phase_of(i))
        self.screen.set_clip(None)

        # scale bar + legend
        sx, sy = plan.x, rect.bottom - u(22)
        lw = u(2)
        pygame.draw.line(self.screen, MUTED, (sx, sy), (sx + 5 * scale, sy), lw)
        for x in (sx, sx + 5 * scale):
            pygame.draw.line(self.screen, MUTED, (x, sy - u(4)), (x, sy + u(4)), lw)
        lab = self._text("5 m", "small", MUTED, (sx + 5 * scale + u(8), sy), "midleft")
        if session.ext is not None and sw.radio_range:
            lx = lab.right + u(24)
            self._dashed_circle((lx + u(7), sy), u(6), TEAL_DIM, dashes=12)
            self._text(f"ESP32 radio range ({sw.radio_range:g} m)", "small", MUTED, (lx + u(20), sy), "midleft")

    def _drone(self, c, inten, real, phase):
        u = self.u
        size = u(11) if real else u(8)
        base = TEAL if real else DRONE
        col = _lerp(base, (255, 236, 170), inten) if inten > 0 else base
        ring_r = size + u(9)
        lw = u(2)
        # phase ring: the firefly's "timer" filling up
        self._ring(c, ring_r, max(1, u(1)), (34, 44, 70))
        if phase is not None and phase > 0.01:
            pygame.draw.lines(self.screen, TEAL if real else (98, 118, 168), False,
                              self._arc_points(c, ring_r, phase, 48), lw)
        # arms and rotors
        arm = size * 0.95
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            end = (c[0] + dx * arm, c[1] + dy * arm)
            pygame.draw.line(self.screen, col, c, end, max(1, u(1.5)))
            rr = max(3, size // 2 - 1)
            self._ring(end, rr, max(1, u(1.2)), col)
        self._aa_circle(c, max(3, size // 3 + 1), col)
        if real:
            self._text("ESP32", "tiny", TEAL, (c[0], c[1] + ring_r + u(6)), "midtop")

    # ----- sidebar ----------------------------------------------------------
    def _sidebar(self, session, rect, gap):
        u = self.u
        half = (rect.w - gap) // 2
        top_h = u(196)
        self._sync_card(session, pygame.Rect(rect.x, rect.y, half, top_h))
        self._phase_card(session, pygame.Rect(rect.x + half + gap, rect.y, rect.w - half - gap, top_h))
        y = rect.y + top_h + gap
        mid_h = u(112)
        if session.ext is not None:
            self._esp32_card(session, pygame.Rect(rect.x, y, rect.w, mid_h))
        else:
            self._params_card(session, pygame.Rect(rect.x, y, rect.w, mid_h))
        y += mid_h + gap
        self._graph_card(session, pygame.Rect(rect.x, y, rect.w, rect.bottom - y))

    def _sync_card(self, session, r):
        u = self.u
        self._card(r, "Swarm sync")
        lvl = session.sync_level()
        col = _level_colour(lvl)
        c = (r.centerx, r.y + u(98))
        R, width = u(52), u(10)
        self._ring(c, R, width, CARD_2)
        self._thick_arc(c, R, width, lvl, col)
        self._text(f"{100 * lvl:.0f}%", "num", TEXT, c, "center")
        if session.synced_after is not None:
            msg, mc = f"Synced in {session.synced_after:.1f} s", GOOD
        else:
            msg, mc = "Synchronizing…", MUTED
        self._text(msg, "small", mc, (r.centerx, r.bottom - u(14)), "midbottom")

    def _phase_card(self, session, r):
        u = self.u
        sw = session.swarm
        self._card(r, "Phase map")
        c = (r.centerx, r.y + u(104))
        R = min(r.w // 2 - u(28), u(62))
        self._ring(c, R, max(1, u(1.5)), BORDER)
        top = (c[0], c[1] - R)
        pygame.draw.line(self.screen, AMBER, (top[0], top[1] - u(6)), (top[0], top[1] + u(6)), u(2))
        self._text("flash", "tiny", AMBER, (top[0] + u(8), top[1] - u(6)), "bottomleft")
        phases = sw.virtual_phases
        for i, ph in enumerate(phases):
            a = -math.pi / 2 + 2 * math.pi * ph
            p = (c[0] + R * math.cos(a), c[1] + R * math.sin(a))
            self._aa_circle(p, u(4), _lerp((130, 145, 190), AMBER, session.flash_intensity(i)))
        if session.ext is not None:
            ph = sw.phase_of(session.ext)
            if ph is not None:
                a = -math.pi / 2 + 2 * math.pi * ph
                self._aa_circle((c[0] + R * math.cos(a), c[1] + R * math.sin(a)), u(6), TEAL)
        lvl = metrics.order_parameter(phases)
        mean = metrics.circular_mean(phases)
        a = -math.pi / 2 + 2 * math.pi * mean
        tip = (c[0] + (R - u(8)) * lvl * math.cos(a), c[1] + (R - u(8)) * lvl * math.sin(a))
        pygame.draw.line(self.screen, _level_colour(lvl), c, tip, u(3))
        self._aa_circle(c, u(3), MUTED)
        self._text("arrow length = sync", "small", FAINT, (r.centerx, r.bottom - u(12)), "midbottom")

    def _esp32_card(self, session, r):
        u = self.u
        link = session.link
        heard = link is not None and link.last_heard is not None
        self._card(r, "Real drone  ·  ESP32",
                   f"hears {len(session._ext_neighbours)} drones  ·  rx {link.received}  tx {link.sent}" if link else None)
        x, y = r.x + u(16), r.y + u(40)
        if not heard:
            self._aa_circle((x + u(6), y + u(20)), u(6), WARN if self._blink() else FAINT)
            self._text("Waiting for ESP32…", "head", TEXT, (x + u(22), y + u(20)), "midleft")
            self._text("Same 2.4 GHz hotspot?  Right IP?  Firewall allows Python?",
                       "small", MUTED, (x + u(22), y + u(46)), "midleft")
            return
        off = session.esp32_offset()
        stale = session.swarm.time - link.last_heard > 3
        self._aa_circle((x + u(6), y + u(20)), u(6), BAD if stale else GOOD)
        self._text("Signal lost" if stale else "Connected", "head", TEXT, (x + u(22), y + u(20)), "midleft")
        self._text("off-beat vs swarm", "small", MUTED, (x + u(22), y + u(46)), "midleft")
        if off is not None:
            a = abs(off)
            col = GOOD if a < 30 else WARN if a < 100 else BAD
            verdict = "in sync" if a < 30 else "locking on…" if a < 100 else "off-beat"
            self._text(f"{off:+.0f} ms", "big", col, (r.right - u(16), y + u(2)), "topright")
            self._text(verdict, "small", col, (r.right - u(16), y + u(46)), "topright")

    def _params_card(self, session, r):
        u = self.u
        sw = session.swarm
        self._card(r, "Model  ·  Mirollo-Strogatz pulse-coupled oscillators")
        items = [("Drones", f"{sw.n_virtual}"),
                 ("Period", f"{sw.period:g} s"),
                 ("Coupling", f"{sw.oscillators[0].coupling:g}"),
                 ("Radio range", "all" if sw.radio_range is None else f"{sw.radio_range:g} m")]
        cw = (r.w - u(32)) // len(items)
        for k, (label, val) in enumerate(items):
            x = r.x + u(16) + k * cw
            self._text(val, "num" if len(val) < 6 else "head", TEXT, (x, r.y + u(42)))
            self._text(label, "small", MUTED, (x, r.y + u(82)))

    def _graph_card(self, session, r):
        u = self.u
        self._card(r, "Sync level", "last 30 s")
        g = pygame.Rect(r.x + u(44), r.y + u(40), r.w - u(60), r.h - u(72))
        for frac, lab in ((1.0, "100%"), (0.5, "50%"), (0.0, "0%")):
            y = g.bottom - frac * g.h
            pygame.draw.line(self.screen, GRID, (g.x, y), (g.right, y))
            self._text(lab, "small", FAINT, (g.x - u(8), y), "midright")
        y95 = g.bottom - 0.95 * g.h
        dash, lw = u(4), max(1, u(1))
        for x in range(g.x, g.right, 2 * dash):
            pygame.draw.line(self.screen, (60, 120, 96), (x, y95), (min(x + dash, g.right), y95), lw)
        self._text("95% = synchronized", "tiny", (60, 150, 116), (g.x + u(4), y95 - u(4)), "bottomleft")
        for frac, lab in ((0, "-30 s"), (0.5, "-15 s"), (1, "now")):
            anchor = "midtop" if 0 < frac < 1 else ("topleft" if frac == 0 else "topright")
            self._text(lab, "small", FAINT, (g.x + frac * g.w, g.bottom + u(6)), anchor)
        hist = list(session.history)
        if len(hist) < 2:
            return
        t_end = hist[-1][0]
        pts = [(g.x + (t - (t_end - 30)) / 30 * g.w, g.bottom - lvl * g.h)
               for t, lvl in hist if t >= t_end - 30]
        if len(pts) < 2:
            return
        fill = pygame.Surface((g.w + 2, g.h + 2), pygame.SRCALPHA)
        poly = [(x - g.x, y - g.y) for x, y in pts] + [(pts[-1][0] - g.x, g.h), (pts[0][0] - g.x, g.h)]
        pygame.draw.polygon(fill, (*AMBER, 38), poly)
        self.screen.blit(fill, g.topleft)
        pygame.draw.lines(self.screen, AMBER, False, pts, u(2))
        self._aa_circle(pts[-1], u(4), AMBER)

    # ----- footer + toasts --------------------------------------------------
    def _footer(self, H, footer_h, gap):
        y = H - footer_h + (footer_h - self.u(22)) // 2
        x = gap + self.u(4)
        for key, label in (("R", "Scramble"), ("SPACE", "Pause"), ("L", "Radio links"),
                           ("F", "Fullscreen"), ("S", "Screenshot"), ("ESC", "Quit")):
            x = self._keycap(x, y, key, label)

    def _draw_toasts(self, floor):
        u = self.u
        now = pygame.time.get_ticks() / 1000
        self._toasts = [t for t in self._toasts if t[2] > now]
        y = floor.y + u(46)
        for text, colour, until in self._toasts[-3:]:
            alpha = min(1.0, (until - now) / 0.4)
            surf = self.f("head").render(text, True, colour)
            box = pygame.Rect(0, 0, surf.get_width() + u(36), u(36))
            box.midtop = (floor.centerx, y)
            panel = pygame.Surface(box.size, pygame.SRCALPHA)
            pygame.draw.rect(panel, (*CARD_2, int(235 * alpha)), panel.get_rect(), border_radius=box.h // 2)
            pygame.draw.rect(panel, (*colour, int(200 * alpha)), panel.get_rect(), 1, border_radius=box.h // 2)
            self.screen.blit(panel, box)
            surf.set_alpha(int(255 * alpha))
            self.screen.blit(surf, surf.get_rect(center=box.center))
            y += u(44)

    # ======================================================================
    def _save_shot(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        folder = os.path.join(root, "data", "shots")
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, datetime.datetime.now().strftime("firesync_%Y%m%d_%H%M%S.png"))
        pygame.image.save(self.screen, path)
        self.toast("Screenshot saved to data/shots", TEXT)

    def save_screenshot(self, path):
        pygame.image.save(self.screen, path)

    def close(self):
        pygame.quit()
