import re as _re
import sys as _sys
import warnings as _warnings
from math import inf as _inf
from typing import (
    ClassVar as _ClassVar,
    Dict as _Dict,
    List as _List,
    Optional as _Optional,
    Pattern as _Pattern,
    Tuple as _Tuple,
    Union as _Union,
)


MIN_PYTHON_VERSION = (3, 8, 1)

__all__ = [
    "MIN_PYTHON_VERSION",
    "__version__",
    "version_info",
    "VersionInfo",
    "_update_event_loop_policy",
]
if _sys.version_info < MIN_PYTHON_VERSION:
    print(
        f"Python {'.'.join(map(str, MIN_PYTHON_VERSION))} is required to run Red, but you have "
        f"{_sys.version}! Please update Python."
    )
    _sys.exit(1)


class VersionInfo:
    ALPHA = "alpha"
    BETA = "beta"
    RELEASE_CANDIDATE = "release candidate"
    FINAL = "final"

    _VERSION_STR_PATTERN: _ClassVar[_Pattern[str]] = _re.compile(
        r"^"
        r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<micro>0|[1-9]\d*)"
        r"(?:(?P<releaselevel>a|b|rc)(?P<serial>0|[1-9]\d*))?"
        r"(?:\.post(?P<post_release>0|[1-9]\d*))?"
        r"(?:\.dev(?P<dev_release>0|[1-9]\d*))?"
        r"(?:\+(?P<local_version>g[a-z0-9]+(?:\.dirty)?))?"
        r"$",
        flags=_re.IGNORECASE,
    )
    _RELEASE_LEVELS: _ClassVar[_List[str]] = [ALPHA, BETA, RELEASE_CANDIDATE, FINAL]
    _SHORT_RELEASE_LEVELS: _ClassVar[_Dict[str, str]] = {
        "a": ALPHA,
        "b": BETA,
        "rc": RELEASE_CANDIDATE,
    }

    def __init__(
        self,
        major: int,
        minor: int,
        micro: int,
        releaselevel: str,
        serial: _Optional[int] = None,
        post_release: _Optional[int] = None,
        dev_release: _Optional[int] = None,
        local_version: _Optional[str] = None,
    ) -> None:
        self.major: int = major
        self.minor: int = minor
        self.micro: int = micro

        if releaselevel not in self._RELEASE_LEVELS:
            raise TypeError(f"'releaselevel' must be one of: {', '.join(self._RELEASE_LEVELS)}")

        self.releaselevel: str = releaselevel
        self.serial: _Optional[int] = serial
        self.post_release: _Optional[int] = post_release
        self.dev_release: _Optional[int] = dev_release
        self.local_version: _Optional[str] = local_version

    @property
    def short_commit_hash(self) -> _Optional[str]:
        if self.local_version is None:
            return None
        return self.local_version[1:].split(".", 1)[0]

    @property
    def dirty(self) -> bool:
        return self.local_version is not None and self.local_version.endswith(".dirty")

    @classmethod
    def from_str(cls, version_str: str) -> "VersionInfo":
        """Parse a string into a VersionInfo object.

        Raises
        ------
        ValueError
            If the version info string is invalid.

        """
        match = cls._VERSION_STR_PATTERN.match(version_str)
        if not match:
            raise ValueError(f"Invalid version string: {version_str}")

        kwargs: _Dict[str, _Union[str, int]] = {}
        for key in ("major", "minor", "micro"):
            kwargs[key] = int(match[key])
        releaselevel = match["releaselevel"]
        if releaselevel is not None:
            kwargs["releaselevel"] = cls._SHORT_RELEASE_LEVELS[releaselevel]
        else:
            kwargs["releaselevel"] = cls.FINAL
        for key in ("serial", "post_release", "dev_release"):
            if match[key] is not None:
                kwargs[key] = int(match[key])
        kwargs["local_version"] = match["local_version"]
        return cls(**kwargs)

    @classmethod
    def from_json(
        cls, data: _Union[_Dict[str, _Union[int, str]], _List[_Union[int, str]]]
    ) -> "VersionInfo":
        if isinstance(data, _List):
            # For old versions, data was stored as a list:
            # [MAJOR, MINOR, MICRO, RELEASELEVEL, SERIAL]
            return cls(*data)
        else:
            return cls(**data)

    def to_json(self) -> _Dict[str, _Union[int, str]]:
        return {
            "major": self.major,
            "minor": self.minor,
            "micro": self.micro,
            "releaselevel": self.releaselevel,
            "serial": self.serial,
            "post_release": self.post_release,
            "dev_release": self.dev_release,
            "local_version": self.local_version,
        }

    def _generate_comparison_tuples(
        self, other: "VersionInfo"
    ) -> _List[
        _Tuple[int, int, int, int, _Union[int, float], _Union[int, float], _Union[int, float], int]
    ]:
        tups: _List[
            _Tuple[
                int, int, int, int, _Union[int, float], _Union[int, float], _Union[int, float], int
            ]
        ] = []
        for obj in (self, other):
            tups.append(
                (
                    obj.major,
                    obj.minor,
                    obj.micro,
                    obj._RELEASE_LEVELS.index(obj.releaselevel),
                    obj.serial if obj.serial is not None else _inf,
                    obj.post_release if obj.post_release is not None else -_inf,
                    obj.dev_release if obj.dev_release is not None else _inf,
                    int(obj.dirty),
                )
            )
        return tups

    def __lt__(self, other: "VersionInfo") -> bool:
        tups = self._generate_comparison_tuples(other)
        return tups[0] < tups[1]

    def __eq__(self, other: "VersionInfo") -> bool:
        tups = self._generate_comparison_tuples(other)
        return tups[0] == tups[1]

    def __le__(self, other: "VersionInfo") -> bool:
        tups = self._generate_comparison_tuples(other)
        return tups[0] <= tups[1]

    def __str__(self) -> str:
        ret = f"{self.major}.{self.minor}.{self.micro}"
        if self.releaselevel != self.FINAL:
            short = next(
                k for k, v in self._SHORT_RELEASE_LEVELS.items() if v == self.releaselevel
            )
            ret += f"{short}{self.serial}"
        if self.post_release is not None:
            ret += f".post{self.post_release}"
        if self.dev_release is not None:
            ret += f".dev{self.dev_release}"
        if self.local_version is not None:
            ret += f"+{self.local_version}"
        return ret

    def __repr__(self) -> str:
        return (
            "VersionInfo(major={major}, minor={minor}, micro={micro}, "
            "releaselevel={releaselevel}, serial={serial}, post={post_release}, "
            "dev={dev_release}, local={local_version})"
        ).format(**self.to_json())

    @classmethod
    def _get_version(cls, *, ignore_installed: bool = False) -> _Tuple[str, "VersionInfo"]:
        if not _VERSION.endswith(".dev1"):
            return _VERSION, cls.from_str(_VERSION)
        try:
            import os

            path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            # we only want to do this for editable installs
            if not os.path.exists(os.path.join(path, ".git")):
                raise RuntimeError("not a git repository")

            import subprocess

            output = subprocess.check_output(
                ("git", "describe", "--tags", "--long", "--dirty"),
                stderr=subprocess.DEVNULL,
                cwd=path,
            )
            _, count, commit, *dirty = output.decode("utf-8").strip().split("-", 3)
            dirty_suffix = f".{dirty[0]}" if dirty else ""
            ver = f"{_VERSION[:-1]}{count}+{commit}{dirty_suffix}"
            return ver, cls.from_str(ver)
        except Exception:
            # `ignore_installed` is `True` when building with setuptools.
            if ignore_installed:
                # we don't want any failure to raise here but we should print it
                import traceback

                traceback.print_exc()
            else:
                try:
                    from importlib.metadata import version

                    ver = version("Red-DiscordBot")
                    return ver, cls.from_str(ver)
                except Exception:
                    # we don't want any failure to raise here but we should print it
                    import traceback

                    traceback.print_exc()

        return _VERSION, cls.from_str(_VERSION)


