from pathlib import Path


class FakePage:
    def set_content(self, html: str, wait_until: str) -> None:
        self.html = html
        self.wait_until = wait_until

    def screenshot(self, *, path: str, type: str, full_page: bool) -> None:
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\nposter")


class FakeBrowser:
    def new_page(self, *, viewport: dict[str, int], device_scale_factor: int) -> FakePage:
        self.viewport = viewport
        self.device_scale_factor = device_scale_factor
        return FakePage()

    def close(self) -> None:
        return None


class FakePlaywright:
    chromium = type("Chromium", (), {"launch": staticmethod(lambda **kwargs: FakeBrowser())})()

    def __enter__(self) -> "FakePlaywright":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None
