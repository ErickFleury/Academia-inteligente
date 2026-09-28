import pytest
from test_clients import AsgiClient, FakeIdentityProvider
from test_progress_updates import client
from test_progress_updates import session as session

from app.database import get_database_session
from app.main import create_app
from app.modules.identity import router as identity_router
from app.modules.identity.service import AuthenticatedIdentity
from app.modules.social.models import ClientFollow
from app.modules.social.service import SocialForbiddenError, SocialService


@pytest.mark.parametrize("direction", ["followers", "following"])
def test_lists_include_only_active_profiles_available_to_the_viewer(session, direction):
    service = SocialService()
    clients = {
        name: client(session, name)
        for name in ("owner", "public", "accepted", "hidden", "inactive", "disabled")
    }
    profiles = {name: service.own_profile(session, name).profile for name in clients}
    for name in ("accepted", "hidden"):
        profiles[name].visible_to_clients = False
    clients["inactive"].active = False
    clients["disabled"].account.account_active = False
    for name in ("public", "accepted", "hidden", "inactive", "disabled"):
        session.add(
            ClientFollow(
                follower_client_id=clients[name].id, followed_client_id=clients["owner"].id
            )
        )
        if direction == "following":
            session.add(
                ClientFollow(
                    follower_client_id=clients["owner"].id, followed_client_id=clients[name].id
                )
            )
    if direction == "followers":
        session.add(
            ClientFollow(
                follower_client_id=clients["owner"].id, followed_client_id=clients["accepted"].id
            )
        )
    session.commit()
    # A different viewer follows only the approved private profile, regardless
    # of which graph direction is being viewed.
    viewer = client(session, "viewer")
    service.own_profile(session, "viewer")
    session.add(
        ClientFollow(follower_client_id=viewer.id, followed_client_id=clients["accepted"].id)
    )
    session.commit()
    result = service.profiles(session, "viewer", profiles["owner"].id, direction, 0, 20)
    assert {view.client.name for view in result} == {"public", "accepted"}


def test_private_graph_is_limited_to_owner_and_accepted_followers(session):
    service = SocialService()
    owner = client(session, "owner")
    viewer = client(session, "viewer")
    profile = service.own_profile(session, "owner").profile
    service.own_profile(session, "viewer")
    profile.visible_to_clients = False
    session.commit()
    assert service.profiles(session, "owner", profile.id, "followers", 0, 20) == []
    with pytest.raises(SocialForbiddenError):
        service.profiles(session, "viewer", profile.id, "followers", 0, 20)
    session.add(ClientFollow(follower_client_id=viewer.id, followed_client_id=owner.id))
    session.commit()
    assert [
        v.client.id for v in service.profiles(session, "viewer", profile.id, "followers", 0, 20)
    ] == [viewer.id]


def test_pagination_keeps_same_name_profiles_in_stable_order(session):
    service = SocialService()
    owner = client(session, "owner")
    profile = service.own_profile(session, "owner").profile
    members = []
    for name in ("one", "two", "three"):
        member = client(session, name)
        service.own_profile(session, name)
        member.name = "Same name"
        members.append(member.id)
        session.add(ClientFollow(follower_client_id=member.id, followed_client_id=owner.id))
    session.commit()
    first = service.profiles(session, "owner", profile.id, "followers", 0, 2)
    second = service.profiles(session, "owner", profile.id, "followers", 2, 2)
    assert [v.client.id for v in first + second] == sorted(members)


def test_graph_api_projection_permissions_and_pagination_bounds(session, monkeypatch):
    service = SocialService()
    owner, other = client(session, "owner"), client(session, "other")
    profile = service.own_profile(session, "owner").profile
    other_profile = service.own_profile(session, "other").profile
    session.add(ClientFollow(follower_client_id=other.id, followed_client_id=owner.id))
    session.commit()
    app = create_app()
    app.dependency_overrides[get_database_session] = lambda: session
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("owner", None, ("client",))),
    )
    http = AsgiClient(app)
    path = f"/social-profiles/profiles/{profile.id}/graph/followers"
    response = http.get(path)
    assert response.status_code == 200
    assert response.json() == [
        {"id": str(other_profile.id), "name": "other", "nickname": None, "has_image": False}
    ]
    for query in ("?offset=-1", "?limit=0", "?limit=51"):
        assert http.request("GET", path + query).status_code == 422
    monkeypatch.setattr(
        identity_router,
        "identity_provider",
        FakeIdentityProvider(AuthenticatedIdentity("admin", None, ("admin",))),
    )
    assert http.get(path).status_code == 403
