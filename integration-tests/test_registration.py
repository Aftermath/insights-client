import os
import pytest
from pytest_client_tools.util import Version
from pytest_client_tools import test_config

pytestmark = pytest.mark.usefixtures("register_subman")

MACHINE_ID_FILE: str = "/etc/insights-client/machine-id"


def test_machineid_exists_only_when_registered(insights_client):
    """`machine-id` is only present when insights-client is registered."""
    assert not insights_client.is_registered
    assert not os.path.exists(MACHINE_ID_FILE)

    res = insights_client.run(check=False)
    assert (
        "This host has not been registered. Use --register to register this host."
    ) in res.stdout
    assert res.returncode != 0
    assert not os.path.exists(MACHINE_ID_FILE)

    insights_client.register()
    assert os.path.exists(MACHINE_ID_FILE)

    insights_client.unregister()
    assert not os.path.exists(MACHINE_ID_FILE)


def test_machineid_stays_unchanged_on_new_registration_with_subman(insights_client):
    """machine-id content changes when insights-client is un- & registered."""
    insights_client.register()
    with open(MACHINE_ID_FILE, "r") as f:
        machine_id_old = f.read()

    insights_client.unregister()
    assert not os.path.exists(MACHINE_ID_FILE)

    insights_client.register()
    with open(MACHINE_ID_FILE, "r") as f:
        machine_id_new = f.read()

    if insights_client.core_version >= Version(3, 3, 13):
        """after the new changes to CCT-161 machine-id stays the same after un- & re-registration"""
        assert machine_id_new == machine_id_old
    else:
        assert machine_id_new != machine_id_old


def test_machineid_changes_when_subman_is_unregistered_and_registered(insights_client, subman):
    """machine-id should be different based on the auth method"""
    if "satellite" in test_config.environment():
        pytest.skip("this test requires BASIC authentication")

    assert not insights_client.is_registered
    insights_client.register()
    with open(MACHINE_ID_FILE, "r") as f:
        machine_id_cert = f.read()
    insights_client.unregister()

    insights_client.config.auto_config = False
    insights_client.config.authmethod = "BASIC"
    insights_client.config.username = test_config.get("candlepin", "username")
    insights_client.config.password = test_config.get("candlepin", "password")
    insights_client.config.save()

    insights_client.register()
    with open(MACHINE_ID_FILE, "r") as f:
        machine_id_random = f.read()

    assert machine_id_random != machine_id_cert


def test_registered_and_unregistered_files_are_created_and_deleted(insights_client):
    """""'.registered and .unregistered file gets created and deleted"""
    assert not insights_client.is_registered

    insights_client.register()
    assert os.path.exists('/etc/insights-client/.registered')

    insights_client.unregister()
    assert os.path.exists('/etc/insights-client/.unregistered')


def test_double_registration(insights_client):
    """`--register` can be passed multiple times.

    Even system that is already registered should allow the `--register` flag to be
    passed in, without resulting in non-zero exit code.

    This behavior has changed multiple times during the package lifetime.
    """
    assert not insights_client.is_registered

    insights_client.register()
    assert os.path.exists(MACHINE_ID_FILE)
    with open(MACHINE_ID_FILE, "r") as f:
        machine_id_old = f.read()

    res = insights_client.register()
    assert "This host has already been registered" in res.stdout
    assert os.path.exists(MACHINE_ID_FILE)
    with open(MACHINE_ID_FILE, "r") as f:
        machine_id_new = f.read()

    assert machine_id_new == machine_id_old
