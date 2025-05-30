from django.db import transaction
from .models import Organization, Payment, BalanceLog
import logging

logger = logging.getLogger(__name__)


class PaymentService:
    @classmethod
    def process_payment(cls, payment_data: dict) -> bool:
        payment_status = True
        operation_id = payment_data.get('operation_id')

        if Payment.objects.filter(operation_id=operation_id).exists():
            logger.info(f"Payment with operation_id {operation_id} already processed")
            payment_status = False

        with transaction.atomic():
            payment = Payment.objects.create(
                operation_id=operation_id,
                amount=payment_data['amount'],
                payer_inn=payment_data['payer_inn'],
                document_number=payment_data['document_number'],
                document_date=payment_data['document_date']
            )

            org, created = Organization.objects.get_or_create(
                inn=payment_data['payer_inn'],
                defaults={'balance': 0}
            )

            previous_balance = org.balance
            org.balance += payment_data['amount']
            org.save()

            BalanceLog.objects.create(
                organization=org,
                amount=payment_data['amount'],
                previous_balance=previous_balance,
                new_balance=org.balance,
                payment=payment
            )

            logger.info(
                f"Processed payment {operation_id}. "
                f"Organization {org.inn} balance updated from {previous_balance} to {org.balance}"
            )

        return payment_status
