"""
SiteHitMiddleware — lightweight request counter.

Increments a simple in-memory hit counter per process (useful for health
checks). Does not perform any database writes.
"""


class SiteHitMiddleware:
    _hit_count = 0

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        SiteHitMiddleware._hit_count += 1
        response = self.get_response(request)
        return response

    @classmethod
    def hit_count(cls) -> int:
        return cls._hit_count
