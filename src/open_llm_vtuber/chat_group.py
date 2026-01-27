from typing import Dict, List, Optional, Set, Tuple, Callable, Any
from dataclasses import dataclass
from fastapi import WebSocket
import json
from loguru import logger


@dataclass
class Group:
    group_id: str
    owner_uid: str
    members: Set[str]  # Set of client_uids


class ChatGroupManager:
    def __init__(self):
        self.client_group_map: Dict[str, str] = {}  # client_uid -> group_id
        self.groups: Dict[str, Group] = {}  # group_id -> Group

    def create_group_for_client(self, client_uid: str) -> str:
        group_id = f"group_{client_uid}"
        new_group = Group(group_id=group_id, owner_uid=client_uid, members={client_uid})
        self.groups[group_id] = new_group
        self.client_group_map[client_uid] = group_id
        logger.info(f"Created group {group_id} for client {client_uid}")
        return group_id

    def add_client_to_group(
        self, inviter_uid: str, invitee_uid: str
    ) -> Tuple[bool, str]:
        """
        Add a client to the group of the inviter
        If inviter is not in a group, create one
        Returns (success, message)
        """
        # Check if invitee exists in client map (connected)
        if invitee_uid not in self.client_group_map:
            return False, f"Invitee {invitee_uid} does not exist"

        # Check if invitee is already in a group
        if invitee_uid in self.client_group_map and self.client_group_map[invitee_uid]:
            return False, f"Invitee {invitee_uid} is already in a group"

        # If inviter is not in a group, create one
        inviter_group_id = self.client_group_map.get(inviter_uid)
        if not inviter_group_id:
            group_id = f"group_{inviter_uid}"
            new_group = Group(
                group_id=group_id, owner_uid=inviter_uid, members={inviter_uid}
            )
            self.groups[group_id] = new_group
            self.client_group_map[inviter_uid] = group_id
            inviter_group_id = group_id
            logger.info(f"Created new group {group_id} for inviter {inviter_uid}")

        # Add invitee to group
        group = self.groups[inviter_group_id]
        group.members.add(invitee_uid)
        self.client_group_map[invitee_uid] = inviter_group_id

        logger.info(f"Added client {invitee_uid} to group {inviter_group_id}")
        return True, f"Successfully added {invitee_uid} to the group"

    def remove_client_from_group(
        self, remover_uid: str, target_uid: str
    ) -> Tuple[bool, str]:
        """
        Remove a client from their group
        Returns (success, message)
        """
        # Check if target is in a group
        target_group_id = self.client_group_map.get(target_uid)
        if not target_group_id:
            return False, f"Target {target_uid} is not in any group"

        group = self.groups[target_group_id]

        # Only group owner or self can remove
        if remover_uid != group.owner_uid and remover_uid != target_uid:
            return False, "Only group owner or self can remove members"

        # Remove target from group
        group.members.remove(target_uid)
        self.client_group_map[target_uid] = ""  # Empty string means not in any group

        # If group becomes empty or only has owner, delete it
        if len(group.members) <= 1:
            # Remove owner from group too
            if group.members:
                owner_uid = next(iter(group.members))
                group.members.remove(owner_uid)
                self.client_group_map[owner_uid] = ""
            del self.groups[target_group_id]
            logger.info(f"Removed empty group {target_group_id}")

        logger.info(f"Removed client {target_uid} from group {target_group_id}")
        return True, f"Successfully removed {target_uid} from the group"

    def remove_client(self, client_uid: str) -> List[str]:
        """
        Remove client from their group and return affected members

        Returns:
            List[str]: List of remaining group members
        """
        group_id = self.client_group_map.get(client_uid)
        if not group_id or group_id not in self.groups:
            return []

        group = self.groups[group_id]
        affected_members = list(group.members)

        # Remove client from group
        if client_uid in group.members:
            group.members.remove(client_uid)
        if client_uid in self.client_group_map:
            del self.client_group_map[client_uid]

        # If client was owner, assign new owner or delete group
        if group.owner_uid == client_uid:
            remaining_members = list(group.members)
            if remaining_members:
                # Assign new owner
                new_owner = remaining_members[0]
                group.owner_uid = new_owner
                logger.info(f"New owner {new_owner} assigned to group {group_id}")
            else:
                # Delete empty group
                del self.groups[group_id]
                logger.info(f"Removed empty group {group_id}")
        # If group becomes empty
        elif len(group.members) == 0:
            del self.groups[group_id]
            logger.info(f"Removed empty group {group_id}")

        return affected_members

    def cleanup_disconnected_clients(self, connected_clients: Set[str]):
        """Remove all disconnected clients from groups"""
        disconnected_clients = set(self.client_group_map.keys()) - connected_clients
        for client_uid in disconnected_clients:
            self.remove_client(client_uid)

    def get_client_group(self, client_uid: str) -> Optional[Group]:
        """
        Get the group that a client belongs to
        """
        group_id = self.client_group_map.get(client_uid)
        return self.groups.get(group_id) if group_id else None

    def get_group_members(self, client_uid: str) -> List[str]:
        """
        Get all members in the client's group
        """
        group = self.get_client_group(client_uid)
        return list(group.members) if group else []

    def get_group_by_id(self, group_id: str) -> Optional[Group]:
        """Get group by group ID"""
        return self.groups.get(group_id)


