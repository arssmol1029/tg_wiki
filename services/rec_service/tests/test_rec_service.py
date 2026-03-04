import pytest

from rec_service.rec.rec_service import (
    RecService,
    RecServiceConfig,
    UserProvisionFailed,
)
from rec_service.domain.vector import VECTOR_DIM


@pytest.mark.asyncio
async def test_get_user_pref_existing_returns_preference_vector(
    dummy_uow_factory, dummy_user_repo
):
    users = dummy_user_repo
    users.get_user_pref.return_value = [0.0] * VECTOR_DIM

    svc = RecService(
        uow_factory=lambda: dummy_uow_factory(users=users),  # type: ignore
        cfg=RecServiceConfig(calibration_size=7),
    )

    pref = await svc.get_user_pref(user_id=1)
    assert pref is not None
    assert len(pref.data) == VECTOR_DIM


@pytest.mark.asyncio
async def test_get_user_pref_creates_user_when_missing(
    dummy_uow_factory, dummy_user_repo
):
    users = dummy_user_repo
    users.get_user_pref.return_value = None
    users.create_user.return_value = True

    svc = RecService(
        uow_factory=lambda: dummy_uow_factory(users=users),  # type: ignore
        cfg=RecServiceConfig(calibration_size=11),
    )

    pref = await svc.get_user_pref(user_id=10)

    users.create_user.assert_awaited_once_with(user_id=10, calibration_size=11)
    assert pref is not None
    assert all(x == 0.0 for x in pref.data)


@pytest.mark.asyncio
async def test_get_user_pref_create_fails_raises(dummy_uow_factory, dummy_user_repo):
    users = dummy_user_repo
    users.get_user_pref.return_value = None
    users.create_user.return_value = False

    svc = RecService(
        uow_factory=lambda: dummy_uow_factory(users=users),  # type: ignore
        cfg=RecServiceConfig(calibration_size=5),
    )

    with pytest.raises(UserProvisionFailed):
        await svc.get_user_pref(user_id=1)


@pytest.mark.asyncio
async def test_update_user_pref_passes_vector_data(dummy_uow_factory, dummy_user_repo):
    users = dummy_user_repo
    users.update_user_pref.return_value = True

    svc = RecService(uow_factory=lambda: dummy_uow_factory(users=users), cfg=RecServiceConfig())  # type: ignore

    from rec_service.domain.preference import Preference

    ok = await svc.update_user_pref(user_id=123, pref=Preference())

    assert ok is True
    users.update_user_pref.assert_awaited()
