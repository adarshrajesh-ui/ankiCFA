# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from __future__ import annotations

import enum
import json
import logging
import mimetypes
import os
import re
import secrets
import sys
import threading
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from errno import EPROTOTYPE
from http import HTTPStatus
from pathlib import Path
from typing import Any

import flask
import stringcase
import waitress.wasyncore
from flask import Response, abort, request
from waitress.server import create_server

import aqt
import aqt.main
import aqt.operations
from anki import frontend_pb2, generic_pb2, hooks
from anki.collection import Collection, OpChangesOnly, Progress, SearchNode
from anki.decks import DeckId, UpdateDeckConfigs, UpdateDeckConfigsMode
from anki.scheduler.v3 import SchedulingStatesWithContext, SetSchedulingStatesRequest
from anki.utils import dev_mode
from aqt.changenotetype import ChangeNotetypeDialog
from aqt.deckoptions import DeckOptionsDialog
from aqt.operations import on_op_finished
from aqt.operations.deck import update_deck_configs as update_deck_configs_op
from aqt.progress import ProgressUpdate
from aqt.qt import *
from aqt.utils import aqt_data_path, show_warning, tr

# https://forums.ankiweb.net/t/anki-crash-when-using-a-specific-deck/22266
waitress.wasyncore._DISCONNECTED = waitress.wasyncore._DISCONNECTED.union({EPROTOTYPE})  # type: ignore

logger = logging.getLogger(__name__)
app = flask.Flask(__name__, root_path="/fake")


@dataclass
class LocalFileRequest:
    # base folder, eg media folder
    root: str
    # path to file relative to root folder
    path: str
    # collection media is untrusted user content; add-on web exports are not
    untrusted: bool = True


UNTRUSTED_MEDIA_CSP = "; ".join(
    (
        "default-src 'none'",
        "script-src 'none'",
        "connect-src 'none'",
        "object-src 'none'",
        "frame-src 'none'",
        "child-src 'none'",
        "base-uri 'none'",
        "form-action 'none'",
        "sandbox",
    )
)


def _editor_content_security_policy(port: int) -> str:
    csp_paths = (
        f"http://127.0.0.1:{port}/_anki/",
        f"http://127.0.0.1:{port}/_addons/",
    )
    return "; ".join((f"script-src {' '.join(csp_paths)}",))


@dataclass
class BundledFileRequest:
    # path relative to aqt data folder
    path: str


@dataclass
class NotFound:
    message: str


DynamicRequest = Callable[[], Response]


class PageContext(enum.IntEnum):
    UNKNOWN = enum.auto()
    EDITOR = enum.auto()
    REVIEWER = enum.auto()
    PREVIEWER = enum.auto()
    CARD_LAYOUT = enum.auto()
    DECK_OPTIONS = enum.auto()
    # something in /_anki/pages/
    NON_LEGACY_PAGE = enum.auto()
    # Do not use this if you present user content (e.g. content from cards), as it's a
    # security issue.
    ADDON_PAGE = enum.auto()


@dataclass
class LegacyPage:
    html: str
    context: PageContext


class MediaServer(threading.Thread):
    _ready = threading.Event()
    daemon = True

    def __init__(self, mw: aqt.main.AnkiQt) -> None:
        super().__init__()
        self.is_shutdown = False
        # map of webview ids to pages
        self._legacy_pages: dict[int, LegacyPage] = {}

    def run(self) -> None:
        try:
            desired_host = os.getenv("ANKI_API_HOST", "127.0.0.1")
            desired_port = int(os.getenv("ANKI_API_PORT") or 0)
            self.server = create_server(
                app,
                host=desired_host,
                port=desired_port,
                clear_untrusted_proxy_headers=True,
            )
            logger.info(
                "Serving on http://%s:%s",
                self.server.effective_host,  # type: ignore[union-attr]
                self.server.effective_port,  # type: ignore[union-attr]
            )

            self._ready.set()
            self.server.run()

        except Exception:
            if not self.is_shutdown:
                raise

    def shutdown(self) -> None:
        self.is_shutdown = True
        sockets = list(self.server._map.values())  # type: ignore
        for socket in sockets:
            socket.handle_close()
        # https://github.com/Pylons/webtest/blob/4b8a3ebf984185ff4fefb31b4d0cf82682e1fcf7/webtest/http.py#L93-L104
        self.server.task_dispatcher.shutdown()

    def getPort(self) -> int:
        self._ready.wait()
        return int(self.server.effective_port)  # type: ignore

    def set_page_html(
        self, id: int, html: str, context: PageContext = PageContext.UNKNOWN
    ) -> None:
        self._legacy_pages[id] = LegacyPage(html, context)

    def get_page(self, id: int) -> LegacyPage | None:
        return self._legacy_pages.get(id)

    def get_page_html(self, id: int) -> str | None:
        if page := self.get_page(id):
            return page.html
        else:
            return None

    def get_page_context(self, id: int) -> PageContext | None:
        if page := self.get_page(id):
            return page.context
        else:
            return None

    def clear_page_html(self, id: int) -> None:
        try:
            del self._legacy_pages[id]
        except KeyError:
            pass


