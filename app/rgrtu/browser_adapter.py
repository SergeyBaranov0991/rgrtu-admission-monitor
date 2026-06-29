from __future__ import annotations


class BrowserAdapterUnavailable(RuntimeError):
    pass


class RgrtuBrowserAdapter:
    async def fetch(self, *_args, **_kwargs) -> None:
        raise BrowserAdapterUnavailable(
            "Playwright fallback is intentionally not wired into MVP code yet. "
            "Use discovery docs before enabling browser fetches."
        )

