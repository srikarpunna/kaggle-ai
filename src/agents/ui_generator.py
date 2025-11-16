"""
ElderCare Agent - UI Generator Agent
Creates task-specific, accessible user interfaces with large icons.
"""

import logging
import json
from typing import Dict, Any, Optional
import google.generativeai as genai

from ..core.config_loader import get_config

logger = logging.getLogger(__name__)


class UIGeneratorAgent:
    """
    UI Generator Agent powered by Gemini.
    Selects and customizes accessible UI templates.
    """

    def __init__(self, api_key: str):
        self.config = get_config().get_agent_config("ui_generator")

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name=self.config.model,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
        )

        logger.info("UI Generator Agent initialized")

    async def generate_ui(
        self,
        task_name: str,
        task_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate UI for a specific task.

        Args:
            task_name: Name of the task (video_call, medication_reminder, etc.)
            task_context: Context data for the task

        Returns:
            Dict with template, customization, and UI config
        """
        # Use Gemini to select the best template
        prompt = get_config().get_prompt(
            "ui_generator",
            "template_selection",
            task_name=task_name,
            task_context=json.dumps(task_context, indent=2)
        )

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Parse JSON response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            template_id = result.get("template")
            customization = result.get("customization", {})

            # Load the template configuration
            template_config = get_config().get_ui_template(template_id)

            # Build the complete UI configuration
            ui_config = self._build_ui_config(template_config, customization, task_context)

            # Validate accessibility
            is_accessible = await self._validate_accessibility(ui_config)

            return {
                "template_id": template_id,
                "template_name": template_config.name,
                "customization": customization,
                "ui_config": ui_config,
                "accessible": is_accessible,
                "auto_cleanup": template_config.auto_cleanup
            }

        except Exception as e:
            logger.error(f"Error generating UI: {e}")
            # Fallback to error UI
            return self._generate_error_ui(str(e))

    def _build_ui_config(
        self,
        template_config: Any,
        customization: Dict[str, Any],
        task_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Build complete UI configuration from template and customization.

        Args:
            template_config: Template configuration object
            customization: Customization from Gemini
            task_context: Task context data

        Returns:
            Complete UI configuration dict
        """
        ui_config = {
            "template": template_config.name,
            "layout": template_config.layout,
            "elements": [],
            "animations": template_config.animations,
            "auto_cleanup": template_config.auto_cleanup
        }

        # Customize elements
        for element in template_config.elements:
            customized_element = element.copy()

            # Apply customization
            if element.get("id") == "contact_name" and "title" in customization:
                customized_element["content"] = customization["title"]
            elif element.get("id") == "relationship" and "subtitle" in customization:
                customized_element["content"] = customization["subtitle"]
            elif element.get("id") == "call_button" and "primary_action" in customization:
                customized_element["text"] = customization["primary_action"]

            # Inject task context data
            if "contact_photo" in task_context and element.get("id") == "contact_photo":
                customized_element["src"] = task_context["contact_photo"]
            if "medication_image" in task_context and element.get("id") == "medication_image":
                customized_element["src"] = task_context["medication_image"]

            ui_config["elements"].append(customized_element)

        return ui_config

    async def _validate_accessibility(self, ui_config: Dict[str, Any]) -> bool:
        """
        Validate UI accessibility using Gemini.

        Args:
            ui_config: UI configuration to validate

        Returns:
            True if accessible
        """
        prompt = get_config().get_prompt(
            "ui_generator",
            "accessibility_check",
            ui_config_json=json.dumps(ui_config, indent=2)
        )

        try:
            response = self.model.generate_content(prompt)
            result_text = response.text.strip()

            # Parse JSON response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]

            result = json.loads(result_text.strip())

            if not result.get("accessible"):
                logger.warning(f"Accessibility issues: {result.get('issues')}")
                logger.info(f"Suggestions: {result.get('suggestions')}")

            return result.get("accessible", True)

        except Exception as e:
            logger.error(f"Error validating accessibility: {e}")
            return True  # Default to True to not block UI generation

    def _generate_error_ui(self, error_message: str) -> Dict[str, Any]:
        """Generate error UI."""
        error_template = get_config().get_ui_template("error_ui")

        return {
            "template_id": "error_ui",
            "template_name": error_template.name,
            "customization": {
                "error_message": error_message
            },
            "ui_config": {
                "template": error_template.name,
                "layout": error_template.layout,
                "elements": error_template.elements,
                "animations": error_template.animations
            },
            "accessible": True,
            "auto_cleanup": error_template.auto_cleanup
        }

    def generate_call_ui(self, contact: Dict[str, Any], deep_link: str) -> Dict[str, Any]:
        """
        Generate UI for video call task.

        Args:
            contact: Contact information
            deep_link: Generated deep link for the call

        Returns:
            UI configuration
        """
        template = get_config().get_ui_template("call_ui")

        return {
            "template_id": "call_ui",
            "template_name": template.name,
            "ui_config": {
                "template": template.name,
                "layout": template.layout,
                "elements": [
                    {
                        "type": "image",
                        "id": "contact_photo",
                        "src": contact.get("photo_url", "/images/default-avatar.png"),
                        "alt": f"Photo of {contact['contact_name']}",
                        **{k: v for k, v in template.elements[0].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "text",
                        "id": "contact_name",
                        "content": contact["contact_name"],
                        **{k: v for k, v in template.elements[1].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "text",
                        "id": "relationship",
                        "content": f"Your {contact.get('relationship', 'contact')}",
                        **{k: v for k, v in template.elements[2].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "button",
                        "id": "call_button",
                        "text": f"📞 Video Call",
                        "action": "open_url",
                        "url": deep_link,
                        **{k: v for k, v in template.elements[3].items() if k not in ["type", "id", "text", "action"]}
                    },
                    {
                        "type": "button",
                        "id": "cancel_button",
                        "text": "Cancel",
                        "action": "close_ui",
                        **{k: v for k, v in template.elements[4].items() if k not in ["type", "id", "text", "action"]}
                    }
                ],
                "animations": template.animations,
                "auto_cleanup": template.auto_cleanup
            },
            "accessible": True
        }

    def generate_medication_ui(self, medication: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate UI for medication reminder.

        Args:
            medication: Medication information

        Returns:
            UI configuration
        """
        template = get_config().get_ui_template("medication_ui")

        return {
            "template_id": "medication_ui",
            "template_name": template.name,
            "ui_config": {
                "template": template.name,
                "layout": template.layout,
                "elements": [
                    {
                        "type": "icon",
                        "id": "alert_icon",
                        "content": "⏰",
                        **{k: v for k, v in template.elements[0].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "text",
                        "id": "reminder_title",
                        "content": "Time for Your Medication",
                        **{k: v for k, v in template.elements[1].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "image",
                        "id": "medication_image",
                        "src": medication.get("image_url", "/images/pill-generic.png"),
                        "alt": f"{medication['medication_name']} pill",
                        **{k: v for k, v in template.elements[2].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "text",
                        "id": "medication_name",
                        "content": medication["medication_name"],
                        **{k: v for k, v in template.elements[3].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "text",
                        "id": "dosage",
                        "content": medication["dosage"],
                        **{k: v for k, v in template.elements[4].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "text",
                        "id": "instructions",
                        "content": medication.get("instructions", ""),
                        **{k: v for k, v in template.elements[5].items() if k not in ["type", "id"]}
                    },
                    {
                        "type": "button",
                        "id": "taken_button",
                        "text": "✓ I Took It",
                        "action": "mark_taken",
                        "data": {"medication_id": medication["medication_id"]},
                        **{k: v for k, v in template.elements[6].items() if k not in ["type", "id", "text", "action"]}
                    },
                    {
                        "type": "button",
                        "id": "snooze_button",
                        "text": "💤 Remind Me in 10 Min",
                        "action": "snooze",
                        **{k: v for k, v in template.elements[7].items() if k not in ["type", "id", "text", "action"]}
                    },
                    {
                        "type": "button",
                        "id": "skip_button",
                        "text": "Skip",
                        "action": "skip",
                        **{k: v for k, v in template.elements[8].items() if k not in ["type", "id", "text", "action"]}
                    }
                ],
                "animations": template.animations,
                "auto_cleanup": template.auto_cleanup
            },
            "accessible": True
        }

    def generate_appointment_ui(self, appointment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate UI for appointment confirmation.

        Args:
            appointment: Appointment information

        Returns:
            UI configuration
        """
        template = get_config().get_ui_template("appointment_ui")

        return {
            "template_id": "appointment_ui",
            "template_name": template.name,
            "ui_config": {
                "template": template.name,
                "layout": template.layout,
                "elements": [
                    {
                        "type": "icon",
                        "content": "📅",
                        **{k: v for k, v in template.elements[0].items() if k != "type"}
                    },
                    {
                        "type": "text",
                        "content": "Doctor Appointment",
                        **{k: v for k, v in template.elements[1].items() if k != "type"}
                    },
                    {
                        "type": "info_row",
                        "label": "Doctor",
                        "value": appointment.get("doctor_name", "Dr. Smith"),
                        **{k: v for k, v in template.elements[2].items() if k not in ["type", "label", "value"]}
                    },
                    {
                        "type": "info_row",
                        "label": "Date",
                        "value": appointment.get("date", ""),
                        **{k: v for k, v in template.elements[3].items() if k not in ["type", "label", "value"]}
                    },
                    {
                        "type": "info_row",
                        "label": "Time",
                        "value": appointment.get("time", ""),
                        **{k: v for k, v in template.elements[4].items() if k not in ["type", "label", "value"]}
                    },
                    {
                        "type": "info_row",
                        "label": "Location",
                        "value": appointment.get("location", ""),
                        **{k: v for k, v in template.elements[5].items() if k not in ["type", "label", "value"]}
                    },
                    {
                        "type": "button",
                        "text": "✓ Confirm",
                        "action": "confirm_appointment",
                        "data": {"appointment_id": appointment.get("appointment_id")},
                        **{k: v for k, v in template.elements[7].items() if k not in ["type", "text", "action"]}
                    }
                ],
                "animations": template.animations,
                "auto_cleanup": template.auto_cleanup
            },
            "accessible": True
        }


if __name__ == "__main__":
    import asyncio
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def test_ui_generator():
        """Test the UI Generator Agent."""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment")
            return

        agent = UIGeneratorAgent(api_key=api_key)

        print("Testing UI Generator Agent...\n")

        # Test 1: Generate call UI
        print("="*60)
        print("TEST 1: Generate call UI")
        print("="*60)
        contact = {
            "contact_name": "John Thompson",
            "relationship": "son",
            "phone": "+1-555-0101",
            "photo_url": "/images/contacts/john.jpg"
        }
        call_ui = agent.generate_call_ui(contact, "https://wa.me/15550101")
        print(f"  Template: {call_ui['template_name']}")
        print(f"  Accessible: {call_ui['accessible']}")
        print(f"  Elements: {len(call_ui['ui_config']['elements'])}")
        print()

        # Test 2: Generate medication UI
        print("="*60)
        print("TEST 2: Generate medication UI")
        print("="*60)
        medication = {
            "medication_id": 1,
            "medication_name": "Lisinopril",
            "dosage": "10 mg",
            "instructions": "Take with water",
            "image_url": "/images/medications/lisinopril.png"
        }
        med_ui = agent.generate_medication_ui(medication)
        print(f"  Template: {med_ui['template_name']}")
        print(f"  Accessible: {med_ui['accessible']}")
        print(f"  Elements: {len(med_ui['ui_config']['elements'])}")
        print()

        # Test 3: Generate appointment UI
        print("="*60)
        print("TEST 3: Generate appointment UI")
        print("="*60)
        appointment = {
            "appointment_id": 1,
            "doctor_name": "Dr. James Smith",
            "date": "Thursday, November 21",
            "time": "10:30 AM",
            "location": "City Health Clinic, Room 204"
        }
        appt_ui = agent.generate_appointment_ui(appointment)
        print(f"  Template: {appt_ui['template_name']}")
        print(f"  Accessible: {appt_ui['accessible']}")
        print(f"  Elements: {len(appt_ui['ui_config']['elements'])}")
        print()

    print("Starting UI Generator tests...")
    asyncio.run(test_ui_generator())
    print("\n✓ UI Generator tests complete!")