@app.route("/favicon.ico")
def favicon() -> Response:
    request = BundledFileRequest(os.path.join("imgs", "favicon.ico"))
    return _handle_builtin_file_request(request)


def _mime_for_path(path: str) -> str:
    "Mime type for provided path/filename."

    _, ext = os.path.splitext(path)
    ext = ext.lower()

    # Badly-behaved apps on Windows can alter the standard mime types in the registry, which can completely
    # break Anki's UI. So we hard-code the most common extensions.
    mime_types = {
        ".css": "text/css",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".html": "text/html",
        ".htm": "text/html",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".ico": "image/x-icon",
        ".json": "application/json",
        ".woff": "font/woff",
        ".woff2": "font/woff2",
        ".ttf": "font/ttf",
        ".otf": "font/otf",
        ".mp3": "audio/mpeg",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".ogg": "audio/ogg",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
    }

    if mime := mime_types.get(ext):
        return mime
    else:
        # fallback to mimetypes, which may consult the registry
        mime, _encoding = mimetypes.guess_type(path)
        return mime or "application/octet-stream"


def _text_response(code: HTTPStatus, text: str) -> Response:
    """Return an error message.

    Response is returned as text/plain, so no escaping of untrusted
    input is required."""
    resp = flask.make_response(text, code)
    resp.headers["Content-type"] = "text/plain"
    return resp


class UnsafePathException(Exception):
    def __init__(self, path: str):
        super().__init__(f"Invalid path: {path}")


def ensure_safe_path(base_dir: str | Path, path: str | Path) -> str:
    base_dir = os.path.realpath(base_dir)
    path = os.path.normpath(path)
    fullpath = os.path.abspath(os.path.join(base_dir, path))

    # protect against directory traversal: https://security.openstack.org/guidelines/dg_using-file-paths.html
    if not fullpath.startswith(base_dir + os.sep):
        raise UnsafePathException(path)
    return fullpath


_LOCALHOST_HOSTS = ("127.0.0.1", "localhost", "[::1]")

_ALLOWED_ORIGIN_PREFIXES = tuple(
    f"{scheme}{host}" for scheme in ("http://", "https://") for host in _LOCALHOST_HOSTS
)


def is_localhost_origin(origin: str) -> bool:
    for prefix in _ALLOWED_ORIGIN_PREFIXES:
        if (
            origin == prefix
            or origin.startswith(prefix + ":")
            or origin.startswith(prefix + "/")
        ):
            return True
    return False


def _handle_local_file_request(request: LocalFileRequest) -> Response:
    directory = request.root
    path = request.path
    try:
        isdir = os.path.isdir(os.path.join(directory, path))
    except ValueError:
        return _text_response(
            HTTPStatus.BAD_REQUEST, f"Path for '{directory} - {path}' is too long!"
        )

    fullpath = ensure_safe_path(directory, path)

    if isdir:
        return _text_response(
            HTTPStatus.FORBIDDEN,
            f"Path for '{directory} - {path}' is a directory (not supported)!",
        )

    try:
        mimetype = _mime_for_path(fullpath)
        if os.path.exists(fullpath):
            if fullpath.endswith(".css"):
                # caching css files prevents flicker in the webview, but we want
                # a short cache
                max_age = 10
            elif fullpath.endswith(".js"):
                # don't cache js files
                max_age = 0
            else:
                max_age = 60 * 60
            response = flask.send_file(
                fullpath,
                mimetype=mimetype,
                conditional=True,
                max_age=max_age,
                download_name="foo",  # type: ignore[call-arg]
            )
            if request.untrusted:
                # Prevent user-provided HTML/SVG from running as an active document.
                response.headers["Content-Security-Policy"] = UNTRUSTED_MEDIA_CSP
            return response
        else:
            print(f"Not found: {path}")
            return _text_response(HTTPStatus.NOT_FOUND, f"Invalid path: {path}")

    except Exception as error:
        if dev_mode:
            print(
                "Caught HTTP server exception,\n%s"
                % "".join(traceback.format_exception(*sys.exc_info())),
            )

        # swallow it - user likely surfed away from
        # review screen before an image had finished
        # downloading
        return _text_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))


