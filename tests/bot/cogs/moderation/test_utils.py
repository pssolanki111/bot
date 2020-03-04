import unittest
from unittest.mock import AsyncMock

from discord import Embed

from bot.cogs.moderation.utils import has_active_infraction, notify_infraction, notify_pardon
from bot.constants import Colours, Icons
from tests.helpers import MockBot, MockContext, MockMember, MockUser

RULES_URL = "https://pythondiscord.com/pages/rules"
APPEAL_EMAIL = "appeals@pythondiscord.com"

INFRACTION_TITLE = f"Please review our rules over at {RULES_URL}"
INFRACTION_APPEAL_FOOTER = f"To appeal this infraction, send an e-mail to {APPEAL_EMAIL}"
INFRACTION_AUTHOR_NAME = "Infraction information"
INFRACTION_COLOR = Colours.soft_red

INFRACTION_DESCRIPTION_TEMPLATE = (
    "\n**Type:** {type}\n"
    "**Expires:** {expires}\n"
    "**Reason:** {reason}\n"
)

PARDON_COLOR = Colours.soft_green


class ModerationUtilsTests(unittest.IsolatedAsyncioTestCase):
    """Tests Moderation utils."""

    def setUp(self):
        self.bot = MockBot()
        self.member = MockMember(id=1234)
        self.user = MockUser(id=1234)
        self.ctx = MockContext(bot=self.bot, author=self.member)
        self.bot.api_client.get = AsyncMock()

    async def test_user_has_active_infraction_true(self):
        """Test does `has_active_infraction` return that user have active infraction."""
        self.bot.api_client.get.return_value = [{
            "id": 1,
            "inserted_at": "2018-11-22T07:24:06.132307Z",
            "expires_at": "5018-11-20T15:52:00Z",
            "active": True,
            "user": 1234,
            "actor": 1234,
            "type": "ban",
            "reason": "Test",
            "hidden": False
        }]
        self.assertTrue(await has_active_infraction(self.ctx, self.member, "ban"), "User should have active infraction")

    async def test_user_has_active_infraction_false(self):
        """Test does `has_active_infraction` return that user don't have active infractions."""
        self.bot.api_client.get.return_value = []
        self.assertFalse(
            await has_active_infraction(self.ctx, self.member, "ban"),
            "User shouldn't have active infraction"
        )

    async def test_notify_infraction(self):
        """Test does `notify_infraction` create correct embed."""
        test_cases = [
            {
                "args": (self.user, "ban", "2020-02-26 09:20 (23 hours and 59 minutes)"),
                "expected_output": {
                    "description": INFRACTION_DESCRIPTION_TEMPLATE.format(**{
                        "type": "Ban",
                        "expires": "2020-02-26 09:20 (23 hours and 59 minutes)",
                        "reason": "No reason provided."
                    }),
                    "icon_url": Icons.token_removed,
                    "footer": INFRACTION_APPEAL_FOOTER
                }
            },
            {
                "args": (self.user, "warning", None, "Test reason."),
                "expected_output": {
                    "description": INFRACTION_DESCRIPTION_TEMPLATE.format(**{
                        "type": "Warning",
                        "expires": "N/A",
                        "reason": "Test reason."
                    }),
                    "icon_url": Icons.token_removed,
                    "footer": Embed.Empty
                }
            },
            {
                "args": (self.user, "note", None, None, Icons.defcon_denied),
                "expected_output": {
                    "description": INFRACTION_DESCRIPTION_TEMPLATE.format(**{
                        "type": "Note",
                        "expires": "N/A",
                        "reason": "No reason provided."
                    }),
                    "icon_url": Icons.defcon_denied,
                    "footer": Embed.Empty
                }
            },
            {
                "args": (self.user, "mute", "2020-02-26 09:20 (23 hours and 59 minutes)", "Test", Icons.defcon_denied),
                "expected_output": {
                    "description": INFRACTION_DESCRIPTION_TEMPLATE.format(**{
                        "type": "Mute",
                        "expires": "2020-02-26 09:20 (23 hours and 59 minutes)",
                        "reason": "Test"
                    }),
                    "icon_url": Icons.defcon_denied,
                    "footer": INFRACTION_APPEAL_FOOTER
                }
            }
        ]

        for case in test_cases:
            args = case["args"]
            expected = case["expected_output"]

            with self.subTest(args=args, expected=expected):
                await notify_infraction(*args)

                embed: Embed = self.user.send.call_args[1]["embed"]

                self.assertEqual(embed.title, INFRACTION_TITLE)
                self.assertEqual(embed.colour.value, INFRACTION_COLOR)
                self.assertEqual(embed.url, RULES_URL)
                self.assertEqual(embed.author.name, INFRACTION_AUTHOR_NAME)
                self.assertEqual(embed.author.url, RULES_URL)
                self.assertEqual(embed.author.icon_url, expected["icon_url"])
                self.assertEqual(embed.footer.text, expected["footer"])
                self.assertEqual(embed.description, expected["description"])

    async def test_notify_pardon(self):
        """Test does `notify_pardon` create correct embed."""
        test_cases = [
            {
                "args": (self.user, "Test title", "Example content"),
                "expected_output": {
                    "description": "Example content",
                    "title": "Test title",
                    "icon_url": Icons.user_verified
                }
            },
            {
                "args": (self.user, "Test title 1", "Example content 1", Icons.user_update),
                "expected_output": {
                    "description": "Example content 1",
                    "title": "Test title 1",
                    "icon_url": Icons.user_update
                }
            }
        ]

        for case in test_cases:
            args = case["args"]
            expected = case["expected_output"]

            with self.subTest(args=args, expected=expected):
                await notify_pardon(*args)

                embed: Embed = self.user.send.call_args[1]["embed"]

                self.assertEqual(embed.description, expected["description"])
                self.assertEqual(embed.colour.value, PARDON_COLOR)
                self.assertEqual(embed.author.name, expected["title"])
                self.assertEqual(embed.author.icon_url, expected["icon_url"])
