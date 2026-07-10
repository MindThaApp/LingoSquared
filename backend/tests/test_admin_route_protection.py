"""Standing regression guard: every admin route must enforce admin auth.

Enumerates admin routes programmatically off FastAPI's own route table
(``app.routes``) rather than a hand-maintained list, so any FUTURE
``/admin/*`` route (or a handler named ``admin_*`` mounted elsewhere) is
covered automatically the moment it's added -- same spirit as
``test_no_dead_models.py``'s introspection-based guard. Two layers:

1. Structural: every enumerated route must have ``app.api.deps.admin_user``
   somewhere in its dependency tree (checked via ``route.dependant``, the
   exact object FastAPI resolves at request time -- not a source-text grep).
2. Behavioral: every enumerated route must actually return 401 for an
   unauthenticated request and 403 for an authenticated NON-admin user,
   proving the dependency fires before any handler/body logic runs.

If a new admin endpoint is added without ``Depends(admin_user)``, both
layers fail loudly with the exact method+path.
"""

import re

from fastapi.routing import APIRoute

from app.api.deps import admin_user
from app.main import app


def _iter_api_routes(routes, prefix=""):
    """Yield (full_path, APIRoute) for every route reachable from `routes`.

    fastapi==0.139.0 (this project's pinned version, see CLAUDE.md's
    Starlette CVE bump entry) does NOT flatten include_router() into plain
    APIRoute objects on app.routes -- each app.include_router() call shows
    up as an opaque `fastapi.routing._IncludedRouter` wrapper instead,
    exposing the real APIRouter via `.original_router` and the prefix that
    call was given via `.include_context.prefix` (confirmed live: this
    app's two `app.include_router(router, ...)` calls in app/main.py, one
    with prefix="/v1" and one with prefix="", each produce one
    `_IncludedRouter` wrapping the SAME 53-route `router` object). Walk
    those recursively (and classic Mounts with a plain `.routes` list, for
    resilience against future refactors) so this enumeration keeps seeing
    every real route regardless of how routers are nested or mounted.
    """
    for route in routes:
        if isinstance(route, APIRoute):
            yield prefix + route.path, route
            continue
        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            inner_prefix = getattr(getattr(route, "include_context", None), "prefix", "") or ""
            yield from _iter_api_routes(original_router.routes, prefix + inner_prefix)
            continue
        sub_routes = getattr(route, "routes", None)
        if sub_routes is not None:
            yield from _iter_api_routes(sub_routes, prefix + getattr(route, "path", ""))


def _admin_routes():
    """Every (method, path, route) that is admin-scoped by path or handler name.

    The app mounts the same router twice (bare and under /v1) -- both are
    real, reachable surfaces, so both are enumerated and tested.
    """
    found = []
    for path, route in _iter_api_routes(app.routes):
        path_is_admin = re.search(r"(^|/)admin(/|$)", path)
        name_is_admin = "admin" in route.endpoint.__name__.lower()
        if not (path_is_admin or name_is_admin):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            found.append((method, path, route))
    return found


def _has_admin_dependency(dependant):
    for dep in dependant.dependencies:
        if dep.call is admin_user or _has_admin_dependency(dep):
            return True
    return False


def _concrete_url(path):
    # Substitute every {param} with a dummy value: admin_user must reject
    # the request before any param is ever looked up, so the value is moot.
    return re.sub(r"\{[^}]+\}", "test-id", path)


def test_admin_route_enumeration_is_not_empty():
    """Guards the guard: if the filter ever silently matches nothing (e.g. a
    router-mounting refactor), the other tests would vacuously pass."""
    paths = {path for _, path, _ in _admin_routes()}
    assert "/admin/content/import" in paths
    assert "/v1/admin/content/import" in paths
    # 11 admin endpoints x 2 mounts as of 2026-07-10; only ever grows.
    assert len(paths) >= 20


def test_every_admin_route_declares_admin_user_dependency():
    unprotected = [
        f"{method} {path}"
        for method, path, route in _admin_routes()
        if not _has_admin_dependency(route.dependant)
    ]
    assert not unprotected, (
        "Admin routes missing Depends(admin_user) -- this is a real "
        f"privilege-escalation hole, not a style issue: {unprotected}"
    )


def test_admin_routes_reject_unauthenticated_requests(client):
    failures = []
    for method, path, _ in _admin_routes():
        response = client.request(method, _concrete_url(path))
        if response.status_code != 401:
            failures.append(f"{method} {path} -> {response.status_code}")
    assert not failures, f"Expected 401 without a token: {failures}"


def test_admin_routes_reject_authenticated_non_admin(client, auth):
    failures = []
    for method, path, _ in _admin_routes():
        response = client.request(method, _concrete_url(path), headers=auth)
        if response.status_code != 403:
            failures.append(f"{method} {path} -> {response.status_code}")
    assert not failures, (
        "Expected 403 (admin_required) for a non-admin user -- any other "
        f"status means the admin gate did not fire first: {failures}"
    )


def test_admin_routes_permit_admin_user(client, admin):
    """Complement check: the gate blocks non-admins, not everyone. A real
    admin must never see 401/403 from these routes (other statuses -- 200,
    404 for the dummy path param, 422 for a missing body -- are fine here;
    functional behavior is covered by each feature's own tests)."""
    failures = []
    for method, path, _ in _admin_routes():
        response = client.request(method, _concrete_url(path), headers=admin)
        if response.status_code in (401, 403):
            failures.append(f"{method} {path} -> {response.status_code}")
    assert not failures, f"Admin was wrongly rejected: {failures}"