def _builtin_data(path: str) -> bytes:
    """Return data from file in aqt/data folder."""
    full_path = ensure_safe_path(aqt_data_path().parent, path)
    with open(full_path, "rb") as f:
        return f.read()


def _handle_builtin_file_request(request: BundledFileRequest) -> Response:
    path = request.path
    # do we need to serve the fallback page?
    immutable = "immutable" in path
    if path.startswith("sveltekit/") and not immutable:
        path = "sveltekit/index.html"
    mimetype = _mime_for_path(path)
    data_path = f"data/web/{path}"
    try:
        data = _builtin_data(data_path)
        response = Response(data, mimetype=mimetype)
        if immutable:
            response.headers["Cache-Control"] = "max-age=31536000"
        return response
    except FileNotFoundError:
        if dev_mode:
            print(f"404: {data_path}")
        resp = _text_response(HTTPStatus.NOT_FOUND, f"Invalid path: {path}")
        # we're including the path verbatim in our response, so we need to either use
        # plain text, or escape HTML characters to avoid reflecting untrusted input
        resp.headers["Content-type"] = "text/plain"
        return resp
    except Exception as error:
        if dev_mode:
            print(
                "Caught HTTP server exception,\n%s"
                % "".join(traceback.format_exception(*sys.exc_info())),
            )

        # swallow it - user likely surfed away from
        # review screen before an image had finished
        # downloading
        return _text_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(error))


@app.route("/<path:pathin>", methods=["GET", "POST"])
def handle_request(pathin: str) -> Response:
    if os.environ.get("ANKI_API_HOST") != "0.0.0.0":
        host = request.headers.get("Host", "").lower()
        origin = request.headers.get("Origin", "").lower()
        allowed_hosts = tuple(f"{h}:" for h in _LOCALHOST_HOSTS)
        if not any(host.startswith(h) for h in allowed_hosts):
            logger.warning("denied non-local host: %s", host)
            abort(403)
        if origin and not is_localhost_origin(origin):
            logger.warning("denied non-local origin: %s", origin)
            abort(403)

    req = _extract_request(pathin)
    logger.debug("%s /%s", flask.request.method, pathin)

    try:
        if isinstance(req, NotFound):
            print(req.message)
            return _text_response(HTTPStatus.NOT_FOUND, f"Invalid path: {pathin}")
        elif callable(req):
            return _handle_dynamic_request(req)
        elif isinstance(req, BundledFileRequest):
            return _handle_builtin_file_request(req)
        elif isinstance(req, LocalFileRequest):
            return _handle_local_file_request(req)
        else:
            return _text_response(HTTPStatus.FORBIDDEN, f"unexpected request: {pathin}")
    except UnsafePathException as exc:
        return _text_response(HTTPStatus.FORBIDDEN, str(exc))


def is_sveltekit_page(path: str) -> bool:
    page_name = path.split("/")[0]
    return page_name in [
        "graphs",
        "congrats",
        "card-info",
        "change-notetype",
        "deck-options",
        "import-anki-package",
        "import-csv",
        "import-page",
        "image-occlusion",
        "cfa-readiness",
        "cfa-deadline",
        "cfa-home",
    ]


def _extract_internal_request(
    path: str,
) -> BundledFileRequest | DynamicRequest | NotFound | None:
    "Catch /_anki references and rewrite them to web export folder."
    if is_sveltekit_page(path):
        path = f"_anki/sveltekit/_app/{path}"
    if path.startswith("_app/"):
        path = path.replace("_app", "_anki/sveltekit/_app")

    prefix = "_anki/"
    if not path.startswith(prefix):
        return None

    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    additional_prefix = None

    if dirname == "_anki":
        if flask.request.method == "POST":
            return _extract_collection_post_request(filename)
        elif get_handler := _extract_dynamic_get_request(filename):
            return get_handler

        # remap legacy top-level references
        base, ext = os.path.splitext(filename)
        if ext == ".css":
            additional_prefix = "css/"
        elif ext == ".js":
            if base in ("jquery-ui", "jquery", "plot"):
                additional_prefix = "js/vendor/"
            else:
                additional_prefix = "js/"
    # handle requests for vendored libraries
    elif dirname == "_anki/js/vendor":
        base, ext = os.path.splitext(filename)

        if base == "jquery":
            base = "jquery.min"
            additional_prefix = "js/vendor/"

        elif base == "jquery-ui":
            base = "jquery-ui.min"
            additional_prefix = "js/vendor/"

    if additional_prefix:
        oldpath = path
        path = f"{prefix}{additional_prefix}{base}{ext}"
        print(f"legacy {oldpath} remapped to {path}")

    return BundledFileRequest(path=path[len(prefix) :])


