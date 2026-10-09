"""Running the external programs: git, curl, the Shopify CLI and pnpm.

Every child gets stdin from /dev/null, so a prompt fails fast instead of
hanging, and a timeout, so a stuck tool cannot hold the invocation forever.
"""

import os
import shutil
import signal
import subprocess
import tempfile

from tuner.output import Failed


def require(tool):
    path = shutil.which(tool)
    if path is None:
        raise Failed("missing-tool", "`%s` is not on PATH" % tool)
    return path


def run(argv, cwd=None, env=None, timeout=120, errors=None):
    """The finished child, its output as text; `errors="replace"` reads bytes that are not
    UTF-8 rather than failing on them."""
    require(argv[0])
    try:
        return subprocess.run(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                              capture_output=True, text=True, errors=errors, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise Failed("timeout", "`%s` did not finish within %d s" % (argv[0], timeout))


def capture(argv, cwd=None, env=None, timeout=120):
    """(its exit code, or None when it was stopped at `timeout`; its output, both streams in
    the order written, as text). For a child that runs the repo's hooks.

    The output goes to a file, never a pipe: Node writes to a pipe without waiting, on
    macOS, so a Node tool that exits straight after printing (`shopify theme check`) loses
    everything past the pipe's first 64 KB, its summary with it. The child leads a process
    group of its own, so stopping it at the time limit stops the hook's own children too.
    """
    require(argv[0])
    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=out,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
            code = None
        out.seek(0)
        return code, out.read().decode("utf-8", "replace")


def child_env(**extra):
    """The program's environment, minus whatever could steer a child to the wrong target.

    `SHOPIFY_FLAG_*` would silently add CLI flags (a store, a theme, `--live`),
    and `SHOPIFY_CLI_THEME_TOKEN` would swap the developer's login for another.
    """
    env = {k: v for k, v in os.environ.items()
           if not k.startswith("SHOPIFY_FLAG_") and k != "SHOPIFY_CLI_THEME_TOKEN"}
    env.update({k: str(v) for k, v in extra.items()})
    return env
