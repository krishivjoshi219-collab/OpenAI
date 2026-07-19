"""Notification use cases and provider-independent routing."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import UTC, datetime

from app import pendo
from app.notifications.contracts import (
    ApprovalRequest,
    DailySummary,
    DeliveryReceipt,
    InvoiceCreatedEvent,
    InvoiceReminder,
    LowInventoryAlert,
    NotificationChannel,
    NotificationDispatch,
    NotificationKind,
    NotificationMessage,
    NotificationTarget,
    PaymentReceivedEvent,
    SystemAlert,
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

        body = f"Requested by: {request.requested_by}\n\n{request.details}"
        if request.expires_at:
            body += f"\n\nExpires: {request.expires_at}"
        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.APPROVAL_REQUEST,
                title=f"Approval required · {request.title}",
                body=body,
                metadata={"requested_by": request.requested_by, "approval_id": request.approval_id},
            ),
            targets,
        )

    def send_invoice_created(
        self, event: InvoiceCreatedEvent, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Notify that a new invoice has been created."""

        body = (
            f"Customer: {event.customer_name}\n"
            f"Amount: {event.currency_code} {event.total}\n"
            f"Invoice: {event.invoice_number}"
        )
        if event.due_date:
            body += f"\nDue: {event.due_date.isoformat()}"
        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.INVOICE_CREATED,
                title=f"Invoice created · {event.invoice_number}",
                body=body,
                metadata={
                    "invoice_number": event.invoice_number,
                    "customer_name": event.customer_name,
                    "total": event.total,
                    "currency_code": event.currency_code,
                },
            ),
            targets,
        )

    def send_payment_received(
        self, event: PaymentReceivedEvent, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Notify that a payment has been received."""

        body = (
            f"Invoice: {event.invoice_number}\n"
            f"Customer: {event.customer_name}\n"
            f"Amount: {event.currency_code} {event.amount}"
        )
        if event.paid_at:
            body += f"\nPaid at: {event.paid_at}"
        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.PAYMENT_RECEIVED,
                title=f"Payment received · {event.invoice_number}",
                body=body,
                metadata={
                    "invoice_number": event.invoice_number,
                    "amount": event.amount,
                    "currency_code": event.currency_code,
                },
            ),
            targets,
        )

    def send_system_alert(
        self, alert: SystemAlert, *, targets: Iterable[NotificationTarget] | None = None
    ) -> NotificationDispatch:
        """Send a system-level alert to operators."""

        body = f"Component: {alert.component}\nLevel: {alert.level}\n\n{alert.message}"
        if alert.details:
            body += "\n\nDetails:\n" + "\n".join(f"- {k}: {v}" for k, v in alert.details.items())
        return self._dispatch(
            NotificationMessage(
                kind=NotificationKind.SYSTEM_ALERT,
                title=f"System alert · {alert.component}",
                body=body,
                metadata={"level": alert.level, "component": alert.component, **alert.details},
            ),
            targets,
        )

    def _dispatch(
        self, message: NotificationMessage, targets: Iterable[NotificationTarget] | None
    ) -> NotificationDispatch:
        deliveries: list[DeliveryReceipt] = []
        sent_at = datetime.now(UTC).isoformat()
        for target in tuple(targets) if targets is not None else self._default_targets:
            channel = self._channels.get(target.channel)
            if channel is None:
                receipt = DeliveryReceipt(
                    channel=target.channel,
                    address=target.address,
                    status="failed",
                    error="Notification channel is not configured.",
                    sent_at=sent_at,
                )
            else:
                try:
                    receipt = channel.send(message, target.address)
                    receipt = DeliveryReceipt(
                        channel=receipt.channel,
                        address=receipt.address,
                        status=receipt.status,
                        provider_message_id=receipt.provider_message_id,
                        error=receipt.error,
                        sent_at=sent_at,
                    )
                except Exception as error:  # Keep one failed target from blocking others.
                    self._logger.error("Notification delivery failed: %s", error, exc_info=True)
                    receipt = DeliveryReceipt(
                        channel=target.channel,
                        address=target.address,
                        status="failed",
                        error=str(error),
                        sent_at=sent_at,
                    )
            deliveries.append(receipt)
            self._logger.info(
                "business_notification kind=%s channel=%s status=%s target=%s",
                message.kind.value,
                receipt.channel,
                receipt.status,
                receipt.address,
            )
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
