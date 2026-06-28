"""
StudyMate AI – Profile Repository (Phase 5A)
Handles user settings updates, username validation, and profile avatar uploads to Supabase Storage.
"""

import io
import logging
import re
from typing import Any, Dict, Optional
from PIL import Image
import streamlit as st

from modules.base_repository import BaseRepository

logger = logging.getLogger("studymate.profile_repository")


class ProfileRepository(BaseRepository):
    """Repository managing profile database fields and avatar uploads."""

    @classmethod
    def get_profile(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the user's profile details.
        Caches the profile in st.session_state to avoid repeated DB calls.
        """
        if not user_id:
            return None

        # Check session state cache first
        cache_key = f"profile_cache_{user_id}"
        if cache_key in st.session_state:
            return st.session_state[cache_key]

        if not cls.is_online():
            return None

        client = cls.get_client()
        if not client:
            return None

        try:
            resp = client.table("users").select("id, full_name, email, username, profile_image_url, bio, email_verified").eq("id", user_id).execute()
            if resp.data:
                profile = resp.data[0]
                # Map full_name as name for backward compatibility
                profile["name"] = profile["full_name"]
                st.session_state[cache_key] = profile
                return profile
        except Exception as e:
            logger.error(f"Error fetching profile for {user_id}: {e}")
        return None

    @classmethod
    def update_profile(cls, user_id: str, full_name: str, username: Optional[str], bio: Optional[str]) -> bool:
        """Update user profile settings in the database and invalidate local cache."""
        if not cls.is_online():
            return False

        client = cls.get_client()
        if not client:
            return False

        try:
            # Clean inputs
            clean_name = str(full_name).strip()
            clean_username = str(username).strip() if username else None
            clean_bio = str(bio).strip() if bio else None

            payload = {
                "full_name": clean_name,
                "username": clean_username,
                "bio": clean_bio,
            }

            resp = client.table("users").update(payload).eq("id", user_id).execute()
            if resp.data:
                # Invalidate cache
                cache_key = f"profile_cache_{user_id}"
                st.session_state.pop(cache_key, None)
                
                # Update main session state values
                st.session_state.user_name = clean_name
                st.session_state.user_username = clean_username
                st.session_state.user_bio = clean_bio
                return True
        except Exception as e:
            logger.error(f"Failed to update profile for {user_id}: {e}")
        return False

    @classmethod
    def validate_username(cls, username: str) -> tuple[bool, str]:
        """Validate username constraints (3-30 chars, letters, numbers, underscores)."""
        if not username:
            return True, ""  # Optional field
        
        val = str(username).strip()
        if len(val) < 3 or len(val) > 30:
            return False, "Username must be between 3 and 30 characters."
            
        if not re.match(r"^[a-zA-Z0-9_]+$", val):
            return False, "Username can only contain letters, numbers, and underscores."
            
        return True, ""

    @classmethod
    def is_username_available(cls, username: str, exclude_user_id: str) -> bool:
        """Check if a username is unique across all user accounts."""
        if not username or not cls.is_online():
            return True

        client = cls.get_client()
        if not client:
            return True

        try:
            resp = client.table("users").select("id").eq("username", username.strip()).execute()
            if resp.data:
                # Username is taken, check if it belongs to someone else
                for user in resp.data:
                    if user["id"] != exclude_user_id:
                        return False
            return True
        except Exception as e:
            logger.error(f"Error checking username availability: {e}")
            return True

    @classmethod
    def upload_profile_picture(cls, user_id: str, image_bytes: bytes, file_name: str, file_size: int) -> Optional[str]:
        """
        Validate, resize, crop to square, convert to WEBP, upload to Storage, 
        and update user's profile_image_url in the database.
        """
        if not cls.is_online():
            return None

        client = cls.get_client()
        if not client:
            return None

        # Validate file size (max 5MB)
        if file_size > 5 * 1024 * 1024:
            logger.warning(f"File size too large: {file_size} bytes")
            return None

        try:
            # 1. Process image using Pillow (Crop to square & resize to 256x256 WebP)
            img = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB mode (needed for WebP)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGBA", img.size, (255, 255, 255, 255))
                img = Image.alpha_composite(background, img.convert("RGBA")).convert("RGB")
            else:
                img = img.convert("RGB")

            # Centered Crop to Square
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) / 2
            top = (height - min_dim) / 2
            right = (width + min_dim) / 2
            bottom = (height + min_dim) / 2
            img = img.crop((left, top, right, bottom))

            # Resize to 256x256
            img = img.resize((256, 256), Image.Resampling.LANCZOS)

            # Export to WEBP bytes
            output_bytes = io.BytesIO()
            img.save(output_bytes, format="WEBP", quality=80)
            processed_data = output_bytes.getvalue()

            # 2. Upload to Supabase Storage (public bucket 'profile-images') under user_uuid/avatar.webp
            storage_path = f"{user_id}/avatar.webp"
            
            # Upload with upsert (replace if exists)
            client.storage.from_("profile-images").upload(
                path=storage_path,
                file=processed_data,
                file_options={"content-type": "image/webp", "x-upsert": "true"}
            )

            # 3. Retrieve public URL
            public_url = client.storage.from_("profile-images").get_public_url(storage_path)

            # 4. Update public_image_url in database
            client.table("users").update({"profile_image_url": public_url}).eq("id", user_id).execute()

            # 5. Invalidate local profile cache
            cache_key = f"profile_cache_{user_id}"
            st.session_state.pop(cache_key, None)
            st.session_state.profile_image_url = public_url

            return public_url
        except Exception as e:
            logger.error(f"Failed uploading profile picture for {user_id}: {e}")
            return None

    @classmethod
    def delete_profile_picture(cls, user_id: str) -> bool:
        """Delete user's avatar from Supabase Storage and remove public URL from DB."""
        if not cls.is_online():
            return False

        client = cls.get_client()
        if not client:
            return False

        try:
            # 1. Remove from storage
            storage_path = f"{user_id}/avatar.webp"
            try:
                client.storage.from_("profile-images").remove([storage_path])
            except Exception:
                pass  # Ignore storage deletion failure if it didn't exist

            # 2. Clear from database
            client.table("users").update({"profile_image_url": None}).eq("id", user_id).execute()

            # 3. Invalidate local cache
            cache_key = f"profile_cache_{user_id}"
            st.session_state.pop(cache_key, None)
            st.session_state.profile_image_url = None

            return True
        except Exception as e:
            logger.error(f"Failed deleting avatar for {user_id}: {e}")
            return False

    @classmethod
    def get_avatar_url(cls, user_id: str) -> Optional[str]:
        """Get public url path of user's avatar."""
        if not cls.is_online():
            return None
        client = cls.get_client()
        if not client:
            return None
        try:
            return client.storage.from_("profile-images").get_public_url(f"{user_id}/avatar.webp")
        except Exception:
            return None
