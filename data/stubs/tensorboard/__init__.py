"""Minimal no-op tensorboard stub for local fine-tuning without the package."""
class _W:
    def __init__(self, *a, **k): pass
    def add_scalar(self, *a, **k): pass
    def add_image(self, *a, **k): pass
    def flush(self): pass
    def close(self): pass
