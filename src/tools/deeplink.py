"""
ElderCare Agent - Deep Link Generator Tool
Generates deep links for various communication platforms (WhatsApp, FaceTime, Phone).
"""

import logging
from typing import Dict, Optional
from urllib.parse import quote

logger = logging.getLogger(__name__)


class DeepLinkGenerator:
    """Generates deep links for communication platforms."""

    @staticmethod
    def generate_whatsapp_link(phone: str, message: Optional[str] = None) -> str:
        """
        Generate WhatsApp deep link.

        Args:
            phone: Phone number (with country code)
            message: Optional pre-filled message

        Returns:
            WhatsApp deep link URL
        """
        # Clean phone number (remove spaces, dashes, parentheses)
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Remove leading + if present
        if clean_phone.startswith("+"):
            clean_phone = clean_phone[1:]

        # Base WhatsApp URL
        url = f"https://wa.me/{clean_phone}"

        # Add message if provided
        if message:
            encoded_message = quote(message)
            url += f"?text={encoded_message}"

        logger.info(f"Generated WhatsApp link for {phone}")
        return url

    @staticmethod
    def generate_facetime_link(phone: str) -> str:
        """
        Generate FaceTime deep link.

        Args:
            phone: Phone number or email

        Returns:
            FaceTime deep link URL
        """
        # Clean phone number
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        url = f"facetime://{clean_phone}"

        logger.info(f"Generated FaceTime link for {phone}")
        return url

    @staticmethod
    def generate_phone_link(phone: str) -> str:
        """
        Generate phone call deep link.

        Args:
            phone: Phone number

        Returns:
            Phone deep link URL
        """
        # Clean phone number
        clean_phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        url = f"tel:{clean_phone}"

        logger.info(f"Generated phone link for {phone}")
        return url

    @staticmethod
    def generate_zoom_link(meeting_id: str, password: Optional[str] = None) -> str:
        """
        Generate Zoom meeting deep link.

        Args:
            meeting_id: Zoom meeting ID
            password: Optional meeting password

        Returns:
            Zoom deep link URL
        """
        url = f"zoommtg://zoom.us/join?confno={meeting_id}"

        if password:
            url += f"&pwd={password}"

        logger.info(f"Generated Zoom link for meeting {meeting_id}")
        return url

    @staticmethod
    def generate_email_link(email: str, subject: Optional[str] = None, body: Optional[str] = None) -> str:
        """
        Generate email deep link.

        Args:
            email: Email address
            subject: Optional email subject
            body: Optional email body

        Returns:
            Email deep link URL
        """
        url = f"mailto:{email}"

        params = []
        if subject:
            params.append(f"subject={quote(subject)}")
        if body:
            params.append(f"body={quote(body)}")

        if params:
            url += "?" + "&".join(params)

        logger.info(f"Generated email link for {email}")
        return url

    def generate_link(self, platform: str, contact_info: Dict[str, str]) -> str:
        """
        Generate deep link for specified platform.

        Args:
            platform: Platform name (whatsapp, facetime, phone, zoom, email)
            contact_info: Contact information dict with phone/email/meeting_id

        Returns:
            Deep link URL

        Raises:
            ValueError: If platform is unknown or required info is missing
        """
        platform = platform.lower()

        if platform == "whatsapp":
            if "phone" not in contact_info:
                raise ValueError("Phone number required for WhatsApp link")
            return self.generate_whatsapp_link(contact_info["phone"])

        elif platform == "facetime":
            if "phone" not in contact_info:
                raise ValueError("Phone number required for FaceTime link")
            return self.generate_facetime_link(contact_info["phone"])

        elif platform == "phone":
            if "phone" not in contact_info:
                raise ValueError("Phone number required for phone link")
            return self.generate_phone_link(contact_info["phone"])

        elif platform == "zoom":
            if "meeting_id" not in contact_info:
                raise ValueError("Meeting ID required for Zoom link")
            return self.generate_zoom_link(
                contact_info["meeting_id"],
                contact_info.get("password")
            )

        elif platform == "email":
            if "email" not in contact_info:
                raise ValueError("Email address required for email link")
            return self.generate_email_link(
                contact_info["email"],
                contact_info.get("subject"),
                contact_info.get("body")
            )

        else:
            raise ValueError(f"Unknown platform: {platform}")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Test the deep link generator
    generator = DeepLinkGenerator()

    print("Testing Deep Link Generator...\n")

    # Test WhatsApp
    whatsapp_link = generator.generate_whatsapp_link("+1-555-0101")
    print(f"WhatsApp: {whatsapp_link}")

    # Test FaceTime
    facetime_link = generator.generate_facetime_link("+1-555-0102")
    print(f"FaceTime: {facetime_link}")

    # Test Phone
    phone_link = generator.generate_phone_link("+1-555-0103")
    print(f"Phone: {phone_link}")

    # Test Zoom
    zoom_link = generator.generate_zoom_link("123456789", "password123")
    print(f"Zoom: {zoom_link}")

    # Test Email
    email_link = generator.generate_email_link(
        "test@example.com",
        subject="Hello",
        body="How are you?"
    )
    print(f"Email: {email_link}")

    # Test with generate_link method
    print("\nTesting generate_link method:")
    link = generator.generate_link("whatsapp", {"phone": "+1-555-0101"})
    print(f"Generated: {link}")

    print("\n✓ Deep Link Generator working correctly!")
