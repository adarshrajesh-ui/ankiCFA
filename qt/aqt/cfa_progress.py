# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""CFA Progress — the native in-window "study statistics" tab.

Renders the SvelteKit ``graphs`` page (reviews, retention, future due, buttons,
etc.) into the MAIN webview. The page is already themed to the CFA design system
(brand eyebrow, CFA page tint, serif-navy card titles), and it is self-contained
— its ``RangeBox`` carries its own scope/search + day-range controls — so it
works as a first-class main-window state without the modal ``NewDeckStats``
dialog chrome (deck chooser + Save-PDF live on the menu-bar ``Statistics`` entry,
which is untouched).

For a CFA exam-prep product, "how am I tracking" is core, yet the themed
statistics screen was reachable ONLY from Anki's menu bar — the CFA top-bar nav
(Home / Study / Ethics / Concept Map / Readiness) had no Progress entry. This
controller mirrors :class:`aqt.cfa_readiness.CfaReadiness` so Progress plugs into
the main-window state machine as the ``cfaProgress`` state; the CFA-branded top
bar is redrawn on show, so the user is never trapped — Home is one click away.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aqt.sound import av_player

if TYPE_CHECKING:
    from aqt.main import AnkiQt


class CfaProgress:
    """Controller for the CFA Progress (statistics) state."""

    def __init__(self, mw: AnkiQt) -> None:
        self.mw = mw
        self.web = mw.web

    def show(self) -> None:
        av_player.stop_and_clear_queue()
        self.web.set_bridge_command(self._link_handler, self)
        # redraw the (CFA-branded) top bar, matching CfaHome/CfaReadiness
        self.mw.toolbar.redraw()
        self.web.load_sveltekit_page("graphs")
        self.web.setFocus()

    # Bridge (pycmd / bridgeCommand) handlers
    ##########################################################################

    def _link_handler(self, cmd: str) -> bool:
        # The graphs page's only bridge command is ``browserSearch: <query>``
        # (click a bar to see those cards), mirrored from the NewDeckStats
        # dialog so the "drill into a chart" affordance keeps working here.
        import aqt

        if cmd.startswith("browserSearch"):
            _, query = cmd.split(":", 1)
            browser = aqt.dialogs.open("Browser", self.mw)
            browser.search_for(query)
        return False