def _extract_addon_request(path: str) -> LocalFileRequest | NotFound | None:
    "Catch /_addons references and rewrite them to addons folder."
    prefix = "_addons/"
    if not path.startswith(prefix):
        return None

    addon_path = path[len(prefix) :]

    try:
        manager = aqt.mw.addonManager
    except AttributeError as error:
        if dev_mode:
            print(f"_redirectWebExports: {error}")
        return None

    try:
        addon, sub_path = addon_path.split("/", 1)
    except ValueError:
        return None
    if not addon:
        return None

    pattern = manager.getWebExports(addon)
    if not pattern:
        return None

    if re.fullmatch(pattern, sub_path):
        return LocalFileRequest(
            root=manager.addonsFolder(), path=addon_path, untrusted=False
        )

    return NotFound(message=f"couldn't locate item in add-on folder {path}")


def _extract_request(
    path: str,
) -> LocalFileRequest | BundledFileRequest | DynamicRequest | NotFound:
    if internal := _extract_internal_request(path):
        return internal
    elif addon := _extract_addon_request(path):
        return addon

    if not aqt.mw.col:
        return NotFound(message=f"collection not open, ignore request for {path}")

    path = hooks.media_file_filter(path)
    return LocalFileRequest(root=aqt.mw.col.media.dir(), path=path)


def congrats_info() -> bytes:
    if not aqt.mw.col.sched._is_finished():
        aqt.mw.taskman.run_on_main(lambda: aqt.mw.moveToState("overview"))
    return raw_backend_request("congrats_info")()


def get_deck_configs_for_update() -> bytes:
    return aqt.mw.col._backend.get_deck_configs_for_update_raw(request.data)


def _on_update_deck_configs_success(input: UpdateDeckConfigs) -> None:
    is_compute_all = (
        input.mode == UpdateDeckConfigsMode.UPDATE_DECK_CONFIGS_MODE_COMPUTE_ALL_PARAMS
    )
    if not is_compute_all and isinstance(
        window := aqt.mw.app.activeModalWidget(), DeckOptionsDialog
    ):
        window.reject()


def update_deck_configs() -> bytes:
    # the regular change tracking machinery expects to be started on the main
    # thread and uses a callback on success, so we need to run this op on
    # main, and return immediately from the web request

    input = UpdateDeckConfigs()
    input.ParseFromString(request.data)

    def on_progress(progress: Progress, update: ProgressUpdate) -> None:
        if progress.HasField("compute_memory"):
            val = progress.compute_memory
            update.max = val.total_cards
            update.value = val.current_cards
            update.label = val.label
        elif progress.HasField("compute_params"):
            val2 = progress.compute_params
            # prevent an indeterminate progress bar from appearing at the start of each preset
            update.max = max(val2.total, 1)
            update.value = val2.current
            pct = str(int(val2.current / val2.total * 100) if val2.total > 0 else 0)
            label = tr.deck_config_optimizing_preset(
                current_count=val2.current_preset, total_count=val2.total_presets
            )
            if val2.reviews:
                reviews = tr.deck_config_percent_of_reviews(
                    pct=pct, reviews=val2.reviews
                )
            else:
                reviews = tr.qt_misc_processing()

            update.label = label + "\n" + reviews
        else:
            return
        if update.user_wants_abort:
            update.abort = True

    def handle_on_main() -> None:
        update_deck_configs_op(parent=aqt.mw, input=input).success(
            lambda _: _on_update_deck_configs_success(input)
        ).with_backend_progress(on_progress).run_in_background()

    aqt.mw.taskman.run_on_main(handle_on_main)
    return b""


def get_scheduling_states_with_context() -> bytes:
    return SchedulingStatesWithContext(
        states=aqt.mw.reviewer.get_scheduling_states(),
        context=aqt.mw.reviewer.get_scheduling_context(),
    ).SerializeToString()


def set_scheduling_states() -> bytes:
    states = SetSchedulingStatesRequest()
    states.ParseFromString(request.data)
    aqt.mw.reviewer.set_scheduling_states(states)
    return b""


def import_done() -> bytes:
    def update_window_modality() -> None:
        if window := aqt.mw.app.activeModalWidget():
            from aqt.import_export.import_dialog import ImportDialog

            if isinstance(window, ImportDialog):
                window.hide()
                window.setWindowModality(Qt.WindowModality.NonModal)
                window.show()

    aqt.mw.taskman.run_on_main(update_window_modality)
    return b""


