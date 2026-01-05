# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Utility classes and functions for Google Tag Manager operations.
Provides shared functionality for GTM management commands.
"""

import json

from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError
from everett.manager import ConfigManager
from google.auth import default
from googleapiclient.discovery import build

# Configuration manager for GTM settings
config = ConfigManager.basic_config()


class GTMConstants:
    """Constants used across GTM management commands."""

    # Resource type subdirectories (used for cache key namespacing)
    TAGS_SUBDIR = "tags"
    TRIGGERS_SUBDIR = "triggers"

    READONLY_SCOPE = config(
        "GTM_READONLY_SCOPE"
    )
    EDIT_SCOPE = config(
        "GTM_EDIT_SCOPE"
    )

    # Fields to remove before creating resources
    TAG_FIELDS_TO_REMOVE = [
        "tagId",
        "path",
        "workspaceId",
        "accountId",
        "containerId",
        "fingerprint",
        "tagManagerUrl",
    ]
    TRIGGER_FIELDS_TO_REMOVE = [
        "triggerId",
        "path",
        "workspaceId",
        "accountId",
        "containerId",
        "fingerprint",
        "tagManagerUrl",
    ]


class GTMClient:
    """Client for interacting with Google Tag Manager API."""

    def __init__(self, scope):
        """Initialize GTM client."""
        self.credentials, project = default(scopes=[scope])
        self.service = build("tagmanager", "v2", credentials=self.credentials)

    def get_tag(self, account_id, container_id, workspace_id, tag_id):
        """Retrieve a tag from GTM."""
        path = self._build_resource_path(
            account_id, container_id, workspace_id, "tags", tag_id
        )
        return (
            self.service.accounts()
            .containers()
            .workspaces()
            .tags()
            .get(path=path)
            .execute()
        )

    def get_trigger(self, account_id, container_id, workspace_id, trigger_id):
        """Retrieve a trigger from GTM."""
        path = self._build_resource_path(
            account_id, container_id, workspace_id, "triggers", trigger_id
        )
        return (
            self.service.accounts()
            .containers()
            .workspaces()
            .triggers()
            .get(path=path)
            .execute()
        )

    def create_tag(self, account_id, container_id, workspace_id, tag_body):
        """Create a tag in GTM."""
        parent = self._build_parent_path(account_id, container_id, workspace_id)
        return (
            self.service.accounts()
            .containers()
            .workspaces()
            .tags()
            .create(parent=parent, body=tag_body)
            .execute()
        )

    def create_trigger(self, account_id, container_id, workspace_id, trigger_body):
        """Create a trigger in GTM."""
        parent = self._build_parent_path(account_id, container_id, workspace_id)
        return (
            self.service.accounts()
            .containers()
            .workspaces()
            .triggers()
            .create(parent=parent, body=trigger_body)
            .execute()
        )

    @staticmethod
    def _build_resource_path(
        account_id, container_id, workspace_id, resource_type, resource_id
    ):
        """Build a GTM resource path."""
        return f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/{resource_type}/{resource_id}"

    @staticmethod
    def _build_parent_path(account_id, container_id, workspace_id):
        """Build a GTM parent path."""
        return (
            f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}"
        )


class GTMCache:
    """Manager for GTM resource caching operations using Redis."""

    def __init__(self):
        """Initialize cache manager using Django's cache framework."""
        pass

    def _build_cache_key(self, subdir, filename):
        """
        Build a Redis cache key from subdir and filename.

        Args:
            subdir: Resource type ('tags' or 'triggers')
            filename: Resource identifier

        Returns:
            Cache key string (e.g., 'gtm:tags:MyTag_123_456_789')
        """

        key_name = filename.replace(".json", "").replace(":", "_").replace("\n", "_").replace("\r", "_")
        key_name = key_name.replace(" ", "_").replace(":", "_").replace("\n", "_").replace("\r", "_")
        return f"gtm:{subdir}:{key_name}"

    def save_resource(self, resource_data, subdir, filename):
        """
        Save a GTM resource to Redis cache.

        Args:
            resource_data: Resource data dictionary
            subdir: Resource type ('tags' or 'triggers')
            filename: Resource identifier (with or without .json extension)

        Returns:
            Cache key string
        """
        cache_key = self._build_cache_key(subdir, filename)
        # Serialize to JSON string for storage
        cache.set(cache_key, json.dumps(resource_data))
        return cache_key

    def load_resource(self, subdir, filename):
        """
        Load a GTM resource from Redis cache.

        Args:
            subdir: Resource type ('tags' or 'triggers')
            filename: Resource identifier (with or without .json extension)

        Returns:
            Tuple of (resource_data, cache_key)

        Raises:
            ValueError: If the resource doesn't exist in cache
        """
        cache_key = self._build_cache_key(subdir, filename)
        cached_data = cache.get(cache_key)

        if cached_data is None:
            raise ValueError(f"Resource not found in cache: {cache_key}")

        # Deserialize from JSON string
        resource_data = json.loads(cached_data)
        return resource_data, cache_key

    def update_resource(self, subdir, filename, resource_data):
        """
        Update a cached resource in Redis.

        Args:
            subdir: Resource type ('tags' or 'triggers')
            filename: Resource identifier
            resource_data: Updated resource data

        Returns:
            Cache key string
        """
        return self.save_resource(resource_data, subdir, filename)

    @staticmethod
    def generate_resource_suffix(account_id, container_id, workspace_id):
        """
        Generate a resource identifier suffix from GTM IDs.

        Args:
            account_id: GTM Account ID
            container_id: GTM Container ID
            workspace_id: GTM Workspace ID

        Returns:
            Suffix string (e.g., '_123_456_789')
        """
        return f"_{account_id}_{container_id}_{workspace_id}"

    @staticmethod
    def generate_resource_identifier(name, account_id, container_id, workspace_id):
        """
        Generate a complete identifier for a cached resource.

        Args:
            name: Resource name
            account_id: GTM Account ID
            container_id: GTM Container ID
            workspace_id: GTM Workspace ID

        Returns:
            Resource identifier string (e.g., 'MyTag_123_456_789')
        """
        suffix = GTMCache.generate_resource_suffix(
            account_id, container_id, workspace_id
        )
        return f"{name}{suffix}"



