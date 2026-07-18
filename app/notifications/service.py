"""Notification use cases and provider-independent routing."""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Iterable

from app import pendo
from app.notifications.contracts import (
    ApprovalRequest,
    DailySummary,
    DeliveryReceipt,
    InvoiceReminder,
    LowInventoryAlert,
    NotificationChannel,
    NotificationDispatch,
    NotificationKind,
    NotificationMessage,
    NotificationTarget,
)


class NotificationService:
    """Format business events once and route them through replaceable channels."""

    def __init__(
        self,
        channels: Iterable[NotificationChannel],
        default_targets: Iterable[NotificationTarget],
        logger: logging.Logger | None = None,
    ) -> None:
        self._channels = {channel.name: channel for channel in channels}
        self._default_targets = tuple(default_targets)
        self._logger = logger or logging.getLogger("app.notifications")

    def send_daily_summary(
        self, summary: DailySummary, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Send an operational summary for the completed business day."""

        metrics = "\n".join(f"- {label}: {value}" for label, value in summary.metrics.items())
        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.DAILY_SUMMARY,
                title=f"Daily summary · {summary.business_name}",
                body=f"Date: {summary.summary_date.isoformat()}\n{metrics or '- No activity recorded'}",
                metadata={"summary_date": summary.summary_date.isoformat(), "metrics": summary.metrics},
            ),
            targets,
        )

    def send_invoice_reminder(
        self, reminder: InvoiceReminder, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Send a payment reminder for an invoice approaching or past its due date."""

        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.INVOICE_REMINDER,
                title=f"Invoice reminder · {reminder.invoice_number}",
                body=(
                    f"Customer: {reminder.customer_name}\n"
                    f"Amount: {reminder.currency_code} {reminder.amount}\n"
                    f"Due date: {reminder.due_date.isoformat()}"
                ),
                metadata={"invoice_number": reminder.invoice_number},
            ),
            targets,
        )

    def send_low_inventory_alert(
        self, alert: LowInventoryAlert, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Send an alert when stock is at or below its reorder level."""

        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.LOW_INVENTORY,
                title=f"Low inventory · {alert.product_name}",
                body=(
                    f"SKU: {alert.sku}\n"
                    f"On hand: {alert.quantity_on_hand}\n"
                    f"Reorder level: {alert.reorder_level}"
                ),
                metadata={"sku": alert.sku, "quantity_on_hand": alert.quantity_on_hand},
            ),
            targets,
        )

    def send_approval_request(
        self, request: ApprovalRequest, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Request human approval before a consequential business action."""

        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.APPROVAL_REQUEST,
                title=f"Approval required · {request.title}",
                body=f"Requested by: {request.requested_by}\n\n{request.details}",
                metadata={"requested_by": request.requested_by},
            ),
            targets,
        )

    def _dispatch(
        self, message: NotificationMessage, targets: Iterable[NotificationTarget] | None
    ) -> NotificationDispatch:
        deliveries: list[DeliveryReceipt] = []
        for target in tuple(targets) if targets is not None else self._default_targets:
            channel = self._channels.get(target.channel)
            if channel is None:
                receipt = DeliveryReceipt(
                    channel=target.channel,
                    address=target.address,
                    status="failed",
                    error="Notification channel is not configured.",
                )
            else:
                try:
                    receipt = channel.send(message, target.address)
                except Exception as error:  # Keep one failed target from blocking others.
                    receipt = DeliveryReceipt(
                        channel=target.channel,
                        address=target.address,
                        status="failed",
                        error=str(error),
                    )
            deliveries.append(receipt)
            self._logger.info("business_notification %s", asdict(receipt))
        pendo.track(
            "notification_dispatched",
            properties={
                "notification_kind": message.kind.value,
                "target_count": len(deliveries),
                "deliveries_sent": sum(1 for d in deliveries if d.status == "sent"),
                "deliveries_failed": sum(1 for d in deliveries if d.status == "failed"),
                "channels_used": ",".join(sorted({d.channel for d in deliveries})),
            },
        )
        return NotificationDispatch(message=message, deliveries=tuple(deliveries))