def import_request(endpoint: str) -> bytes:
    output = raw_backend_request(endpoint)()
    response = OpChangesOnly()
    response.ParseFromString(output)

    def handle_on_main() -> None:
        window = aqt.mw.app.activeModalWidget()
        on_op_finished(aqt.mw, response, window)

    aqt.mw.taskman.run_on_main(handle_on_main)

    return output


def import_csv() -> bytes:
    return import_request("import_csv")


def import_anki_package() -> bytes:
    return import_request("import_anki_package")


def import_json_file() -> bytes:
    return import_request("import_json_file")


def import_json_string() -> bytes:
    return import_request("import_json_string")


def search_in_browser() -> bytes:
    node = SearchNode()
    node.ParseFromString(request.data)

    def handle_on_main() -> None:
        aqt.dialogs.open("Browser", aqt.mw, search=(node,))

    aqt.mw.taskman.run_on_main(handle_on_main)

    return b""


def change_notetype() -> bytes:
    data = request.data

    def handle_on_main() -> None:
        window = aqt.mw.app.activeModalWidget()
        if isinstance(window, ChangeNotetypeDialog):
            window.save(data)

    aqt.mw.taskman.run_on_main(handle_on_main)
    return b""


def deck_options_require_close() -> bytes:
    def handle_on_main() -> None:
        window = aqt.mw.app.activeModalWidget()
        if isinstance(window, DeckOptionsDialog):
            window.require_close()

    # on certain linux systems, askUser's QMessageBox.question unsets the active window
    # so we wait for the next event loop before querying the next current active window
    aqt.mw.taskman.run_on_main(lambda: QTimer.singleShot(0, handle_on_main))
    return b""


def deck_options_ready() -> bytes:
    def handle_on_main() -> None:
        window = aqt.mw.app.activeModalWidget()
        if isinstance(window, DeckOptionsDialog):
            window.set_ready()

    aqt.mw.taskman.run_on_main(handle_on_main)
    return b""


def save_custom_colours() -> bytes:
    colors = [
        QColorDialog.customColor(i).name(QColor.NameFormat.HexRgb)
        for i in range(QColorDialog.customCount())
    ]
    aqt.mw.col.set_config("customColorPickerPalette", colors)
    return b""


# =============================================================================
# CFA fork: JSON payloads for the SvelteKit Exam Readiness / Deadline pages.
#
# These mirror the desktop dialogs in aqt/cfa.py exactly — same pylib scores,
# same abstain gate, same labels/thresholds — so the web pages present the SAME
# honest data. There is NO logic/threshold change here; this layer only
# serialises the existing scores into the JSON data contract that the shared web
# components (ts/lib/cfa) consume.
# =============================================================================

_CFA_READINESS_FOOTER = (
    "The headline is a Bayesian call: exam-weighted accuracy as a 95% credible "
    "band (per-topic Beta posterior on first-exposure correctness) that starts "
    "wide and narrows as reviews accrue — no give-up wall. Recall uses FSRS R, "
    "falling back to an SM-2 forgetting curve so a number appears from the first "
    "review. Below it, the three give-up-gated scores: Memory (exam-weighted "
    "per-topic FSRS retrievability), Performance (Wilson interval on "
    "first-exposure accuracy) and Readiness (fused P(pass)). The pass/fail call "
    "is NOT validated against real exam data. No AI — pure spaced-repetition "
    "stats."
)

_CFA_DEADLINE_FOOTER = (
    "Weakest cards on the day are shown first. Study these to peak on the exam "
    "date. Read-only — FSRS scheduling and undo stay valid. No AI."
)

# Predicted exam-day recall below this is flagged as a weak card (mirrors the
# desktop deadline table's warn colour: recall < 0.85).
_CFA_DEADLINE_WARN_RECALL = 0.85


def _cfa_score_band(name: str, meaning: str, score: Any) -> dict[str, Any]:
    """One honest score serialised as the shared ScoreBand contract."""
    return {
        "name": name,
        "meaning": meaning,
        "abstain": score.abstain,
        "reason": score.reason,
        "point": score.point,
        "rangeLow": score.range_low,
        "rangeHigh": score.range_high,
    }


