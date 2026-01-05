# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import json

from google_marketing_platform.utils import (
    BaseGTMResourceCommand,
    GTMConstants,
    prompt_input,
    prompt_yes_no,
    remove_gtm_metadata_fields,
)


class Command(BaseGTMResourceCommand):
    help = "Remotely manage GTM triggers."

    def _configure_resource_type(self):
        """Configure trigger-specific settings."""
        self.resource_type = "trigger"
        self.resource_id_param = "trigger_id"
        self.cache_subdir = GTMConstants.TRIGGERS_SUBDIR
        self.fields_to_remove = GTMConstants.TRIGGER_FIELDS_TO_REMOVE

    def _fetch_resource(self, client, account_id, container_id, workspace_id, resource_id):
        """Fetch a trigger from GTM."""
        return client.get_trigger(account_id, container_id, workspace_id, resource_id)

    def _create_resource(self, client, account_id, container_id, workspace_id, resource_body):
        """Create a trigger in GTM."""
        return client.create_trigger(account_id, container_id, workspace_id, resource_body)

    def _post_fetch_hook(self, client, account_id, container_id, workspace_id, resource):
        """Cache associated firing triggers after fetching a trigger."""
        if "firingTriggerId" in resource and isinstance(resource["firingTriggerId"], list):
            for firing_id in resource["firingTriggerId"]:
                self._fetch_and_cache_firing_trigger(
                    client, account_id, container_id, workspace_id, firing_id
                )

    def _fetch_and_cache_firing_trigger(
        self, client, account_id, container_id, workspace_id, firing_id
    ):
        """Fetch a firing trigger from GTM and cache it."""
        try:
            firing_trigger = client.get_trigger(
                account_id, container_id, workspace_id, firing_id
            )
            firing_name = firing_trigger.get("name", f"trigger_{firing_id}")
            identifier = self.cache.generate_resource_identifier(
                firing_name, account_id, container_id, workspace_id
            )
            saved_path = self.cache.save_resource(
                firing_trigger, GTMConstants.TRIGGERS_SUBDIR, identifier
            )

            self.stdout.write(
                self.style.WARNING(
                    f"Trigger metadata for ID {firing_name} cached to {saved_path}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error retrieving trigger {firing_id}: {e}")
            )

    def _post_clone_hook(self, client, account_id, container_id, workspace_id, created_resource):
        """Handle optional tag association after trigger creation."""
        new_trigger_id = created_resource.get("triggerId")
        if not new_trigger_id:
            return

        self._handle_tag_association(
            client, account_id, container_id, workspace_id, new_trigger_id
        )

    def _handle_tag_association(
        self, client, account_id, container_id, workspace_id, new_trigger_id
    ):
        """Handle optional tag association after trigger creation."""
        if not prompt_yes_no("Would you like to attach this to a tag?"):
            self.stdout.write(self.style.WARNING("Session ended."))
            return

        tag_name = prompt_input(
            "Which tag would you like to associate with this trigger? "
            "Please input the cached resource identifier"
        )

        try:
            # Load the tag
            identifier = tag_name
            tag, tag_path = self.cache.load_resource(GTMConstants.TAGS_SUBDIR, identifier)

            # Update the tag with the new trigger ID
            tag["firingTriggerId"] = [new_trigger_id]
            self.cache.update_resource(GTMConstants.TAGS_SUBDIR, identifier, tag)

            self.stdout.write(
                self.style.WARNING(
                    f"Updated {tag_name} with new firingTriggerId: {new_trigger_id}"
                )
            )

            # Offer to deploy the tag
            self._handle_tag_deployment(
                client, account_id, container_id, workspace_id, tag
            )

        except ValueError as e:
            self.stdout.write(self.style.ERROR(str(e)))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error associating tag: {e}"))

    def _handle_tag_deployment(
        self, client, account_id, container_id, workspace_id, tag
    ):
        """Handle optional tag deployment after association."""
        if prompt_yes_no("Would you like to deploy this tag to the same workspace?"):
            self._deploy_tag_to_workspace(
                client, account_id, container_id, workspace_id, tag
            )
        elif prompt_yes_no("Would you like to deploy to a different destination?"):
            self._deploy_tag_to_different_destination(client, tag)
        else:
            self.stdout.write(self.style.WARNING("Session ended."))

    def _deploy_tag_to_workspace(
        self, client, account_id, container_id, workspace_id, tag
    ):
        """Deploy a tag to the specified workspace."""
        try:
            remove_gtm_metadata_fields(tag, GTMConstants.TAG_FIELDS_TO_REMOVE)

            created_tag = client.create_tag(account_id, container_id, workspace_id, tag)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Tag deployed successfully! New tag info:\n{json.dumps(created_tag, indent=2)}"
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error deploying tag: {e}"))

    def _deploy_tag_to_different_destination(self, client, tag):
        """Deploy a tag to a different destination with user-provided IDs."""
        dest_account_id = prompt_input("Destination Account ID")
        dest_container_id = prompt_input("Destination Container ID")
        dest_workspace_id = prompt_input("Destination Workspace ID")

        try:
            remove_gtm_metadata_fields(tag, GTMConstants.TAG_FIELDS_TO_REMOVE)

            created_tag = client.create_tag(
                dest_account_id, dest_container_id, dest_workspace_id, tag
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Tag deployed to new destination! New tag info:\n{json.dumps(created_tag, indent=2)}"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error deploying tag to new destination: {e}")
            )
