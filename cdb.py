#
# Copyright (c) 2026 Huang Qinjin (huangqinjin@gmail.com)
#
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE_1_0.txt or copy at
#          https://www.boost.org/LICENSE_1_0.txt)
#
import contextlib
from enum import StrEnum
from loguru import logger
import os
import regex
import string
import subprocess
import sys
import time
import win32file
import yaml


class BracedTemplate(string.Template):
    """A ``string.Template`` that recognizes ``${name}`` and nothing else.
    Bare ``$name`` and the ``$$`` escape are deliberately left to the text.
    """

    pattern = r"""
        \$(?:
          (?P<escaped>(?!x)x)                      |
          (?P<named>(?!x)x)                        |
          \{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}   |
          (?P<invalid>(?!x)x)
        )
    """

    def __init__(self, template: str, mapping: dict | None = None):
        super().__init__(template)
        self.mapping = mapping

    def __str__(self) -> str:
        return self.substitute(self.mapping or {})


class EventStatus(StrEnum):
    IGNORE = "ignore"
    OUTPUT = "output"
    BREAK = "break"
    SECOND_BREAK = "break2"


class SpecError(Exception):
    pass


class Step:
    def __init__(self, index: int, run: str, timeout: int, output: regex.Pattern):
        self.index = index
        self.run = run
        self.timeout = timeout
        self.output = output
        self.label = f"{index:04d}"
        self.script_name = f"{self.label}.txt"
        self.log_name = f"{self.label}.log"
        # .logopen/.logclose are logged as they run, so they delimit the region
        # the step's run lines produced.
        self.open = f"Opened log file '{self.log_name}'"
        self.close = f"Closing open log file {self.log_name}"

    def script(self) -> str:
        return f".logopen {self.log_name}\n{self.run}\n.logclose\n"


class Spec:
    def __init__(self, path: str, mapping: dict = {}):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except OSError as e:
            raise SpecError(f"cannot read spec {path}: {e}")
        except yaml.YAMLError as e:
            raise SpecError(f"cannot parse spec {path}: {e}")

        self.where = ""
        self.mapping = mapping

        self.target = self._str(data, "target")
        self.is_64bit = True

        try:
            if win32file.GetBinaryType(self.target) == 0:
                self.is_64bit = False
        except:
            pass

        self.debugger = self._str(data, "debugger", "cdbX64" if self.is_64bit else "cdbX86")
        self.attach = self._bool(data, "attach", False)
        self.detach = self._bool(data, "detach", False)

        events = self._dict(data, "events", {})
        self.where = "events"
        self._events(events)

        self.where = ""
        steps = self._list(data, "steps", [])
        self.where = "steps"
        self.steps = [ self._step(index, node) for index, node in enumerate(steps, 1) ]

        del self.where
        del self.mapping

    def cmd(self) -> list[str]:
        event_status_opts = {
            EventStatus.IGNORE: "-xi",
            EventStatus.OUTPUT: "-xn",
            EventStatus.BREAK: "-xe",
            EventStatus.SECOND_BREAK: "-xd",
        }

        args = [ self.debugger ]
        if self.detach: args.append("-pd")
        if self.initial_breakpoint in (EventStatus.IGNORE, EventStatus.OUTPUT): args.append("-g")
        if self.final_breakpoint in (EventStatus.IGNORE, EventStatus.OUTPUT): args.append("-G")

        args.extend([ event_status_opts[self.load_module], "ld" ])
        args.extend([ event_status_opts[self.unload_module], "ud" ])

        if self.attach: args.append("-pn")
        args.append(self.target)
        return args

    def _events(self, data: dict):
        def _status(key: str, default: EventStatus):
            try:
                value = data.get(key)
                if value is None: return default
                return EventStatus(value)
            except ValueError:
                where = key if self.where == "" else self.where + "." + key
                raise SpecError(f"{where}: valid values are {[x.value for x in EventStatus]}")

        self.initial_breakpoint = _status("initial_breakpoint", EventStatus.IGNORE)
        self.final_breakpoint = _status("final_breakpoint", EventStatus.IGNORE)
        self.load_module = _status("load_module", EventStatus.IGNORE)
        self.unload_module = _status("unload_module", EventStatus.IGNORE)

    def _dict(self, data: dict, key: str, default: dict | None = None) -> dict:
        value = data.get(key, default)
        where = key if self.where == "" else self.where + "." + key
        if not isinstance(value, dict):
            raise SpecError(f"{where}: expected a dict")
        return value

    def _list(self, data: dict, key: str, default: list | None = None) -> list[str]:
        value = data.get(key, default)
        where = key if self.where == "" else self.where + "." + key
        if not isinstance(value, list):
            raise SpecError(f"{where}: expected a list")
        return value

    def _str(self, data: dict, key: str, default: str | None = None) -> str:
        value = data.get(key, default)
        where = key if self.where == "" else self.where + "." + key
        if not isinstance(value, str):
            raise SpecError(f"{where}: expected a string")
        try:
            return str(BracedTemplate(value, self.mapping))
        except Exception as e:
            raise SpecError(f"{where}: malformed template: {e}")

    def _int(self, data: dict, key: str, default: int | None = None) -> int:
        value = data.get(key, default)
        where = key if self.where == "" else self.where + "." + key
        if not isinstance(value, int):
            raise SpecError(f"{where}: expected an integer")
        return value

    def _bool(self, data: dict, key: str, default: bool | None = None) -> bool:
        value = data.get(key, default)
        where = key if self.where == "" else self.where + "." + key
        if not isinstance(value, bool):
            raise SpecError(f"{where}: expected true or false")
        return value

    def _step(self, index: int, data: dict) -> Step:
        where = f"{self.where}[{index}]"
        run = self._str(data, "run").strip()
        timeout = self._int(data, "timeout", 10)
        output = self._str(data, "output").strip()

        try:
            pattern = regex.compile(output)
        except regex.error as e:
            raise SpecError(f"{where}.output: invalid regex: {e}")

        return Step(index, run, timeout, pattern)