def _cfa_exam_readiness_payload(col: Collection, deck_id: int) -> dict[str, Any]:
    from anki import cfa

    # ``deck_id == 0`` means score the WHOLE collection (every deck) rather than a
    # single deck subtree. The CFA Home / Concept Map / native Readiness screens
    # pass 0 so the special "CFA::Ethics Pairs" deck — which is a SIBLING of the
    # "CFA Level II" deck, not a child — and any other studied CFA content all
    # impact the three scores, the Bayesian verdict and the concept-map fills.
    # This matches the AnkiDroid client, which already calls
    # ``computeCfaScores(wholeCollection=true)``: the desktop was the only surface
    # still scoping the headline scores to the "CFA Level II" subtree, so the same
    # reviews produced different scores on desktop vs phone and ethics-pair reviews
    # never reached the desktop readiness report or concept map. A real (non-zero)
    # deck id still scopes to that deck + children (per-deck readiness).
    scope = deck_id or None
    bayes = cfa.bayesian_readiness(col, deck_id=scope)
    score = cfa.memory_score(col, deck_id=scope)
    perf = cfa.performance_score(col, deck_id=scope)
    ready = cfa.readiness_score(col, deck_id=scope)
    deck_name = _cfa_scope_name(col, deck_id)

    # Hero: the Bayesian pass/fail call, but ABSTAIN when either Memory or
    # Performance gives up — identical gate to the desktop dialog
    # (score.abstain || perf.abstain).
    hero_abstain = score.abstain or perf.abstain

    payload: dict[str, Any] = {
        "deckName": deck_name,
        "heroMode": "abstain" if hero_abstain else "bayesian_call",
        "memory": _cfa_score_band(
            "Memory",
            "recall probability, exam-weighted across topics",
            score,
        ),
        "performance": _cfa_score_band(
            "Performance",
            "P(correct on a new question), first-exposure accuracy",
            perf,
        ),
        "readiness": {
            **_cfa_score_band("Readiness", "P(pass); wide range, uncalibrated", ready),
            "label": ready.label,
        },
        "caption": {
            "coveragePct": score.coverage_pct,
            "topicsCovered": score.topics_covered,
            "topicsTotal": score.topics_total,
            "gradedReviews": score.graded_reviews,
            "firstExposures": perf.first_exposures,
            "lastReviewAt": score.last_review_at,
        },
        "topics": [
            {
                # Display the readable CFA topic-area NAME, not the raw
                # ``los::<slug>`` join-key tag (behaviour otherwise identical).
                "topic": cfa.topic_display_name(t.topic),
                "weight": t.weight,
                "reviewedCards": t.reviewed_cards,
                "gradedReviews": t.graded_reviews,
                "recallRange": (
                    {"low": t.r_low, "high": t.r_high} if t.avg_r is not None else None
                ),
                "covered": t.covered,
            }
            for t in sorted(score.topics, key=lambda x: -x.weight)
        ],
        "footerText": _CFA_READINESS_FOOTER,
    }

    if hero_abstain:
        payload["heroAbstain"] = {
            "reason": score.reason if score.abstain else perf.reason,
            "readinessLabel": cfa.READINESS_LABEL,
        }
    else:
        payload["heroBayesian"] = {
            "call": bayes.call,
            "callProb": bayes.call_prob,
            "passed": bayes.call == "likely pass",
            "accuracy": bayes.accuracy,
            "ciLow": bayes.ci_low,
            "ciHigh": bayes.ci_high,
            "mps": bayes.mps,
            "recall": bayes.recall,
            "firstExposures": bayes.first_exposures,
            "topicsCovered": bayes.topics_covered,
            "topicsTotal": bayes.topics_total,
            "label": bayes.label,
        }
    return payload


def get_cfa_exam_readiness() -> bytes:
    req = frontend_pb2.GetCfaExamReadinessRequest()
    req.ParseFromString(request.data)
    payload = _cfa_exam_readiness_payload(aqt.mw.col, req.deck_id)
    return generic_pb2.Json(json=json.dumps(payload).encode()).SerializeToString()


