"""Human Approval Tool

A FunctionTool that pauses the pipeline and asks for human confirmation
before the campaign is executed.
"""

import json


def human_approval(campaign_preview: str) -> str:
    """Request human approval before sending a campaign.

    Args:
        campaign_preview: A JSON string containing the campaign preview with
            health_concern, channel, recipient_count, and email_samples.

    Returns:
        A string indicating approval status: "APPROVED" or "REJECTED: <reason>"
    """
    # In a real deployment this would trigger an async callback / UI card.
    # For local development we use stdin.
    print("\n" + "=" * 60)
    print("  HUMAN APPROVAL REQUIRED")
    print("=" * 60)

    try:
        preview = json.loads(campaign_preview)
        print(json.dumps(preview, indent=2))
    except (json.JSONDecodeError, TypeError):
        print(campaign_preview)

    print("=" * 60)

    # Auto-approve for non-interactive / testing environments
    # In production, replace with actual human-in-the-loop mechanism
    response = input("Approve this campaign? (yes/no): ").strip().lower()

    if response in ("yes", "y", "approve"):
        return "APPROVED"
    else:
        reason = input("Reason for rejection (optional): ").strip()
        return f"REJECTED: {reason}" if reason else "REJECTED"