def remove_gtm_metadata_fields(resource_data, fields_to_remove):
    """
    Remove GTM metadata fields from a resource dictionary.
    Modifies the dictionary in place.

    Args:
        resource_data: Resource dictionary
        fields_to_remove: List of field names to remove
    """
    for field in fields_to_remove:
        resource_data.pop(field, None)


def prompt_yes_no(message, default="n"):
    """
    Prompt user for yes/no input.

    Args:
        message: Prompt message
        default: Default value ('y' or 'n')

    Returns:
        True if yes, False if no
    """
    suffix = " [Y/n]: " if default.lower() == "y" else " [y/N]: "
    response = input(message + suffix).strip().lower()
    if not response:
        return default.lower() == "y"
    return response == "y"


def prompt_input(message):
    """
    Prompt user for text input.

    Args:
        message: Prompt message

    Returns:
        User input string (stripped)
    """
    return input(message + ": ").strip()


class BaseGTMResourceCommand(BaseCommand):
    """
    Base command class for GTM resource management (tags, triggers, etc.).
    Provides shared functionality for get, clone, and print operations.
    """

    def __init__(self):
        super().__init__()
        self.cache = GTMCache()
        self._configure_resource_type()

    def _configure_resource_type(self):
        """
        Configure resource-specific settings. Must be implemented by subclasses.
        Should set: resource_type, resource_id_param, cache_subdir, fields_to_remove
        """
        raise NotImplementedError("Subclasses must implement _configure_resource_type()")

    def add_arguments(self, parser):
        """Add shared argument parsers for GTM resource commands."""
        subparsers = parser.add_subparsers(dest="subcommand", required=True)

        # get_gtm_resource subcommand
        get_parser = subparsers.add_parser(
            f"get_gtm_{self.resource_type}",
            help=f"Retrieve a {self.resource_type} from GTM and cache it.",
        )
        get_parser.add_argument("--account-id", required=True, help="GTM Account ID")
        get_parser.add_argument("--container-id", required=True, help="GTM Container ID")
        get_parser.add_argument("--workspace-id", required=True, help="GTM Workspace ID")
        get_parser.add_argument(
            f"--{self.resource_id_param.replace('_', '-')}",
            required=True,
            help=f"GTM {self.resource_type.capitalize()} ID",
        )

        # clone_resource_to_container subcommand
        clone_parser = subparsers.add_parser(
            f"clone_{self.resource_type}_to_container",
            help=f"Clone a cached {self.resource_type} to a new GTM container/workspace.",
        )
        clone_parser.add_argument(
            "--account-id", required=True, help="Destination GTM Account ID"
        )
        clone_parser.add_argument(
            "--container-id", required=True, help="Destination GTM Container ID"
        )
        clone_parser.add_argument(
            "--workspace-id", required=True, help="Destination GTM Workspace ID"
        )
        clone_parser.add_argument(
            f"--{self.resource_type}-name",
            required=True,
            help=f"Name of the cached {self.resource_type} to clone (resource identifier)",
        )

        # print_cached subcommand
        print_parser = subparsers.add_parser(
            "print_cached", help=f"Print the contents of a cached {self.resource_type}."
        )
        print_parser.add_argument(
            "--name",
            required=True,
            help=f"Name of the cached {self.resource_type}",
        )

    def handle(self, *args, **options):
        """Route to appropriate subcommand handler."""
        subcommand = options["subcommand"]
        if subcommand == f"get_gtm_{self.resource_type}":
            self.get_gtm_resource(options)
        elif subcommand == f"clone_{self.resource_type}_to_container":
            self.clone_resource_to_container(options)
        elif subcommand == "print_cached":
            self.print_cached(options)
        else:
            raise CommandError("Unknown subcommand")

    def get_gtm_resource(self, options):
        """Retrieve a resource from GTM and cache it."""
        account_id = options["account_id"]
        container_id = options["container_id"]
        workspace_id = options["workspace_id"]
        resource_id = options[self.resource_id_param]

        try:
            client = GTMClient(GTMConstants.READONLY_SCOPE)

            # Fetch the resource using the appropriate client method
            resource = self._fetch_resource(
                client, account_id, container_id, workspace_id, resource_id
            )

            self.stdout.write(
                self.style.SUCCESS(f"{self.resource_type.capitalize()} retrieved successfully:")
            )
            self.stdout.write(json.dumps(resource, indent=2))

            # Cache the resource
            resource_name = resource.get("name", f"{self.resource_type}_{resource_id}")
            identifier = self.cache.generate_resource_identifier(
                resource_name, account_id, container_id, workspace_id
            )
            saved_path = self.cache.save_resource(
                resource, self.cache_subdir, identifier
            )

            self.stdout.write(
                self.style.WARNING(f"{self.resource_type.capitalize()} cached to {saved_path}")
            )

            # Allow subclasses to handle additional caching (e.g., associated triggers)
            self._post_fetch_hook(client, account_id, container_id, workspace_id, resource)

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error retrieving {self.resource_type}: {e}")
            )

    def clone_resource_to_container(self, options):
        """Clone a cached resource to a new GTM container/workspace."""
        account_id = options["account_id"]
        container_id = options["container_id"]
        workspace_id = options["workspace_id"]
        resource_name = options[f"{self.resource_type}_name"]

        try:
            # Load the cached resource
            identifier = resource_name
            resource, _ = self.cache.load_resource(self.cache_subdir, identifier)

            # Remove fields that shouldn't be sent
            remove_gtm_metadata_fields(resource, self.fields_to_remove)

            # Create the resource in the destination
            client = GTMClient(GTMConstants.EDIT_SCOPE)
            created_resource = self._create_resource(
                client, account_id, container_id, workspace_id, resource
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"{self.resource_type.capitalize()} cloned successfully! "
                    f"New {self.resource_type} info:\n{json.dumps(created_resource, indent=2)}"
                )
            )

            # Allow subclasses to handle post-creation logic
            self._post_clone_hook(
                client, account_id, container_id, workspace_id, created_resource
            )

        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error cloning {self.resource_type}: {e}")
            )

    def print_cached(self, options):
        """Print the contents of a cached resource."""
        resource_name = options["name"]

        try:
            # Load the cached resource
            resource, _ = self.cache.load_resource(self.cache_subdir, resource_name)

            self.stdout.write(
                self.style.SUCCESS(f"Cached {self.resource_type} '{resource_name}':")
            )
            self.stdout.write(json.dumps(resource, indent=2))

        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error loading cached {self.resource_type}: {e}")
            )

    def _fetch_resource(self, client, account_id, container_id, workspace_id, resource_id):
        """Fetch a resource from GTM. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _fetch_resource()")

    def _create_resource(self, client, account_id, container_id, workspace_id, resource_body):
        """Create a resource in GTM. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _create_resource()")

    def _post_fetch_hook(self, client, account_id, container_id, workspace_id, resource):
        """
        Optional hook called after fetching a resource.
        Subclasses can override to add additional behavior (e.g., caching related resources).
        """
        pass

    def _post_clone_hook(self, client, account_id, container_id, workspace_id, created_resource):
        """
        Optional hook called after cloning a resource.
        Subclasses can override to add additional behavior.
        """
        pass