def _cfa_deadline_payload(col: Collection, deck_id: int) -> dict[str, Any]:
    from anki import cfa
    from aqt.cfa import _sanitized_exam_date

    cfg = cfa.get_exam_config(col) or {}
    # Self-heal an absurd/stale persisted exam date back to the canonical default
    # (mirrors the old Qt dialog's _initial_date heal), and rank due AND new cards
    # so a fresh all-new deck is never a dead-end — both preserved from #17.
    exam_date = _sanitized_exam_date(cfg.get("exam_date"))
    topic_weights = cfg.get("topic_weights", {})

    result = cfa.deadline_retention_with_new(
        col, deck_id=deck_id, exam_date=exam_date, fetch_limit=50
    )
    recalls = list(result.predicted_recall)

    # Never-studied (NEW) cards carry no FSRS memory state, so their predicted
    # exam-day recall is 0.0 BY CONSTRUCTION (see deadline_retention_with_new) —
    # not a genuine "you will forget everything" figure. Flag them so the page
    # renders a calm "New" instead of an alarming warn-orange "0.0%", and never
    # warn-colours a row that only reads 0.0 because it has no data yet.
    from anki import cfa_deadline

    deck_name = col.decks.name(DeckId(int(deck_id)))
    escaped = cfa_deadline._escape_deck_name(deck_name)
    new_set = {int(cid) for cid in col.find_cards(f'deck:"{escaped}" is:new')}

    return {
        "examDate": exam_date,
        "topicWeights": dict(topic_weights),
        "cardCount": len(result),
        "dataSource": "Rust RPC" if result.used_rpc else "read-only fallback",
        "headerMode": "ranked" if len(result) else "empty",
        "rows": [
            {
                "cardId": result.card_ids[i],
                "predictedRecall": recalls[i],
                "suggestedIntervalDays": result.suggested_interval_days[i],
                "isNew": result.card_ids[i] in new_set,
                "warnLowRecall": (
                    result.card_ids[i] not in new_set
                    and recalls[i] < _CFA_DEADLINE_WARN_RECALL
                ),
            }
            for i in range(len(result))
        ],
        "footerText": _CFA_DEADLINE_FOOTER,
    }


def get_cfa_deadline_view() -> bytes:
    req = frontend_pb2.GetCfaDeadlineViewRequest()
    req.ParseFromString(request.data)
    payload = _cfa_deadline_payload(aqt.mw.col, req.deck_id)
    return generic_pb2.Json(json=json.dumps(payload).encode()).SerializeToString()


def set_cfa_exam_date() -> bytes:
    from anki import cfa

    req = frontend_pb2.SetCfaExamDateRequest()
    req.ParseFromString(request.data)
    col = aqt.mw.col
    cfg = cfa.get_exam_config(col) or {}
    cfa.set_exam_config(
        col, exam_date=req.exam_date, topic_weights=cfg.get("topic_weights", {})
    )
    return b""


# CFA fork: the canonical Level II study deck the Home dashboard reports on.
_CFA_HOME_DECK_NAME = "CFA Level II"


def _cfa_scope_name(col: Collection, deck_id: int) -> str:
    """Heading for the readiness / home scope. A real deck id -> that deck's
    name; ``0`` (whole-collection scoring) -> the "CFA Level II" deck name if it
    exists, else the literal, so the overall exam-readiness view is labelled with
    the exam rather than whichever single deck happens to be selected."""
    if deck_id:
        return col.decks.name(DeckId(deck_id))
    did = col.decks.id_for_name(_CFA_HOME_DECK_NAME)
    return col.decks.name(DeckId(did)) if did is not None else _CFA_HOME_DECK_NAME


def _cfa_home_payload(col: Collection) -> dict[str, Any]:
    """The CFA Home dashboard payload: the SAME three honest scores + Bayesian
    hero the Exam Readiness page shows (parity by reuse), plus the exam
    countdown, sync status and the master AI-toggle state for the dashboard
    chrome."""
    from anki import cfa
    from aqt.cfa_sync_connect import sync_status_payload

    # Whole-collection scoring (deck_id=0) so ethics-pair reviews and every other
    # CFA deck impact the Home scores + concept map, matching the phone.
    payload = _cfa_exam_readiness_payload(col, 0)

    cfg = cfa.get_exam_config(col) or {}
    payload["examDate"] = cfg.get("exam_date")
    payload["daysToExam"] = cfa.days_to_exam(col)
    # Master AI state for the Home chip (contract default: ON / AI-first). The
    # Home surface only reports the master state; per-feature toggles live in AI
    # settings. Without an API key, features still degrade deterministically.
    payload["aiEnabled"] = bool(col.get_config("cfa_ai_enabled", True))
    payload["sync"] = sync_status_payload(getattr(aqt, "mw", None))
    return payload


def get_cfa_home_view() -> bytes:
    payload = _cfa_home_payload(aqt.mw.col)
    return generic_pb2.Json(json=json.dumps(payload).encode()).SerializeToString()


post_handler_list = [
    congrats_info,
    get_deck_configs_for_update,
    update_deck_configs,
    get_scheduling_states_with_context,
    set_scheduling_states,
    change_notetype,
    import_done,
    import_csv,
    import_anki_package,
    import_json_file,
    import_json_string,
    search_in_browser,
    deck_options_require_close,
    deck_options_ready,
    save_custom_colours,
    get_cfa_exam_readiness,
    get_cfa_deadline_view,
    set_cfa_exam_date,
    get_cfa_home_view,
]


