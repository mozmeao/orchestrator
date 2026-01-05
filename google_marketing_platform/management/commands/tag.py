# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from googleapiclient.errors import HttpError

from google_marketing_platform.utils import (
    BaseGTMResourceCommand,
    GTMConstants,
    prompt_input,
    prompt_yes_no,
)


class Command(BaseGTMResourceCommand):
    help = "Remotely manage GTM tags."

    def _configure_resource_type(self):
        """Configure tag-specific settings."""
        self.resource_type = "tag"
        self.resource_id_param = "tag_id"
        self.cache_subdir = GTMConstants.TAGS_SUBDIR
        self.fields_to_remove = GTMConstants.TAG_FIELDS_TO_REMOVE

    def _fetch_resource(self, client, account_id, container_id, workspace_id, resource_id):
        """Fetch a tag from GTM."""
        return client.get_tag(account_id, container_id, workspace_id, resource_id)

    def _create_resource(self, client, account_id, container_id, workspace_id, resource_body):
        """Create a tag in GTM."""
        return client.create_tag(account_id, container_id, workspace_id, resource_body)

    def _post_fetch_hook(self, client, account_id, container_id, workspace_id, resource):
        """Cache associated triggers after fetching a tag."""
        if "firingTriggerId" in resource and isinstance(resource["firingTriggerId"], list):
            for trigger_id in resource["firingTriggerId"]:
                self._fetch_and_cache_trigger(
                    client, account_id, container_id, workspace_id, trigger_id
                )

    def _fetch_and_cache_trigger(
        self, client, account_id, container_id, workspace_id, trigger_id
    ):
        """Fetch a trigger from GTM and cache it."""
        try:
            trigger = client.get_trigger(
                account_id, container_id, workspace_id, trigger_id
            )
            trigger_name = trigger.get("name", f"trigger_{trigger_id}")
            identifier = self.cache.generate_resource_identifier(
                trigger_name, account_id, container_id, workspace_id
            )
            saved_path = self.cache.save_resource(
                trigger, GTMConstants.TRIGGERS_SUBDIR, identifier
            )

            self.stdout.write(
                self.style.WARNING(
                    f"Trigger metadata for ID {trigger_name} cached to {saved_path}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error retrieving trigger {trigger_id}: {e}")
            )

    def clone_resource_to_container(self, options):
        """Clone a cached tag to a new GTM container/workspace with special error handling."""
        account_id = options["account_id"]
        container_id = options["container_id"]
        workspace_id = options["workspace_id"]
        tag_name = options["tag_name"]

        try:
            # Load the cached tag
            identifier = tag_name
            tag, _ = self.cache.load_resource(GTMConstants.TAGS_SUBDIR, identifier)

            # Remove fields that shouldn't be sent
            from google_marketing_platform.utils import remove_gtm_metadata_fields
            remove_gtm_metadata_fields(tag, GTMConstants.TAG_FIELDS_TO_REMOVE)

            # Create the tag in the destination
            from google_marketing_platform.utils import GTMClient
            client = GTMClient(GTMConstants.EDIT_SCOPE)

            try:
                self._attempt_tag_creation(
                    client, account_id, container_id, workspace_id, tag
                )
            except HttpError as e:
                error_msg = str(e)
                if e.resp.status == 400 and "unknown trigger" in error_msg.lower():
                    self._handle_missing_trigger_error(
                        client, account_id, container_id, workspace_id, tag, identifier
                    )
                else:
                    self.stdout.write(self.style.ERROR(f"Error cloning tag: {e}"))

        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error cloning tag: {e}"))

    def _attempt_tag_creation(
        self, client, account_id, container_id, workspace_id, tag_body
    ):
        """Attempt to create a tag in GTM."""
        created_tag = client.create_tag(
            account_id, container_id, workspace_id, tag_body
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Tag cloned successfully! New tag info:\n{json.dumps(created_tag, indent=2)}"
            )
        )

    def _handle_missing_trigger_error(
        self, client, account_id, container_id, workspace_id, tag, identifier
    ):
        """Handle the missing trigger error during tag cloning."""
        self.stdout.write(
            self.style.WARNING(
                "Missing Trigger. If the trigger you'd like to attach exists in the new container, "
                "please input the ID. If it does not exist, please refer to the trigger cache and "
                "create the trigger first prior to cloning."
            )
        )

        if prompt_yes_no(
            "Would you like to leverage an existing trigger (in the target container)?"
        ):
            trigger_id = prompt_input("Enter the trigger ID to attach to this tag")
            tag["firingTriggerId"] = [trigger_id]

            # Update the cached tag in Redis
            self.cache.update_resource(GTMConstants.TAGS_SUBDIR, identifier, tag)
            self.stdout.write(
                self.style.WARNING(f"Updated firingTriggerId in cache to: {trigger_id}")
            )

            try:
                self._attempt_tag_creation(
                    client, account_id, container_id, workspace_id, tag
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Error cloning tag after updating trigger: {e}")
                )
        else:
            self.stdout.write(
                self.style.ERROR(
                    "Aborting tag clone. Please clone the required trigger to the target container first."
                )
            )
