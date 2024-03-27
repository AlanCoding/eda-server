#  Copyright 2023 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from unittest import mock

import pytest
from ansible_base.rbac.models import DABPermission, RoleDefinition
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from rest_framework.test import APIClient

from aap_eda.core import enums, models

ADMIN_USERNAME = "test.admin"
ADMIN_PASSWORD = "test.admin.123"


@pytest.fixture
def default_organization():
    "Corresponds to migration add_default_organization"
    return models.Organization.objects.get_or_create(
        name=settings.DEFAULT_ORGANIZATION_NAME,
        description="The default organization",
    )[0]


@pytest.fixture
def admin_user(default_organization):
    user = models.User.objects.create_user(
        username=ADMIN_USERNAME,
        password=ADMIN_PASSWORD,
        email="admin@localhost",
    )
    organization = models.Organization.objects.get_default()
    admin_role = RoleDefinition.objects.create(
        name="Test Admin",
        content_type=ContentType.objects.get_for_model(organization),
    )
    admin_role.permissions.add(*DABPermission.objects.all())
    admin_role.give_permission(user, organization)
    return user


@pytest.fixture
def admin_awx_token(admin_user):
    return models.AwxToken.objects.create(
        name="admin-awx-token",
        token="maytheforcebewithyou",
        user=admin_user,
    )


@pytest.fixture
def base_client() -> APIClient:
    """Return APIClient instance with minimal required configuration."""
    client = APIClient(default_format="json")
    return client


@pytest.fixture
def client(base_client: APIClient, admin_user: models.User) -> APIClient:
    """Return a pre-configured instance of an APIClient."""
    base_client.force_authenticate(user=admin_user)
    return base_client


@pytest.fixture
def check_permission_mock():
    with mock.patch.object(
        models.User,
        "has_obj_perm",
        autospec=True,
        wraps=models.User.has_obj_perm,
    ) as m:
        yield m


@pytest.fixture
def default_de(default_organization) -> models.DecisionEnvironment:
    """Return a default DE."""
    return models.DecisionEnvironment.objects.create(
        name="default_de",
        image_url="quay.io/ansible/ansible-rulebook:latest",
        description="Default DE",
        organization=default_organization,
    )


@pytest.fixture
def default_user() -> models.User:
    """Return a default User."""
    return models.User.objects.create_user(
        username="luke.skywalker",
        first_name="Luke",
        last_name="Skywalker",
        email="luke.skywalker@example.com",
        password="secret",
    )


@pytest.fixture
def default_user_awx_token(default_user):
    return models.AwxToken.objects.create(
        name="admin-awx-token",
        token="maytheforcebewithyou",
        user=default_user,
    )


@pytest.fixture
def default_project(default_organization) -> models.Project:
    """Return a default Project."""
    return models.Project.objects.create(
        git_hash="684f62df18ce5f8d5c428e53203b9b975426eed0",
        name="default-project",
        url="https://git.example.com/acme/project-01",
        description="Default Project",
        organization=default_organization,
    )


@pytest.fixture
def default_rulesets() -> str:
    return """
---
- name: hello
  hosts: localhost
  gather_facts: false
  tasks:
    - debug:
        msg: hello
"""


@pytest.fixture
def default_rulebook(default_project, default_rulesets) -> models.Rulebook:
    """Return a default Rulebook"""
    return models.Rulebook.objects.create(
        name="default-rulebook.yml",
        rulesets=default_rulesets,
        description="test rulebook",
        project=default_project,
    )


@pytest.fixture
def ruleset_with_job_template() -> str:
    return """
---
- name: test
  sources:
    - ansible.eda.range:
        limit: 10
  rules:
    - name: example rule
      condition: event.i == 8
      actions:
        - run_job_template:
            organization: Default
            name: example
"""


@pytest.fixture
def rulebook_with_job_template(
    default_project, ruleset_with_job_template
) -> models.Rulebook:
    rulebook = models.Rulebook.objects.create(
        name="job-template.yml",
        description="rulebook with job template",
        rulesets=ruleset_with_job_template,
        project=default_project,
    )
    return rulebook


@pytest.fixture
def default_extra_var(default_organization) -> models.ExtraVar:
    """Return a default ExtraVar"""
    return models.ExtraVar.objects.create(
        extra_var="""
        ---
        collections:
        - community.general
        - benthomasson.eda
        """,
        organization=default_organization,
    )


@pytest.fixture
def activation_payload(
    default_de,
    default_project,
    default_rulebook,
    default_extra_var,
    default_organization,
    default_user,
) -> dict:
    return {
        "name": "test-activation",
        "description": "Test Activation",
        "is_enabled": True,
        "decision_environment_id": default_de.id,
        "project_id": default_project.id,
        "rulebook_id": default_rulebook.id,
        "extra_var_id": default_extra_var.id,
        "organization": default_organization.id,
        "user_id": default_user.id,
        "log_level": "debug",
    }


@pytest.fixture
def default_activation(
    default_de,
    default_project,
    default_rulebook,
    default_extra_var,
    default_organization,
    default_user,
    default_credential,
) -> models.Activation:
    """Return a default Activation"""
    activation = models.Activation.objects.create(
        name="default-activation",
        description="Default Activation",
        decision_environment=default_de,
        project=default_project,
        rulebook=default_rulebook,
        extra_var=default_extra_var,
        organization=default_organization,
        user=default_user,
        log_level="debug",
    )
    activation.credentials.add(default_credential)
    return activation


@pytest.fixture
def new_activation(
    default_de,
    default_project,
    default_rulebook,
    default_extra_var,
    default_organization,
    default_user,
) -> models.Activation:
    """Return a new Activation"""
    return models.Activation.objects.create(
        name="new-activation",
        description="New Activation",
        decision_environment=default_de,
        project=default_project,
        rulebook=default_rulebook,
        extra_var=default_extra_var,
        organization=default_organization,
        user=default_user,
        log_level="debug",
    )


@pytest.fixture
def credential_registry_type() -> models.CredentialType:
    return models.CredentialType.objects.create(
        name=enums.DefaultCredentialType.REGISTRY,
        inputs={
            "fields": [
                {"id": "username", "label": "Username"},
                {"id": "password", "label": "Password", "secret": True},
            ]
        },
        injectors={},
        managed=False,
    )


@pytest.fixture
def default_eda_credential(
    default_organization: models.Organization,
    credential_registry_type: models.CredentialType,
) -> models.EdaCredential:
    """Return a default Credential"""
    return models.EdaCredential.objects.create(
        name="default-credential",
        description="Default EDA Credential",
        credential_type=credential_registry_type,
        inputs={"username": "dummy-user", "password": "dummy-password"},
        organization=default_organization,
    )