def _update_event_loop_policy():
    if _sys.implementation.name == "cpython":
        # Let's not force this dependency, uvloop is much faster on cpython
        try:
            import uvloop
        except ImportError:
            pass
        else:
            import asyncio

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())


def _ensure_no_colorama():
    # a hacky way to ensure that nothing initialises colorama
    # if we're not running with legacy Windows command line mode
    from rich.console import detect_legacy_windows

    if not detect_legacy_windows():
        import colorama
        import colorama.initialise

        colorama.deinit()

        def _colorama_wrap_stream(stream, *args, **kwargs):
            return stream

        colorama.wrap_stream = _colorama_wrap_stream
        colorama.initialise.wrap_stream = _colorama_wrap_stream


def _update_logger_class():
    from red_commons.logging import maybe_update_logger_class

    maybe_update_logger_class()


def _early_init():
    # This function replaces logger so we preferrably (though not necessarily) want that to happen
    # before importing anything that calls `logging.getLogger()`, i.e. `asyncio`.
    _update_logger_class()
    _update_event_loop_policy()
    _ensure_no_colorama()


# This is bumped automatically by release workflow (`.github/workflows/scripts/bump_version.py`)
_VERSION = "3.5.0.dev1"

__version__, version_info = VersionInfo._get_version()

# Filter fuzzywuzzy slow sequence matcher warning
_warnings.filterwarnings("ignore", module=r"fuzzywuzzy.*")
# Show DeprecationWarning
_warnings.filterwarnings("default", category=DeprecationWarning)

# TODO: Rearrange cli flags here and use the value instead of this monkeypatch
if not any(_re.match("^-(-debug|d+|-verbose|v+)$", i) for i in _sys.argv):
    # DEP-WARN
    # Individual warnings - tracked in https://github.com/Cog-Creators/Red-DiscordBot/issues/3529
    # DeprecationWarning: an integer is required (got type float).  Implicit conversion to integers using __int__ is deprecated, and may be removed in a future version of Python.
    _warnings.filterwarnings("ignore", category=DeprecationWarning, module="importlib", lineno=219)
    # DeprecationWarning: The loop argument is deprecated since Python 3.8, and scheduled for removal in Python 3.10
    #   stdin, stdout, stderr = await tasks.gather(stdin, stdout, stderr,
    # this is a bug in CPython
    _warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        module="asyncio",
        message="The loop argument is deprecated since Python 3.8",
    )