exposed_backend_list = [
    # CollectionService
    "latest_progress",
    "get_custom_colours",
    # DeckService
    "get_deck_names",
    # I18nService
    "i18n_resources",
    # ImportExportService
    "get_csv_metadata",
    "get_import_anki_package_presets",
    # NotesService
    "get_field_names",
    "get_note",
    # NotetypesService
    "get_notetype_names",
    "get_change_notetype_info",
    # StatsService
    "card_stats",
    "get_review_logs",
    "graphs",
    "get_graph_preferences",
    "set_graph_preferences",
    # TagsService
    "complete_tag",
    # ImageOcclusionService
    "get_image_for_occlusion",
    "add_image_occlusion_note",
    "get_image_occlusion_note",
    "update_image_occlusion_note",
    "get_image_occlusion_fields",
    # SchedulerService
    "compute_fsrs_params",
    "compute_optimal_retention",
    "set_wants_abort",
    "evaluate_params_legacy",
    "get_optimal_retention_parameters",
    "simulate_fsrs_review",
    "simulate_fsrs_workload",
    # DeckConfigService
    "get_ignored_before_count",
    "get_retention_workload",
]


def raw_backend_request(endpoint: str) -> Callable[[], bytes]:
    # check for key at startup
    from anki._backend import RustBackend

    assert hasattr(RustBackend, f"{endpoint}_raw")

    return lambda: getattr(aqt.mw.col._backend, f"{endpoint}_raw")(request.data)


# all methods in here require a collection
post_handlers = {
    stringcase.camelcase(handler.__name__): handler for handler in post_handler_list
} | {
    stringcase.camelcase(handler): raw_backend_request(handler)
    for handler in exposed_backend_list
}


def _extract_collection_post_request(path: str) -> DynamicRequest | NotFound:
    if not aqt.mw.col:
        return NotFound(message=f"collection not open, ignore request for {path}")
    if handler := post_handlers.get(path):
        # convert bytes/None into response
        def wrapped() -> Response:
            try:
                if data := handler():
                    response = flask.make_response(data)
                    response.headers["Content-Type"] = "application/binary"
                else:
                    response = _text_response(HTTPStatus.NO_CONTENT, "")
            except Exception as exc:
                print(traceback.format_exc())
                response = _text_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))
            return response

        return wrapped
    else:
        return NotFound(message=f"{path} not found")


def _check_dynamic_request_permissions():
    if request.method == "GET":
        return

    def warn() -> None:
        show_warning(
            "Unexpected API access. Please report this message on the Anki forums."
        )

    # check content type header to ensure this isn't an opaque request from another origin
    if request.headers["Content-type"] != "application/binary":
        aqt.mw.taskman.run_on_main(warn)
        abort(403)

    # does page have access to entire API?
    if _have_api_access():
        return

    # whitelisted API endpoints for reviewer/previewer
    if request.path in (
        "/_anki/getSchedulingStatesWithContext",
        "/_anki/setSchedulingStates",
        "/_anki/i18nResources",
        "/_anki/congratsInfo",
        # CFA fork: the Home dashboard renders in the main webview (kind MAIN,
        # no API token), so its read-only score payload is whitelisted here —
        # exactly like congratsInfo.
        "/_anki/getCfaHomeView",
    ):
        pass
    else:
        # other legacy pages may contain third-party JS, so we do not
        # allow them to access our API
        aqt.mw.taskman.run_on_main(warn)
        abort(403)


def _handle_dynamic_request(req: DynamicRequest) -> Response:
    _check_dynamic_request_permissions()
    try:
        return req()
    except Exception as e:
        return _text_response(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))


def legacy_page_data() -> Response:
    id = int(request.args["id"])
    page = aqt.mw.mediaServer.get_page(id)
    if page:
        response = Response(page.html, mimetype="text/html")
        # Prevent JS in field content from being executed in the editor, as it would
        # have access to our internal API, and is a security risk.
        if page.context == PageContext.EDITOR:
            response.headers["Content-Security-Policy"] = (
                _editor_content_security_policy(aqt.mw.mediaServer.getPort())
            )
        return response
    else:
        return _text_response(HTTPStatus.NOT_FOUND, "page not found")


_APIKEY = secrets.token_urlsafe(32)


def _have_api_access() -> bool:
    return (
        request.headers.get("Authorization") == f"Bearer {_APIKEY}"
        or os.environ.get("ANKI_API_HOST") == "0.0.0.0"
    )


# this currently only handles a single method; in the future, idempotent
# requests like i18nResources should probably be moved here
def _extract_dynamic_get_request(path: str) -> DynamicRequest | None:
    if path == "legacyPageData":
        return legacy_page_data
    else:
        return None