async def handle_group_operation(
    operation: str,
    client_uid: str,
    target_uid: str,
    chat_group_manager: "ChatGroupManager",
    client_connections: Dict[str, WebSocket],
    send_group_update: Callable,
) -> None:
    """Handle group-related operations"""
    if target_uid:
        # Get all affected members before operation
        old_members = chat_group_manager.get_group_members(client_uid)
        target_old_members = chat_group_manager.get_group_members(target_uid)
        all_affected_members = set(old_members + target_old_members)

        if operation == "add-client-to-group":
            success, message = chat_group_manager.add_client_to_group(
                inviter_uid=client_uid, invitee_uid=target_uid
            )

            if success and target_uid in client_connections:
                try:
                    # Send group update to the newly invited member
                    await send_group_update(client_connections[target_uid], target_uid)
                    # Notify the invited member
                    await client_connections[target_uid].send_text(
                        json.dumps(
                            {
                                "type": "group-operation-result",
                                "success": True,
                                "message": f"You have been invited to the group by {client_uid}",
                            }
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to update invited member {target_uid}: {e}")

        else:  # remove operation
            success, message = chat_group_manager.remove_client_from_group(
                remover_uid=client_uid, target_uid=target_uid
            )

        # Send operation result to the initiator
        await client_connections[client_uid].send_text(
            json.dumps(
                {
                    "type": "group-operation-result",
                    "success": success,
                    "message": message,
                }
            )
        )

        if success:
            # For removal operation, update the removed member
            if operation != "add-client-to-group" and target_uid in client_connections:
                try:
                    await send_group_update(client_connections[target_uid], target_uid)
                    await client_connections[target_uid].send_text(
                        json.dumps(
                            {
                                "type": "group-operation-result",
                                "success": True,
                                "message": "You have been removed from the group",
                            }
                        )
                    )
                except Exception as e:
                    logger.error(f"Failed to update removed member {target_uid}: {e}")

            # Get new group members after operation
            new_members = chat_group_manager.get_group_members(client_uid)
            all_affected_members.update(new_members)

            # Update remaining group members
            for member_uid in all_affected_members:
                if member_uid in client_connections and member_uid != target_uid:
                    try:
                        await send_group_update(
                            client_connections[member_uid], member_uid
                        )
                        if member_uid != client_uid:
                            await client_connections[member_uid].send_text(
                                json.dumps(
                                    {
                                        "type": "group-operation-result",
                                        "success": True,
                                        "message": (
                                            f"Member {target_uid} was "
                                            f"{'added to' if operation == 'add-client-to-group' else 'removed from'} "
                                            "the group"
                                        ),
                                    }
                                )
                            )
                    except Exception as e:
                        logger.error(f"Failed to update member {member_uid}: {e}")


async def handle_client_disconnect(
    client_uid: str,
    chat_group_manager: "ChatGroupManager",
    client_connections: Dict[str, WebSocket],
    send_group_update: Callable,
) -> None:
    """Handle client disconnection from group"""
    old_group_members = chat_group_manager.get_group_members(client_uid)
    chat_group_manager.remove_client(client_uid)

    # Send updates to remaining group members
    for member_uid in old_group_members:
        if member_uid != client_uid and member_uid in client_connections:
            await send_group_update(client_connections[member_uid], member_uid)
            await client_connections[member_uid].send_text(
                json.dumps(
                    {
                        "type": "group-operation-result",
                        "success": True,
                        "message": f"Member {client_uid} disconnected",
                    }
                )
            )


async def broadcast_to_group(
    group_members: List[str],
    message: Dict[str, Any],
    client_connections: Dict[str, WebSocket],
    exclude_uid: Optional[str] = None,
) -> None:
    """Broadcasts a message to all members in a group except the sender"""
    for member_uid in group_members:
        if member_uid != exclude_uid and member_uid in client_connections:
            try:
                await client_connections[member_uid].send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to broadcast to {member_uid}: {e}")