class Session(contextlib.AbstractContextManager):
    def __init__(self, argv: list[str], verbose: bool = False):
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.STDOUT if verbose else subprocess.DEVNULL,
            stderr=subprocess.STDERR if verbose else subprocess.DEVNULL,
        )

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def wait(self, predicate, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        while True:
            if predicate():
                return True
            if time.monotonic() >= deadline:
                return False
            if self.proc.poll() is not None:
                return predicate()
            time.sleep(0.05)

    def send(self, line: str):
        stream = self.proc.stdin
        stream.write(line.encode("utf-8") + b"\n")
        stream.flush()

    def close(self):
        if self.proc.poll() is None:
            try:
                self.send("q")
            except (OSError, ValueError):
                pass
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                try:
                    self.proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    pass
        if self.proc.stdin is not None:
            try:
                self.proc.stdin.close()
            except OSError:
                pass

    def exec(self, step: Step):
        script_path = step.script_name
        log_path = step.log_name
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(step.script())
        try:
            os.remove(log_path)
        except FileNotFoundError:
            pass

        def check_log():
            try:
                with open(log_path, "rb") as f:
                    end = step.close.encode("utf-8") + b"\r\n"
                    f.seek(-len(end), os.SEEK_END)
                    return end == f.read()
            except OSError:
                pass
            return False

        logger.debug(t"step {step.index}: script\n{step.run}")
        self.send(f"$$><{step.script_name}")
        if not self.wait(check_log, step.timeout):
            logger.error(t"step {step.index}: {step.log_name} is not closed within {step.timeout:g}s")
            return 1

        with open(log_path, "r") as f:
            log_content = f.read().strip()

        if not log_content.startswith(step.open):
            logger.error(t"step {step.index}: output does not start with: {step.open}")
            return 1

        if not log_content.endswith(step.close):
            logger.error(t"step {step.index}: output does not end with: {step.close}")
            return 1

        log_content = log_content[len(step.open) : -len(step.close)].strip()
        logger.debug(t"step {step.index}: output\n{log_content}")
        if not regex.search(step.output, log_content):
            logger.error(t"step {step.index}: output does not match expected pattern")
            return 1

        return 0

    def run(self, spec: Spec):
        for step in spec.steps:
            started = time.monotonic()
            logger.trace(t"step {step.index}: {step.script_name}")
            if self.exec(step) != 0: return 1
            logger.info(t"step {step.index}/{len(spec.steps)} ok ({time.monotonic() - started:.2f}s)")
        logger.success(t"all {len(spec.steps)} step(s) passed")
        return 0


def main(argv: list[str]) -> int:
    mapping = {
        "cwd": os.path.join(os.getcwd(), ""),
        "ext": os.path.join(os.path.dirname(__file__), ""),
    }

    try:
        spec = Spec(argv[0], mapping)
        cmd = spec.cmd()
        logger.debug(t"debugger: {cmd}")
        with Session(cmd) as session:
            return session.run(spec)
    except SpecError:
        logger.exception("spec error")
        return 2
    except Exception:
        logger.exception("unexcepted error")
        return 3

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
